"""Streamlit presentation helpers for uploaded datasets."""

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from data_adapter import read_delimited_csv
from pos_transactions import summarize_pos_transactions
from validation import audit_source_transactions


def render_source_audit(messages: Iterable[str]) -> None:
    """Display source transaction audit messages."""

    with st.expander("Source transaction audit"):
        for message in messages:
            st.write(message)

        st.caption(
            "This audit checks for identical source records "
            "and repeated transaction IDs. "
            "Repeated IDs may be normal for multi-item orders. "
            "No records are automatically removed."
        )


def render_pos_accounting_summary(
    raw_df: pd.DataFrame,
    mapping: dict[str, str | None],
) -> None:
    """Display POS accounting when price and quantity are mapped.

    This is a source-data audit, not an authorization to use
    refund candidates as positive demand observations.
    """
    price_column = mapping.get("price")
    quantity_column = mapping.get("units_sold")

    if not price_column or not quantity_column:
        return

    if (
        price_column not in raw_df.columns
        or quantity_column not in raw_df.columns
    ):
        return

    transaction_df = raw_df[
        [price_column, quantity_column]
    ].rename(
        columns={
            price_column: "price",
            quantity_column: "units_sold",
        }
    )

    try:
        summary = summarize_pos_transactions(transaction_df)
    except ValueError as exc:
        st.warning(
            f"POS transaction accounting is unavailable: {exc}"
        )
        return

    with st.expander("POS transaction accounting", expanded=False):
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Gross Revenue",
            f"{summary['gross_revenue']:,.2f}",
        )
        col2.metric(
            "Refund Candidates",
            int(summary["refund_candidate_rows"]),
        )
        col3.metric(
            "Net Revenue",
            f"{summary['net_revenue']:,.2f}",
        )

        st.caption(
            "Negative quantities are treated as refund candidates "
            "for this accounting preview. Confirm the POS export "
            "convention before relying on net revenue. "
            "Refund candidates remain excluded from the existing "
            "validated demand-model pipeline."
        )


def load_uploaded_sales(
    uploaded,
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, list[str]]:
    """Load uploaded sales data and audit source transactions.

    Reading and auditing are kept separate from Streamlit
    error handling so they can be independently tested.

    UTF-8 is the default. Windows-1252 can be selected
    explicitly for legacy POS exports.
    """
    uploaded.seek(0)

    raw_df = read_delimited_csv(
        uploaded,
        encoding=encoding,
    )

    source_audit_messages = audit_source_transactions(
        raw_df
    )

    return raw_df, source_audit_messages

