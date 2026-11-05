"""Interactive, non-destructive review of problematic POS source records."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import streamlit as st

from data_pipeline.pos_quarantine import POSQuarantineResult, inspect_pos_rows
from ui.table_formatters import prepare_dataframe_for_display


def render_pos_quarantine(
    raw_df: pd.DataFrame,
    mapping: Mapping[str, str | None],
    *,
    status_column: str | None = None,
    amount_column: str | None = None,
) -> POSQuarantineResult:
    """Show review candidates and return data safe for sales-only analytics."""
    invoice_column = next(
        (str(c) for c in raw_df.columns if str(c).casefold() == "invoiceno"),
        None,
    )
    with st.expander("POS data-quality quarantine & excluded-row review", expanded=True):
        st.caption(
            "Source records remain unchanged. Sales-only analytics excludes malformed "
            "rows and refund/cancellation review candidates. This is NOT a net-sales audit."
        )
        enabled = False
        if invoice_column is not None:
            enabled = st.checkbox(
                "Apply UCI Online Retail's C-prefixed invoice review convention",
                value=False,
                key="uci_c_invoice_review_optin",
                help=(
                    "For UCI Online Retail only; this is not a universal POS rule. "
                    "C-prefixed invoices are flagged, never automatically refunded."
                ),
            )
        result = inspect_pos_rows(
            raw_df,
            mapping,
            status_column=status_column,
            amount_column=amount_column,
            invoice_column=invoice_column,
            uci_cancellation_prefix=enabled,
        )
        a, b, c, d = st.columns(4)
        a.metric("Source records", f"{result.source_rows:,}")
        b.metric("Eligible sales rows", f"{len(result.analysis_rows):,}")
        c.metric("Invalid source rows", f"{result.invalid_rows:,}")
        d.metric("Refund candidates", f"{result.refund_candidates:,}")
        st.caption(
            f"Cancellation-status review candidates: {result.cancellation_candidates:,}. "
            f"C-prefixed invoices observed: {result.invoice_prefix_candidates:,} "
            "(UCI convention is opt-in)."
        )
        if result.invalid_rows:
            st.warning(
                f"{result.invalid_rows:,} record(s) have invalid required data "
                "or invalid supplied costs and are excluded from sales-only analytics. "
                "Full-export accounting remains unverified."
            )
        if not result.review_rows.empty:
            summary = pd.DataFrame(
                [(key, value) for key, value in result.reason_counts.items() if value],
                columns=["Review reason", "Rows"],
            )
            st.dataframe(summary, hide_index=True)
            st.dataframe(
                prepare_dataframe_for_display(result.review_rows.head(30)),
                hide_index=True,
            )
            st.download_button(
                "Download source rows requiring review (CSV)",
                result.review_rows.to_csv(index=False).encode("utf-8-sig"),
                file_name="pos_rows_for_review.csv",
                mime="text/csv",
                key="pos_quarantine_export",
            )
            st.caption(
                "Review reasons can overlap. This file includes all original columns, "
                "source row numbers and candidate reasons. No original file is changed."
            )
        if result.analysis_rows.empty:
            st.error("No eligible sales records remain. Review the source mappings and rows.")
            st.stop()
        return result
