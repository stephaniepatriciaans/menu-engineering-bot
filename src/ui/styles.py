
"""Modern Fintech styling for the Menu Engineering Bot dashboard."""

import streamlit as st


def apply_dashboard_styles() -> None:
    """Apply readable, responsive and theme-aware dashboard styling."""

    st.markdown(
        """
        <style>

        /* ==========================================
           1. MAIN DASHBOARD LAYOUT
           ========================================== */

        .block-container {
            max-width: 1600px;
            padding-top: 2rem;
            padding-bottom: 3rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }


        /* ==========================================
           2. MAIN HEADINGS
           ========================================== */

        [data-testid="stMain"] h1 {
            font-size: 2.5rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.035em;
            line-height: 1.2;
        }

        [data-testid="stMain"] h2 {
            font-size: 2rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.03em;
            line-height: 1.25;
        }

        [data-testid="stMain"] h3 {
            font-size: 1.65rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em;
            line-height: 1.3;
        }

        [data-testid="stMain"] h4 {
            font-size: 1.3rem !important;
            font-weight: 650 !important;
            line-height: 1.35;
        }


        /* ==========================================
           3. STANDARD TEXT AND DESCRIPTIONS
           ========================================== */

        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {
            font-size: 1.05rem !important;
            line-height: 1.65;
        }

        [data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            font-size: 1rem !important;
            line-height: 1.5;
        }


        /* ==========================================
           4. KPI CARDS
           ========================================== */

        [data-testid="stMetricValue"] {
            font-size: 2.1rem !important;
            font-weight: 750 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.025em;
            overflow-wrap: anywhere;
        }

        [data-testid="stMetricLabel"] p {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            line-height: 1.4;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.95rem !important;
        }

        /* Maintain consistent card corners */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
        }

        /* Colored icons in KPI cards */
        .fintech-kpi-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: var(--secondary-background-color);
            font-size: 1.5rem;
            line-height: 1;
        }


        /* ==========================================
           5. ANALYTICS TABS
           ========================================== */

        [data-testid="stMain"] button[data-baseweb="tab"] {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            padding: 0.85rem 0.75rem !important;
        }


        /* ==========================================
           6. WIDGET LABELS AND INPUT CONTROLS
           ========================================== */

        [data-testid="stWidgetLabel"] p {
            font-size: 1rem !important;
            font-weight: 600 !important;
        }

        [data-baseweb="select"] {
            font-size: 1rem !important;
        }

        [data-baseweb="select"] > div {
            min-height: 40px;
        }

        [data-baseweb="radio"] label {
            font-size: 1rem !important;
        }

        /* Buttons */
        [data-testid="stButton"] button {
            font-size: 1rem !important;
            font-weight: 600 !important;
            min-height: 40px;
        }

        /* Expandable sections */
        [data-testid="stExpander"] summary {
            font-size: 1rem !important;
            font-weight: 600;
        }


        /* ==========================================
           7. CHARTS
           ========================================== */

        [data-testid="stPlotlyChart"] {
            border-radius: 14px;
            overflow: hidden;
        }


        /* ==========================================
           8. SIDEBAR
           ========================================== */

        [data-testid="stSidebar"] {
            padding-top: 0.5rem;
        }

        [data-testid="stSidebar"] p {
            font-size: 1rem !important;
            line-height: 1.5;
        }

        [data-testid="stSidebar"] h2 {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] h3 {
            font-size: 1.2rem !important;
            font-weight: 650 !important;
        }


        /* ==========================================
           9. RESPONSIVE LAYOUT
           ========================================== */

        @media (max-width: 900px) {

            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.65rem !important;
            }

            [data-testid="stMain"] h1 {
                font-size: 2rem !important;
            }

            [data-testid="stMain"] h2 {
                font-size: 1.65rem !important;
            }

            [data-testid="stMain"] h3 {
                font-size: 1.4rem !important;
            }

            [data-testid="stMain"] button[data-baseweb="tab"] {
                font-size: 0.95rem !important;
            }
        }

        /* KPI typography — custom elements */
            .fintech-kpi-label {
                font-size: 16px !important;
                font-weight: 600 !important;
                line-height: 1.4 !important;
            }

            .fintech-kpi-value {
                font-size: 28px !important;
                font-weight: 800 !important;
                letter-spacing: -0.03em !important;
                line-height: 1.25 !important;
                margin-top: 5px;
                overflow-wrap: anywhere;
            }

        </style>
        """,
        unsafe_allow_html=True,
    )
