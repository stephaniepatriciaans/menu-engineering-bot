"""Theme-safe fintech dashboard styling."""

import streamlit as st


def apply_dashboard_styles() -> None:
    """Style the dashboard without overriding Streamlit theme colors."""

    st.markdown(
        """
        <style>
        /* ============================================
           1. RESPONSIVE DASHBOARD LAYOUT
           ============================================ */

        [data-testid="stMain"] .block-container {
            max-width: 1450px;
            padding: 2.25rem 2.5rem 5rem;
        }

        /* ============================================
           2. TYPOGRAPHY
           ============================================ */

        [data-testid="stMain"] h1 {
            font-size: clamp(2rem, 3vw, 2.8rem) !important;
            font-weight: 750 !important;
            letter-spacing: -0.045em !important;
            line-height: 1.16 !important;
        }

        [data-testid="stMain"] h2 {
            font-size: clamp(1.5rem, 2vw, 2rem) !important;
            font-weight: 720 !important;
            letter-spacing: -0.035em !important;
        }

        [data-testid="stMain"] h3 {
            font-size: 1.3rem !important;
            font-weight: 680 !important;
            letter-spacing: -0.025em !important;
        }

        [data-testid="stMain"] h4 {
            font-size: 1.1rem !important;
            font-weight: 650 !important;
        }

        /* ============================================
           3. INPUTS AND BUTTONS
           ============================================ */

        [data-baseweb="select"] > div {
            border-radius: 10px !important;
            min-height: 43px;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
            border-radius: 10px !important;
        }

        [data-testid="stButton"] button {
            border-radius: 10px !important;
            min-height: 43px !important;
            font-weight: 650 !important;
            transition: transform 160ms ease;
        }

        /* ============================================
           4. NATIVE METRIC CARDS
           ============================================ */

        [data-testid="stMetric"] {
            border: 1px solid
                color-mix(in srgb, currentColor 18%, transparent);
            border-radius: 14px;
            padding: 1.2rem 1.35rem;
        }

        [data-testid="stMetricLabel"] p {
            font-size: 0.87rem !important;
            font-weight: 550 !important;
        }

        [data-testid="stMetricValue"] {
            font-size: clamp(1.5rem, 2vw, 2.15rem) !important;
            font-weight: 750 !important;
            letter-spacing: -0.035em !important;
            font-variant-numeric: tabular-nums;
        }

        /* ============================================
           5. CUSTOM KPI CARDS
           ============================================ */

        .fintech-overview-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(min(100%, 230px), 1fr));
            gap: 1rem;
            width: 100%;
            margin-bottom: 1.5rem;
        }

        .fintech-overview-card {
            box-sizing: border-box;
            min-width: 0;
            min-height: 145px;
            padding: 1.15rem;
            border: 1px solid
                color-mix(in srgb, currentColor 18%, transparent);
            border-radius: 14px;
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }

        .fintech-overview-card-top {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 0;
        }

        .fintech-overview-icon,
        .fintech-kpi-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 40px;
            width: 40px;
            height: 40px;
            border-radius: 11px;
            background: rgba(96, 165, 250, 0.12);
            font-size: 1.35rem;
        }

        .fintech-overview-label,
        .fintech-kpi-label {
            font-size: 0.86rem;
            font-weight: 600;
            line-height: 1.35;
            opacity: 0.8;
        }

        .fintech-overview-value,
        .fintech-kpi-value {
            min-width: 0;
            max-width: 100%;
            font-size: clamp(1.15rem, 2vw, 1.85rem);
            font-weight: 800;
            letter-spacing: -0.04em;
            line-height: 1.2;
            white-space: nowrap;
            overflow-x: auto;
            font-variant-numeric: tabular-nums;
        }

        .fintech-overview-caption {
            font-size: 0.82rem;
            line-height: 1.4;
            margin-top: auto;
            opacity: 0.75;
        }

        .st-key-kpi_card_0,
        .st-key-kpi_card_1,
        .st-key-kpi_card_2,
        .st-key-kpi_card_3 {
            min-width: 0;
        }

        /* ============================================
        6. PRICING RISK CARDS
        ============================================ */

        /* Shared card styling */
        .st-key-pricing_risk_assessed,
        .st-key-pricing_risk_negative,
        .st-key-pricing_risk_nonnegative {
            border-radius: 14px;
            padding: 1rem;
            min-height: 155px;
            box-sizing: border-box;
        }

        /* Blue — Menu Items Assessed */
        .st-key-pricing_risk_assessed {
            background-color: rgba(96, 165, 250, 0.14);
            border: 1px solid rgba(96, 165, 250, 0.60);
        }

        /* Rose — Negative Worst-Case */
        .st-key-pricing_risk_negative {
            background-color: rgba(251, 113, 133, 0.14);
            border: 1px solid rgba(251, 113, 133, 0.60);
        }

        /* Green — No Simulated Downside Loss */
        .st-key-pricing_risk_nonnegative {
            background-color: rgba(52, 211, 153, 0.14);
            border: 1px solid rgba(52, 211, 153, 0.60);
        }

        /* Prevent nested metric backgrounds from covering card colors */
        .st-key-pricing_risk_assessed [data-testid="stMetric"],
        .st-key-pricing_risk_negative [data-testid="stMetric"],
        .st-key-pricing_risk_nonnegative [data-testid="stMetric"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }

        /* Larger, prominent KPI values */
        .st-key-pricing_risk_assessed [data-testid="stMetricValue"],
        .st-key-pricing_risk_negative [data-testid="stMetricValue"],
        .st-key-pricing_risk_nonnegative [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.04em;
            font-variant-numeric: tabular-nums;
        }

        /* Keep labels readable on smaller screens */
        .st-key-pricing_risk_assessed [data-testid="stMetricLabel"] p,
        .st-key-pricing_risk_negative [data-testid="stMetricLabel"] p,
        .st-key-pricing_risk_nonnegative [data-testid="stMetricLabel"] p {
            white-space: normal !important;
            overflow-wrap: break-word;
        }

        /* Responsive card sizing */
        @media (max-width: 900px) {
            .st-key-pricing_risk_assessed,
            .st-key-pricing_risk_negative,
            .st-key-pricing_risk_nonnegative {
                min-height: 130px;
                padding: 0.85rem;
            }

            .st-key-pricing_risk_assessed [data-testid="stMetricValue"],
            .st-key-pricing_risk_negative [data-testid="stMetricValue"],
            .st-key-pricing_risk_nonnegative [data-testid="stMetricValue"] {
                font-size: 2rem !important;
            }
        }
        
        /* Semantic KPI number colors */

        /* Blue number — Menu Items Assessed */
        .st-key-pricing_risk_assessed [data-testid="stMetricValue"] {
            color: #3B82F6 !important;
        }

        /* Red number — Negative Worst-Case */
        .st-key-pricing_risk_negative [data-testid="stMetricValue"] {
            color: #E11D48 !important;
        }

        /* Green number — No Simulated Downside Loss */
        .st-key-pricing_risk_nonnegative [data-testid="stMetricValue"] {
            color: #059669 !important;
        }


        /* ============================================
           7. EXPANDERS, TABLES, CHARTS
           ============================================ */

        [data-testid="stExpander"] {
            border-radius: 14px;
            overflow: hidden;
        }

        [data-testid="stExpander"] summary {
            font-size: 0.93rem !important;
            font-weight: 620 !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        [data-testid="stPlotlyChart"],
        [data-testid="stVegaLiteChart"],
        [data-testid="stArrowVegaLiteChart"] {
            border: 1px solid
                color-mix(in srgb, currentColor 15%, transparent);
            border-radius: 14px;
            padding: 0.7rem;
            overflow: hidden;
        }

        /* ============================================
           8. TABS AND DIVIDERS
           ============================================ */

        [data-testid="stTabs"] {
            margin-top: 0.8rem;
        }

        [data-testid="stMain"] button[data-baseweb="tab"] {
            font-size: 0.93rem !important;
            font-weight: 600 !important;
            padding: 0.85rem 1rem !important;
        }

        [data-testid="stMain"] hr {
            margin: 1.6rem 0;
        }

        /* ============================================
           9. RESPONSIVE DESIGN
           ============================================ */

        @media (max-width: 1100px) {
            [data-testid="stHorizontalBlock"]:has(
                [data-testid="stMetric"]
            ) {
                flex-wrap: wrap !important;
            }

            [data-testid="stHorizontalBlock"]:has(
                [data-testid="stMetric"]
            ) > [data-testid="stColumn"] {
                flex: 1 1 230px !important;
                min-width: min(100%, 230px) !important;
            }
        }

        @media (max-width: 900px) {
            [data-testid="stMain"] .block-container {
                padding: 1.5rem 1rem 3rem;
            }
        }

        @media (max-width: 640px) {
            [data-testid="stMain"] .block-container {
                padding: 1rem 0.8rem 2.5rem;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.4rem !important;
            }

            .fintech-overview-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            [data-testid="stButton"] button {
                transition: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
