"""Streamlit presentation helpers for uploaded datasets."""

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from data_adapter import read_delimited_csv
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


def load_uploaded_sales(uploaded) -> tuple[pd.DataFrame, list[str]]:
    """Load uploaded sales data and audit source transactions.

    Reading and auditing are kept separate from Streamlit
    error handling so they can be independently tested.
    """
    uploaded.seek(0)

    raw_df = read_delimited_csv(uploaded)

    source_audit_messages = audit_source_transactions(
        raw_df
    )

    return raw_df, source_audit_messages
