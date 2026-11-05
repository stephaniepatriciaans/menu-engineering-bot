"""Menu Engineering Bot — Streamlit application entry point.

Business logic lives in analytics/, core/, data_pipeline/, pos/, and reporting/.
Dashboard workflows live in ui/pages/.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from ui.pages.analytics import render_analytics
from ui.pages.data_quality import render_data_quality
from ui.pages.data_setup import render_data_setup
from ui.pages.reports import render_reports
from ui.sidebar import render_sidebar
from ui.styles import apply_dashboard_styles


def main() -> None:
    """Render all four stages without changing established financial semantics."""
    load_dotenv()
    st.set_page_config(
        page_title="Menu Engineering Bot",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_dashboard_styles()
    st.title("Menu Engineering Bot")
    st.caption(
        "Universal menu/POS data adapter + deterministic pricing analytics + AI explanation. "
        "The numerical engine never delegates calculations to the LLM."
    )
    settings = render_sidebar()
    data_tab, quality_tab, analytics_tab, reports_tab = st.tabs(
        ["1. Data Setup", "2. Data Quality", "3. Analytics", "4. Reports"]
    )
    # All tabs execute on each Streamlit rerun, so dependent context is
    # computed in order even when a later tab is currently selected.
    with data_tab:
        setup = render_data_setup(settings)
    with quality_tab:
        quality = render_data_quality(setup)
    with analytics_tab:
        moves = render_analytics(setup, quality, settings)
    with reports_tab:
        render_reports(setup, quality, settings, moves)


if __name__ == "__main__":
    main()
