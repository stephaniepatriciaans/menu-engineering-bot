
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

        st.header("Price simulation")

        max_decrease = st.slider(
            "Maximum price decrease",
            0, 30, 10, 5,
            format="-%d%%",
        )

        max_increase = st.slider(
            "Maximum price increase",
            0, 30, 15, 5,
            format="+%d%%",
        )

        st.header("1. Load dataset")

        source = st.radio(
            "Data source",
            [
                "Full Demo Dataset — Synthetic Cafe",
                "Upload my own CSV",
            ],
        )

        uploaded = None

        if source == "Upload my own CSV":
            uploaded = st.file_uploader(
                "Upload sales/POS CSV",
                type=["csv"],
            )

    return SidebarSettings(
        business_name=business_name,
        dataset_name=dataset_name,
        currency=currency,
        max_decrease=max_decrease,
        max_increase=max_increase,
        source=source,
        uploaded=uploaded,
    )
