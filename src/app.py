"""Menu Engineering Bot — Streamlit application entry point

Business logic lives in analytics/, core/, data_pipeline/, pos/, and reporting/.
Dashboard workflows live in ui/pages/.

Supports two independent data workflows:
- Transaction-level data
- Aggregated monthly sales reports
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from core.performance import PerformanceProfiler
from ui.monthly_report_dashboard import render_monthly_report_dashboard
from ui.pages.analytics import render_analytics
from ui.pages.data_quality import render_data_quality
from ui.pages.data_setup import render_data_setup
from ui.pages.reports import render_reports
from ui.performance_dashboard import render_performance_summary
from ui.sidebar import render_sidebar
from ui.styles import apply_dashboard_styles


def render_transaction_workflow() -> None:
    """Render the existing transaction-level dashboard."""
    profiler = PerformanceProfiler()
    settings = render_sidebar()

    data_tab, quality_tab, analytics_tab, reports_tab = st.tabs(
        [
            "1. Data Setup",
            "2. Data Quality",
            "3. Analytics",
            "4. Reports",
        ]
    )

    # All tabs execute on each Streamlit rerun.
    # Preserve the existing dependency order.
    with data_tab, profiler.measure("Data Setup"):
        setup = render_data_setup(settings)

    with quality_tab, profiler.measure("Data Quality"):
        quality = render_data_quality(setup)

    with analytics_tab, profiler.measure("Analytics"):
        moves = render_analytics(setup, quality, settings)

    with reports_tab, profiler.measure("Reports"):
        render_reports(setup, quality, settings, moves)

    render_performance_summary(profiler)


def render_monthly_workflow() -> None:
    """Render analytics for aggregated monthly POS reports."""
    render_monthly_report_dashboard()


def main() -> None:
    """Launch the unified Menu Engineering Bot."""
    load_dotenv()

    st.set_page_config(
        page_title="Menu Engineering Bot",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_dashboard_styles()

    st.title("Menu Engineering Bot")

    st.caption(
        "Universal menu/POS data adapter + deterministic pricing analytics "
        "+ AI explanation. "
        "The numerical engine never delegates calculations to the LLM."
    )

    st.divider()

    data_mode = st.radio(
        "Select data type",
        options=[
            "Transaction Data",
            "Monthly Sales Reports",
        ],
        horizontal=True,
        key="data_mode",
    )

    st.divider()

    if data_mode == "Transaction Data":
        render_transaction_workflow()
    else:
        render_monthly_workflow()


if __name__ == "__main__":
    main()