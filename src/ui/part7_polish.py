"""Additional responsive, theme-aware dashboard polish for Part 7.4.

Presentation only: never changes accounting, input data, or forecasts.
"""

import streamlit as st

PART7_CSS = """
<style>
/* 7.4: scoped to the main content and sidebar; theme tokens are respected. */
[data-testid="stMain"] .block-container {
    max-width: 1480px;
    padding-top: clamp(1.1rem, 2.5vw, 2.25rem);
    padding-bottom: 3rem;
}
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 {
    text-wrap: balance;
    line-height: 1.2;
}
[data-testid="stMain"] [data-testid="stMetric"] {
    min-width: 0;
    border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
    border-radius: 14px;
    padding: 1rem 1.1rem;
}
[data-testid="stMain"] [data-testid="stMetricValue"] {
    overflow-wrap: anywhere;
    font-variant-numeric: tabular-nums;
}
[data-testid="stMain"] [data-testid="stAlert"] {
    border-radius: 10px;
    line-height: 1.5;
}
[data-testid="stMain"] [data-testid="stExpander"] {
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stMain"] [data-testid="stDataFrame"],
[data-testid="stMain"] [data-testid="stVegaLiteChart"] {
    min-width: 0;
}
[data-testid="stMain"] [data-baseweb="tab-list"] {
    gap: 0.35rem;
    overflow-x: auto;
    scrollbar-width: thin;
}
[data-testid="stMain"] [data-baseweb="tab"] {
    white-space: nowrap;
    min-height: 40px;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    line-height: 1.4;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    min-width: 0;
}
[data-testid="stMain"] [data-testid="stSelectbox"],
[data-testid="stMain"] [data-testid="stNumberInput"],
[data-testid="stMain"] [data-testid="stTextInput"] {
    min-width: 0;
}
@media (max-width: 850px) {
    [data-testid="stMain"] .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    [data-testid="stMain"] [data-testid="stMetric"] {
        padding: 0.85rem;
    }
}
@media (prefers-reduced-motion: reduce) {
    [data-testid="stMain"] *,
    [data-testid="stSidebar"] * {
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
"""


def apply_part7_polish() -> None:
    """Apply additive CSS after existing theme styles."""
    st.markdown(PART7_CSS, unsafe_allow_html=True)
