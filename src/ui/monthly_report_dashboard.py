"""Monthly summary analytics inside the main Menu Engineering Bot Streamlit app.

These workbooks contain month-level menu summaries, NOT individual orders.
No transaction dates, costs, margins, or elasticity are inferred.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from analytics.monthly_business_insights import build_monthly_business_insights
from data_pipeline.monthly_report import (
    category_performance,
    item_performance,
    load_monthly_reports,
    monthly_overview,
)
from reporting.monthly_business_insights_pdf import build_monthly_business_insights_pdf

ITEM_IDENTITY = [
    "Menu Code",
    "Menu",
    "Menu Category",
    "Menu Category Detail",
]


def _money(amount: float) -> str:
    """Compact IDR display; underlying values are never rounded or modified."""
    value = float(amount)
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:,.2f}B"
    if magnitude >= 1_000_000:
        return f"Rp {value / 1_000_000:,.2f}M"
    if magnitude >= 1_000:
        return f"Rp {value / 1_000:,.1f}K"
    return f"Rp {value:,.0f}"


def _month_label(value: object) -> str:
    return pd.Timestamp(str(value)).strftime("%b %Y")


def _rank_items(rows: pd.DataFrame) -> pd.DataFrame:
    """Sum units by exact item identity, combining channels only for that identity."""
    return (
        rows.groupby(ITEM_IDENTITY, dropna=False, as_index=False)
        .agg(
            units_sold=("Qty", "sum"),
            reported_net_sales=("Net Sales Total", "sum"),
        )
        .sort_values(["units_sold", "reported_net_sales"], ascending=[False, False])
        .reset_index(drop=True)
    )


def _downloads(overview: pd.DataFrame, items: pd.DataFrame,
               categories: pd.DataFrame, audit: pd.DataFrame) -> None:
    with st.expander("Download analysis tables (CSV)"):
        columns = st.columns(2)
        for index, (filename, table) in enumerate((
            ("monthly_overview.csv", overview),
            ("item_performance.csv", items),
            ("category_performance.csv", categories),
            ("source_audit.csv", audit),
        )):
            with columns[index % 2]:
                st.download_button(
                    filename,
                    data=table.to_csv(index=False).encode("utf-8-sig"),
                    file_name=filename,
                    mime="text/csv",
                    key=f"monthly_export_{filename}",
                    width="stretch",
                )


def render_monthly_report_dashboard() -> None:
    """Display validated monthly sales summaries in the existing Streamlit app."""
    st.subheader("Monthly Sales Analytics")
    st.caption(
        "Monthly aggregated menu sales · IDR · 'Most ordered' means units sold "
        "(Qty), not distinct customer orders. No individual transaction dates, "
        "item costs, margins, or elasticity are inferred."
    )

    uploads = st.file_uploader(
        "Upload monthly Sales Menu Recapitulation reports (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
        key="monthly_report_uploads",
    )
    if not uploads:
        st.info("Upload one or more monthly reports to see your most ordered items and sales trends.")
        return

    try:
        report = load_monthly_reports(uploads)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        st.error(f"Monthly reports could not be validated: {exc}")
        return

    overview = monthly_overview(report.rows)
    items = item_performance(report.rows)
    categories = category_performance(report.rows)
    if overview.empty:
        st.warning("No monthly data found.")
        return

    overview = overview.sort_values("period_start").reset_index(drop=True)
    total_sales = float(overview["reported_net_sales"].sum())
    total_units = float(overview["units_sold"].sum())
    newest = overview.iloc[-1]
    growth = None
    if len(overview) >= 2:
        prior_month = pd.Timestamp(overview.iloc[-2]["period_start"]).to_period("M")
        latest_month = pd.Timestamp(newest["period_start"]).to_period("M")
        previous = float(overview.iloc[-2]["reported_net_sales"])
        if latest_month.ordinal - prior_month.ordinal == 1 and previous != 0:
            growth = (float(newest["reported_net_sales"]) / previous - 1) * 100

    kpi = st.columns(4)
    kpi[0].metric("Reported net sales · all months", _money(total_sales))
    kpi[1].metric("Units sold · all months", f"{total_units:,.0f}")
    kpi[2].metric("Latest month", _month_label(newest["period_start"]))
    kpi[3].metric(
        "Latest MoM net sales",
        f"{growth:+.1f}%" if growth is not None else "N/A",
        help="Change from the previous uploaded month; only meaningful when months are consecutive.",
    )

    overview_tab, popularity_tab, category_tab, insights_tab, audit_tab = st.tabs(
        ["Overview", "Most Ordered", "Categories & Channels", "Business Insights", "Data Quality"]
    )

    with overview_tab:
        st.markdown("#### Monthly reported net sales")
        sales_chart = overview[["period_start", "reported_net_sales"]].copy()
        sales_chart["Month"] = sales_chart["period_start"].map(_month_label)
        sales_chart["Net sales (Rp billions)"] = sales_chart["reported_net_sales"] / 1_000_000_000
        # Explicit ordinal sort guarantees Aug -> Sep -> Oct even when
        # a charting library would otherwise sort month labels alphabetically.
        month_order = sales_chart["Month"].tolist()
        monthly_chart = (
            alt.Chart(sales_chart)
            .mark_bar(size=48, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Month:N", sort=month_order, axis=alt.Axis(labelAngle=0, title=None)),
                y=alt.Y("Net sales (Rp billions):Q", title="Net sales (Rp billions)"),
                tooltip=[
                    alt.Tooltip("Month:N"),
                    alt.Tooltip("reported_net_sales:Q", title="Net sales (IDR)", format=",.0f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(monthly_chart, width="stretch")

        monthly_table = overview.copy()
        monthly_table["Month"] = monthly_table["period_start"].map(_month_label)
        monthly_table = monthly_table.rename(columns={
            "units_sold": "Units sold",
            "reported_net_sales": "Net sales (IDR)",
            "reported_grand_total": "Grand total (IDR)",
            "menu_discount": "Menu discounts (IDR)",
            "bill_discount": "Bill discounts (IDR)",
            "summary_rows": "Source rows",
        })
        st.dataframe(
            monthly_table[[
                "Month", "Source rows", "Units sold", "Net sales (IDR)",
                "Grand total (IDR)", "Menu discounts (IDR)", "Bill discounts (IDR)",
            ]],
            hide_index=True,
            width="stretch",
            column_config={
                "Source rows": st.column_config.NumberColumn(format="%d"),
                "Units sold": st.column_config.NumberColumn(format="%d"),
                "Net sales (IDR)": st.column_config.NumberColumn(format="Rp %,.0f"),
                "Grand total (IDR)": st.column_config.NumberColumn(format="Rp %,.0f"),
                "Menu discounts (IDR)": st.column_config.NumberColumn(format="Rp %,.0f"),
                "Bill discounts (IDR)": st.column_config.NumberColumn(format="Rp %,.0f"),
            },
        )

    with popularity_tab:
        st.markdown("#### Most ordered menu items")
        st.caption(
            "Ranked by summed Qty. Sales channels are combined only when menu "
            "code, name, category and subcategory all match; different variations stay separate."
        )

        periods = sorted(report.rows["period_start"].unique())
        period_options = ["All uploaded months", *[_month_label(p) for p in periods]]
        left, middle, right = st.columns([2, 2, 1])
        with left:
            month_choice = st.selectbox("Reporting month", period_options, key="monthly_pop_month")
        with middle:
            item_type = st.selectbox(
                "Item type",
                [
                    "All recorded items",
                    "Beverages",
                    "Food",
                    "Exclude ADDITIONAL category",
                ],
                index=0,
                key="monthly_pop_item_type",
            )
        with right:
            top_n = st.selectbox("Show top", [10, 20, 50], key="monthly_pop_top")

        second_left, second_right = st.columns(2)
        with second_left:
            category_options = sorted(report.rows["Menu Category"].dropna().astype(str).unique())
            category_choice = st.selectbox(
                "Source category", ["All categories", *category_options], key="monthly_pop_category"
            )
        with second_right:
            channel_options = sorted(report.rows["Sales Type"].dropna().astype(str).unique())
            channel_choice = st.selectbox(
                "Sales channel", ["All channels", *channel_options], key="monthly_pop_channel"
            )

        st.caption(
            "Item types are determined using the source Menu Category. "
            "Excluding ADDITIONAL removes that category only; bundled or "
            "promotional entries in other categories may still appear."
        )
        filtered = report.rows.copy()
        if month_choice != "All uploaded months":
            chosen_period = periods[period_options.index(month_choice) - 1]
            filtered = filtered.loc[filtered["period_start"] == chosen_period]
        categories_normalized = filtered["Menu Category"].fillna("").astype(str).str.strip().str.upper()
        if item_type == "Beverages":
            filtered = filtered.loc[categories_normalized.str.startswith("BEVERAGE")]
        elif item_type == "Food":
            filtered = filtered.loc[categories_normalized.eq("FOOD")]
        elif item_type == "Exclude ADDITIONAL category":
            filtered = filtered.loc[~categories_normalized.eq("ADDITIONAL")]
        if category_choice != "All categories":
            filtered = filtered.loc[filtered["Menu Category"] == category_choice]
        if channel_choice != "All channels":
            filtered = filtered.loc[filtered["Sales Type"] == channel_choice]

        ranked = _rank_items(filtered)
        if ranked.empty:
            st.info("No items match these filters.")
        else:
            most = ranked.head(int(top_n)).copy()
            most.insert(0, "Rank", range(1, len(most) + 1))
            winner = most.iloc[0]
            st.metric(
                "Most ordered item (by units)",
                str(winner["Menu"]),
                f"{float(winner['units_sold']):,.0f} units",
                delta_color="off",
            )
            chart = most.iloc[::-1].copy()
            chart["Item"] = (
                chart["Menu"].astype(str).str.slice(0, 55)
                + " | " + chart["Menu Code"].astype(str)
            )
            ranking_chart = (
                alt.Chart(chart)
                .mark_bar(cornerRadiusEnd=3)
                .encode(
                    y=alt.Y("Item:N", sort=chart["Item"].iloc[::-1].tolist(),
                            axis=alt.Axis(title=None, labelLimit=240)),
                    x=alt.X("units_sold:Q", title="Units sold"),
                    tooltip=[
                        alt.Tooltip("Menu:N", title="Menu item"),
                        alt.Tooltip("Menu Code:N", title="Menu code"),
                        alt.Tooltip("units_sold:Q", title="Units sold", format=",.0f"),
                        alt.Tooltip("reported_net_sales:Q", title="Net sales (IDR)", format=",.0f"),
                    ],
                )
                .properties(height=max(340, min(1050, len(chart) * 34)))
            )
            st.altair_chart(ranking_chart, width="stretch")
            display = most.rename(columns={
                "Menu": "Menu item", "Menu Code": "Menu code",
                "Menu Category": "Category", "Menu Category Detail": "Subcategory",
                "units_sold": "Units sold", "reported_net_sales": "Net sales (IDR)",
            })
            st.dataframe(
                display[[
                    "Rank", "Menu item", "Menu code", "Category", "Subcategory",
                    "Units sold", "Net sales (IDR)",
                ]],
                hide_index=True,
                width="stretch",
                column_config={
                    "Units sold": st.column_config.NumberColumn(format="%d"),
                    "Net sales (IDR)": st.column_config.NumberColumn(format="Rp %,.0f"),
                },
            )

            with st.expander("Least ordered items"):
                st.caption(
                    "Low volume may reflect limited availability, seasonal items, "
                    "or modifiers; it does not automatically mean poor performance."
                )
                least = ranked.sort_values("units_sold", ascending=True).head(int(top_n))
                st.dataframe(
                    least[["Menu", "Menu Code", "Menu Category", "units_sold"]],
                    hide_index=True,
                    width="stretch",
                )

    with category_tab:
        st.markdown("#### Category and sales channel performance")
        category_totals = (
            categories.groupby("Menu Category", dropna=False, as_index=False)
            .agg(units_sold=("units_sold", "sum"),
                 reported_net_sales=("reported_net_sales", "sum"))
            .sort_values("units_sold", ascending=False)
        )
        category_chart = (
            alt.Chart(category_totals)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                y=alt.Y("Menu Category:N", sort="-x", title=None,
                        axis=alt.Axis(labelLimit=240)),
                x=alt.X("units_sold:Q", title="Units sold"),
                tooltip=[
                    alt.Tooltip("Menu Category:N", title="Category"),
                    alt.Tooltip("units_sold:Q", title="Units sold", format=",.0f"),
                    alt.Tooltip("reported_net_sales:Q", title="Net sales (IDR)", format=",.0f"),
                ],
            )
            .properties(height=max(320, min(750, len(category_totals) * 34)))
        )
        st.altair_chart(category_chart, width="stretch")
        st.dataframe(
            categories.rename(columns={
                "period_start": "Month", "units_sold": "Units sold",
                "reported_net_sales": "Net sales (IDR)",
            }),
            hide_index=True,
            width="stretch",
        )

        st.markdown("#### POS vs MO&P")
        channel_totals = (
            report.rows.groupby("Sales Type", dropna=False, as_index=False)
            .agg(units_sold=("Qty", "sum"),
                 reported_net_sales=("Net Sales Total", "sum"))
        )
        st.dataframe(channel_totals, hide_index=True, width="stretch")

    with insights_tab:
        st.markdown("#### Business Insights")
        st.caption(
            "Deterministic, data-grounded explanations. No AI-generated causes "
            "or recommendations are presented as facts."
        )
        language_option = st.selectbox(
            "Insight language",
            options=["English", "Bahasa Indonesia"],
            key="monthly_insights_language",
        )
        language = "id" if language_option == "Bahasa Indonesia" else "en"
        insights = build_monthly_business_insights(report.rows, language=language)
        for insight in insights:
            st.markdown(f"**{insight.heading}**")
            st.write(insight.observation)
            if insight.kind == "caution":
                st.caption(
                    ("Perlu ditinjau: " if language == "id" else "Review: ")
                    + insight.next_step
                )
            else:
                st.caption(
                    ("Langkah selanjutnya: " if language == "id" else "Next check: ")
                    + insight.next_step
                )
            st.divider()
        text_report = "\n\n".join(
            f"{insight.heading}\n{insight.observation}\n{insight.next_step}"
            for insight in insights
        )
        download_col, pdf_col = st.columns(2)
        with download_col:
            st.download_button(
                "Download business insights (.txt)",
                data=text_report.encode("utf-8-sig"),
                file_name="monthly_business_insights.txt",
                mime="text/plain",
                key="monthly_insights_text_download",
                width="stretch",
            )
        with pdf_col:
            pdf_data = build_monthly_business_insights_pdf(report.rows, language=language)
            st.download_button(
                "Download business insights (.pdf)",
                data=pdf_data,
                file_name=f"monthly_business_insights_{language}.pdf",
                mime="application/pdf",
                key="monthly_insights_pdf_download",
                width="stretch",
            )

    with audit_tab:
        st.markdown("#### Source validation")
        st.dataframe(report.audit, hide_index=True, width="stretch")
        st.warning(
            "All financial amounts are source-reported. Matching accounting "
            "identities does not independently prove accuracy. 'Unit Price' is "
            "not used to reconstruct sales; unusual values are retained."
        )
        st.caption(
            "These reports do not establish distinct orders, refunds, daily/hourly "
            "patterns, unit costs, contribution margins, or price elasticity."
        )

    _downloads(overview, items, categories, report.audit)
