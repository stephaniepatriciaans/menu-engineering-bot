
"""Sidebar controls for the Menu Engineering Bot."""

from typing import NamedTuple

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from config import CURRENCY_CONFIG


class SidebarSettings(NamedTuple):
    """Values returned by the sidebar controls."""
    business_name: str
    dataset_name: str
    currency: str
    max_decrease: int
    max_increase: int
    source: str
    uploaded: UploadedFile | None
    encoding: str = "utf-8-sig"


def render_sidebar() -> SidebarSettings:
    """Render sidebar controls and return selected settings."""

    with st.sidebar:
        st.header("Business settings")

        business_name = st.text_input(
            "Business name",
            value="My Food-Service Business",
        )

        dataset_name = st.text_input(
            "Dataset name",
            value="Menu Sales Dataset",
        )

        currency = st.selectbox(
            "Currency",
            list(CURRENCY_CONFIG.keys()),
            index=0,
        )

        st.header("Dataset")

        source = st.radio(
            "Data source",
            [
                "Full Demo Dataset — Synthetic Cafe",
                "Upload my own CSV",
            ],
        )

        uploaded = None
        encoding = "utf-8-sig"

        if source == "Upload my own CSV":
            encoding = st.selectbox(
                "CSV file encoding",
                options=["utf-8-sig", "cp1252"],
                format_func=lambda value: (
                    "UTF-8 (Recommended)"
                    if value == "utf-8-sig"
                    else "Windows-1252 (Legacy POS)"
                ),
                help=(
                    "Use UTF-8 for most CSV files. "
                    "Select Windows-1252 only for legacy POS exports."
                ),
                key="sales_csv_encoding",
            )

            uploaded = st.file_uploader(
                "Upload sales/POS CSV",
                type=["csv"],
            )

    return SidebarSettings(
        business_name=business_name,
        dataset_name=dataset_name,
        currency=currency,
        max_decrease=10,
        max_increase=15,
        source=source,
        uploaded=uploaded,
        encoding=encoding,
    )
