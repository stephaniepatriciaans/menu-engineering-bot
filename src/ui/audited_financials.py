"""Streamlit views for independently matched financial totals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.financial_integration import (
    AuditedFinancials,
    audited_menu_quadrants,
    build_audited_financials,
    financial_report_text,
)
from pos.export_validation import POSAudit
from reporting.financial_appendix_pdf import generate_audited_financial_pdf
from ui.audited_daily_chart import build_audited_daily_sales_chart


def get_audited_financials(
    validated_and_filtered: pd.DataFrame,
    financial_preview: dict[str, object] | None,
) -> AuditedFinancials | None:
    """Never use an operator-only preview as a verified financial source."""
    if financial_preview is None:
        return None
    audit = financial_preview.get("matched_audit")
    rows = financial_preview.get("audited_rows")
    if not isinstance(audit, POSAudit) or not isinstance(rows, pd.DataFrame):
        return None
    try:
        return build_audited_financials(validated_and_filtered, rows, audit)
    except (ValueError, KeyError) as exc:
        st.warning(f"Audited financial view unavailable: {exc}")
        return None


def render_audited_financials(
    financials: AuditedFinancials | None,
    currency: str,
    cost_is_assumption: bool = False,
) -> None:
    """Expose audited business-level net sales and filtered eligible analysis."""
    st.subheader("Audited POS financial performance")
    if financials is None:
        st.info(
            "Financial integration is locked. In Data Quality → Advanced POS "
            "discount & sales reconciliation, confirm the mapping and compare "
            "the full export with an independently generated POS net-sales summary."
        )
        return

    st.success("Full-export pre-tax net sales independently matched to the cent.")
    net, eligible, profit = st.columns(3)
    net.metric("Full-export net item sales", f"{currency} {financials.full_export_net_sales:,.2f}")
    eligible.metric("Filtered eligible sale revenue", f"{currency} {financials.eligible_sales:,.2f}")
    profit.metric(
        "Filtered eligible contribution (cost estimate)",
        f"{currency} {financials.contribution_profit:,.2f}"
        if financials.contribution_profit is not None else "Cost data incomplete",
    )
    st.caption(
        "Full-export net sales include signed refund events. Filtered item/day totals "
        "include only eligible sales. They must not be presented as filtered net revenue."
    )
    if financials.contribution_profit is not None:
        st.caption(
            "Contribution profit uses provided or estimated unit costs. "
            "The settlement audit validates sales totals, not purchasing costs."
        )
        if cost_is_assumption:
            st.warning("Unit costs are scenario assumptions, not verified purchase costs.")
    if financials.has_refund_events:
        st.warning(
            "Refund events have not been allocated to products or dates. "
            "Item-level profit and margin exclude refunds and refund costs."
        )

    st.markdown("**Eligible sales by item**")
    items = financials.by_item.copy()
    if not items.empty:
        for column in ("revenue", "contribution_profit"):
            items[column] = items[column].map(
                lambda value: float(value) if pd.notna(value) else None
            )
        st.dataframe(items, use_container_width=True, hide_index=True)

    st.markdown("**Eligible sales by category**")
    categories = financials.by_category.copy()
    if not categories.empty:
        for column in ("revenue", "contribution_profit"):
            categories[column] = categories[column].map(
                lambda value: float(value) if pd.notna(value) else None
            )
        st.dataframe(categories, use_container_width=True, hide_index=True)

    st.markdown("**Eligible-sales menu quadrants**")
    quadrants = audited_menu_quadrants(financials)
    if quadrants.empty:
        st.info("Audited quadrants need complete costs and nonzero item revenue.")
    else:
        st.dataframe(
            quadrants[["item", "units", "revenue", "margin_pct", "quadrant"]],
            use_container_width=True, hide_index=True,
        )
        st.caption("Quadrants use eligible-sales contribution margins and popularity; refund costs are not allocated.")

    st.markdown("**Eligible sales by hour**")
    hours = financials.by_hour.copy()
    if hours.empty:
        st.caption("No usable transaction-hour data for the audited eligible rows.")
    else:
        hours["revenue"] = hours["revenue"].map(float)
        st.bar_chart(hours.set_index("hour")["revenue"], x_label="Hour", y_label="Eligible sales")

    st.markdown("**Eligible sales by day**")
    days = financials.by_day.copy()
    if not days.empty:
        days["revenue"] = days["revenue"].map(float)
        st.plotly_chart(
            build_audited_daily_sales_chart(days),
            width="stretch",
            config={"displayModeBar": False},
        )
        st.dataframe(days, use_container_width=True, hide_index=True)

    st.caption(
        "Pricing recommendations, elasticity and model evaluation remain on their "
        "original pre-discount price basis. A reconciliation alone cannot validate "
        "counterfactual demand effects or infer regular menu prices from coupons."
    )


def render_audited_report_download(
    financials: AuditedFinancials | None,
    business_name: str,
) -> None:
    """Provide a separate deterministic attachment, not an unverified AI claim."""
    if financials is None:
        st.caption("No independently audited financial appendix is available for this export.")
        return
    text = financial_report_text(financials, business_name=business_name)
    st.download_button(
        "Download audited financial appendix (.txt)",
        text,
        file_name="audited_pos_financial_appendix.txt",
        mime="text/plain",
        key="audited_pos_financial_report_download",
    )
    st.download_button(
        "Download audited financial appendix (.pdf)",
        generate_audited_financial_pdf(text),
        file_name="audited_pos_financial_appendix.pdf",
        mime="application/pdf",
        key="audited_pos_financial_pdf_download",
    )
    st.caption(
        "The appendix is calculated deterministically from the matched POS audit. "
        "The AI pricing memo remains separate and is not certified by this audit."
    )
