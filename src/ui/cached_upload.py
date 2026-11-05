"""Bounded cache for repeated CSV/Excel parsing of unchanged upload bytes."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st


@st.cache_data(max_entries=1, ttl=1800, show_spinner=False)
def cached_uploaded_sales(
    filename: str,
    file_bytes: bytes,
    encoding: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Cache complete source audit by name, file contents and encoding.

    A cached DataFrame is returned as a separate copy by Streamlit. No private
    POS data is saved to the repository or sent to an external service.
    """
    # Local import avoids an import cycle with ui.data_upload.
    from ui.data_upload import _load_uploaded_sales_uncached

    upload = BytesIO(file_bytes)
    upload.name = filename  # type: ignore[attr-defined]
    return _load_uploaded_sales_uncached(upload, encoding=encoding)
