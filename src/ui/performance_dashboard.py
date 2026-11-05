"""Optional developer-facing time diagnostics with no dataset payloads."""

from __future__ import annotations

import streamlit as st

from core.performance import PerformanceProfiler


def render_performance_summary(profiler: PerformanceProfiler) -> None:
    """Display last execution's stage timing; not a rigorous benchmark."""
    with st.sidebar.expander("Performance diagnostics (last rerun)", expanded=False):
        st.caption(
            "Wall-clock time spent in each workflow stage on this rerun. "
            "The sum excludes browser rendering; results vary with device and cache state."
        )
        for label, seconds in profiler.durations.items():
            st.write(f"{label}: {seconds:.2f} seconds")
        st.write(f"**Measured total:** {profiler.total_seconds:.2f} seconds")
