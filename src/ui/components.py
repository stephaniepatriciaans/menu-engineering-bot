"""Reusable Streamlit dashboard components."""

import pandas as pd
import streamlit as st

from config import format_currency


def render_kpi_cards(
    df: pd.DataFrame,
    currency: str,
) -> None:
    """Display Modern Fintech KPI cards with colored icons."""

    total_revenue = float(
        (df["price"] * df["units_sold"]).sum()
    )

    total_units = df["units_sold"].sum()
    sales_records = len(df)
    menu_items = df["item"].nunique()

    cards = [
        {
            "label": "Total Revenue",
            "value": format_currency(total_revenue, currency),
            "icon": "📈",
            "caption": "Sales revenue",
        },
        {
            "label": "Units Sold",
            "value": f"{total_units:,.0f}",
            "icon": "📦",
            "caption": "Products purchased",
        },
        {
            "label": "Sales Records",
            "value": f"{sales_records:,}",
            "icon": "🧾",
            "caption": "Recorded sales rows",
        },
        {
            "label": "Menu Items",
            "value": f"{menu_items:,}",
            "icon": "🍽️",
            "caption": "Unique menu items",
        },
    ]

    columns = st.columns(4, gap="medium")

    for index, (column, card) in enumerate(zip(columns, cards)):
        with column:
            with st.container(border=True):

                icon_col, metric_col = st.columns(
                    [1, 4],
                    gap="small",
                    vertical_alignment="center",
                )

                with icon_col:
                    with st.container(key=f"kpi_icon_{index}"):
                        st.markdown(
                            f"<div class='fintech-kpi-icon'>"
                            f"{card['icon']}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                with metric_col:
                    st.markdown(
                        f"""
                        <div class="fintech-kpi-label">
                            {card["label"]}
                        </div>
                        <div class="fintech-kpi-value">
                            {card["value"]}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.caption(card["caption"])



def render_business_header(
    business_name: str,
    start_date,
    end_date,
    menu_item_count: int,
) -> None:
    """Display a clean Modern Fintech business header."""

    start_label = start_date.strftime("%b %d, %Y")
    end_label = end_date.strftime("%b %d, %Y")

    with st.container(border=True):
        st.caption("BUSINESS INTELLIGENCE / OVERVIEW")

        st.markdown(f"## {business_name}")

        st.write(
            "Sales performance, trends, and menu intelligence."
        )

        st.caption(
            f"📅 {start_label} – {end_label}"
        )


def render_data_quality_summary(
    adapter_warnings: list[str],
    validation_warnings: list[str],
) -> None:
    """Display important data-quality messages in a compact panel."""

    warnings = list(dict.fromkeys(
        [*adapter_warnings, *validation_warnings]
    ))

    if not warnings:
        st.success("Data quality checks passed.")
        return

    st.warning(
        f"{len(warnings)} data-quality notice(s). "
        "Review these before making business decisions."
    )

    with st.expander(
        "View Data Quality Details",
        expanded=False,
    ):
        for warning in warnings:
            st.markdown(f"- {warning}")


def render_validation_overview(
    df: pd.DataFrame,
    adapter_warnings: list[str],
    validation_warnings: list[str],
) -> None:
    """Display a compact, theme-aware validation status."""

    warnings = list(
        dict.fromkeys([*adapter_warnings, *validation_warnings])
    )

    dates = pd.to_datetime(
        df["date"],
        errors="coerce",
    ).dropna()

    if dates.empty:
        date_label = "Dates unavailable"
    else:
        date_label = (
            f"{dates.min():%b %Y} – "
            f"{dates.max():%b %Y}"
        )

    notice_count = len(warnings)

    # Compact validation status
    with st.container(border=True):
        status_col, date_col, notice_col = st.columns(
            [2.5, 2, 1.5],
            gap="medium",
            vertical_alignment="center",
        )

        with status_col:
            st.markdown("**✅ Dataset Validated**")

        with date_col:
            st.caption(f"📅 {date_label}")

        with notice_col:
            if notice_count:
                st.caption(
                    f"⚠️ {notice_count} quality "
                    f"{'notice' if notice_count == 1 else 'notices'}"
                )
            else:
                st.caption("✅ No quality notices")

    # Keep every warning available for review.
    if warnings:
        with st.expander(
            "View Data Quality Details",
            expanded=False,
        ):
            for warning in warnings:
                st.warning(warning)

def render_chart_header(
    title: str,
    description: str = "",
) -> None:
    """Display consistent, readable dashboard chart headings."""

    st.markdown(f"### {title}")

    if description:
        st.caption(description)