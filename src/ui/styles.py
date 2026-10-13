"""Modern Fintech + Pricing Intelligence dashboard styling"""
import streamlit as st


def apply_dashboard_styles() -> None:
    """Apply a consistent, responsive fintech dashboard theme."""
    st.markdown(
        """
        <style>
        /* ============================================
           1. DESIGN SYSTEM
           ============================================ */
        :root {
            /* Streamlit theme colors with compatibility fallbacks */
            --fintech-bg: var(
                --st-background-color,
                var(--background-color, #F8FAFC)
            );

            --fintech-sidebar: var(
                --st-secondary-background-color,
                var(--secondary-background-color, #FFFFFF)
            );

            --fintech-card: var(
                --st-secondary-background-color,
                var(--secondary-background-color, #FFFFFF)
            );

            --fintech-card-hover: color-mix(
                in srgb,
                var(--fintech-card) 92%,
                var(--fintech-blue)
            );

            --fintech-border: var(
                --st-border-color,
                color-mix(
                    in srgb,
                    var(--fintech-text) 18%,
                    transparent
                )
            );

            --fintech-text: var(
                --st-text-color,
                var(--text-color, #0F172A)
            );

            --fintech-muted: color-mix(
                in srgb,
                var(--fintech-text) 62%,
                var(--fintech-bg)
            );

            --fintech-blue: var(
                --st-primary-color,
                var(--primary-color, #2563EB)
            );

            --fintech-green: #10B981;
            --fintech-yellow: #F59E0B;
            --fintech-red: #F43F5E;
            --fintech-radius: 14px;
        }

        /* ============================================
           2. APP BACKGROUND AND CONTENT WIDTH
           ============================================ */
        .stApp {
            background: var(--fintech-bg);
            color: var(--fintech-text);
        }
        [data-testid="stAppViewContainer"] {
            background: var(--fintech-bg);
        }
        [data-testid="stMain"] {
            background: var(--fintech-bg);
        }
        [data-testid="stMain"] .block-container {
            max-width: 1450px;
            padding: 2.25rem 2.5rem 5rem;
        }
        /* ============================================
           3. TYPOGRAPHY
           ============================================ */
        [data-testid="stMain"] h1 {
            color: var(--fintech-text) !important;
            font-size: clamp(2rem, 3vw, 2.8rem) !important;
            font-weight: 750 !important;
            letter-spacing: -0.045em !important;
            line-height: 1.16 !important;
        }
        [data-testid="stMain"] h2 {
            color: var(--fintech-text) !important;
            font-size: clamp(1.5rem, 2vw, 2rem) !important;
            font-weight: 720 !important;
            letter-spacing: -0.035em !important;
            line-height: 1.25 !important;
        }
        [data-testid="stMain"] h3 {
            color: var(--fintech-text) !important;
            font-size: 1.3rem !important;
            font-weight: 680 !important;
            letter-spacing: -0.025em !important;
            line-height: 1.3 !important;
        }
        [data-testid="stMain"] h4 {
            color: var(--fintech-text) !important;
            font-size: 1.1rem !important;
            font-weight: 650 !important;
        }
        [data-testid="stMain"]
        [data-testid="stMarkdownContainer"] p {
            font-size: 0.97rem;
            line-height: 1.65;
        }
        [data-testid="stCaptionContainer"] p {
            color: var(--fintech-muted) !important;
            font-size: 0.86rem !important;
            line-height: 1.55 !important;
        }
        /* ============================================
           4. SIDEBAR
           ============================================ */
        [data-testid="stSidebar"] {
            background: var(--fintech-sidebar);
            border-right: 1px solid var(--fintech-border);
        }
        [data-testid="stSidebar"] > div {
            background: var(--fintech-sidebar);
        }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--fintech-text) !important;
            letter-spacing: -0.025em;
        }
        [data-testid="stSidebar"]
        [data-testid="stWidgetLabel"] p {
            font-size: 0.87rem !important;
            font-weight: 600 !important;
            color: var(--fintech-text) !important;
        }
        [data-testid="stSidebar"]
        [data-testid="stCaptionContainer"] p {
            color: var(--fintech-muted) !important;
        }
        /* ============================================
           5. INPUTS AND SELECT BOXES
           ============================================ */
        [data-baseweb="select"] > div {
            background-color: var(--fintech-card) !important;
            border: 1px solid var(--fintech-border) !important;
            border-radius: 10px !important;
            min-height: 43px;
        }
        [data-baseweb="select"] > div:hover {
            border-color: var(--fintech-blue) !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
            background: var(--fintech-card) !important;
            border: 1px solid var(--fintech-border) !important;
            border-radius: 10px !important;
            color: var(--fintech-text) !important;
        }
        [data-testid="stWidgetLabel"] p {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }
        /* ============================================
           6. SLIDERS AND INTERACTIVE CONTROLS
           ============================================ */
        [data-testid="stSlider"] {
            padding-top: 0.35rem;
            padding-bottom: 0.55rem;
        }
        [data-testid="stSlider"] [role="slider"] {
            box-shadow: 0 0 0 4px rgba(96,165,250,0.13);
        }
        /* ============================================
           7. BUTTONS
           ============================================ */
        [data-testid="stButton"] button {
            border-radius: 10px !important;
            min-height: 43px !important;
            padding: 0.55rem 1.1rem !important;
            font-weight: 650 !important;
            font-size: 0.9rem !important;
            transition:
                background 160ms ease,
                border-color 160ms ease,
                transform 160ms ease;
        }
        [data-testid="stButton"] button[kind="primary"] {
            background: #2563EB !important;
            border: 1px solid #3B82F6 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stButton"] button[kind="primary"]:hover {
            background: #1D4ED8 !important;
            border-color: #60A5FA !important;
        }
        [data-testid="stButton"] button:focus-visible {
            outline: 2px solid var(--fintech-blue);
            outline-offset: 2px;
        }
        /* ============================================
           8. KPI METRICS AND CARDS
           ============================================ */
        [data-testid="stMetric"] {
            background: var(--fintech-card);
            border: 1px solid var(--fintech-border);
            border-radius: var(--fintech-radius);
            padding: 1.2rem 1.35rem;
        }
        [data-testid="stMetricLabel"] p {
            font-size: 0.87rem !important;
            font-weight: 550 !important;
            color: var(--fintech-muted) !important;
        }
        [data-testid="stMetricValue"] {
            color: var(--fintech-text) !important;
            font-size: clamp(1.5rem, 2vw, 2.15rem) !important;
            font-weight: 750 !important;
            letter-spacing: -0.035em !important;
            overflow-wrap: anywhere;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.85rem !important;
        }
        /* Custom KPI elements used by the app */
        .fintech-kpi-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: rgba(96,165,250,0.12);
            color: var(--fintech-blue);
            font-size: 1.45rem;
        }
        .fintech-kpi-label {
            color: var(--fintech-muted);
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            line-height: 1.4;
        }
        .fintech-kpi-value {
            color: var(--fintech-text);
            font-size: 1.9rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.04em;
            line-height: 1.2;
            margin-top: 0.35rem;
            overflow-wrap: anywhere;
        }
        /* ============================================
           9. TABS
           ============================================ */
        [data-testid="stTabs"] {
            margin-top: 0.8rem;
        }
        [data-testid="stMain"] button[data-baseweb="tab"] {
            color: var(--fintech-muted) !important;
            font-size: 0.93rem !important;
            font-weight: 600 !important;
            padding: 0.85rem 1rem !important;
        }
        [data-testid="stMain"]
        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--fintech-blue) !important;
        }
        /* ============================================
           10. DATA TABLES
           ============================================ */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--fintech-border);
            border-radius: var(--fintech-radius);
            overflow: hidden;
            background: var(--fintech-card);
        }
        [data-testid="stDataFrame"] > div {
            border-radius: var(--fintech-radius);
        }
        /* ============================================
           11. EXPANDERS
           ============================================ */
        [data-testid="stExpander"] {
            background: var(--fintech-card);
            border: 1px solid var(--fintech-border);
            border-radius: var(--fintech-radius);
            overflow: hidden;
        }
        [data-testid="stExpander"] summary {
            font-size: 0.93rem !important;
            font-weight: 620 !important;
            padding: 0.35rem 0.2rem;
        }
        [data-testid="stExpander"] summary:hover {
            color: var(--fintech-blue);
        }
        /* ============================================
           12. CHARTS AND ANALYTICS
           ============================================ */
        [data-testid="stPlotlyChart"],
        [data-testid="stVegaLiteChart"],
        [data-testid="stArrowVegaLiteChart"] {
            background: var(--fintech-card);
            border: 1px solid var(--fintech-border);
            border-radius: var(--fintech-radius);
            padding: 0.7rem;
            overflow: hidden;
        }
        /* ============================================
           13. ALERTS
           ============================================ */
        [data-testid="stAlert"] {
            border-radius: 11px;
            border-width: 1px;
        }
        /* ============================================
           14. CUSTOM SECTION DIVIDERS
           ============================================ */
        [data-testid="stMain"] hr {
            border-color: var(--fintech-border);
            margin: 1.6rem 0;
        }
        /* ============================================
           15. RESPONSIVE DESIGN
           ============================================ */
        @media (max-width: 900px) {
            [data-testid="stMain"] .block-container {
                padding: 1.5rem 1rem 3rem;
            }
            [data-testid="stMain"] h1 {
                font-size: 1.9rem !important;
            }
            [data-testid="stMain"] h2 {
                font-size: 1.5rem !important;
            }
            [data-testid="stMain"] h3 {
                font-size: 1.2rem !important;
            }
            [data-testid="stMetric"] {
                padding: 0.9rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.5rem !important;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            [data-testid="stButton"] button {
                transition: none !important;
            }
        }
        /* Pricing Risk Overview: three semantic card styles */
        .st-key-pricing_risk_assessed,
        .st-key-pricing_risk_negative,
        .st-key-pricing_risk_nonnegative {
            border-radius: 14px;
            padding: 1rem;
            min-height: 155px;
        }
        
        /* Avoid a second card border inside the outer card */
        .st-key-pricing_risk_assessed [data-testid="stMetric"],
        .st-key-pricing_risk_negative [data-testid="stMetric"],
        .st-key-pricing_risk_nonnegative [data-testid="stMetric"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        
        /* Blue: assessed items */
        .st-key-pricing_risk_assessed {
            background: color-mix(
                in srgb,
                var(--fintech-card) 92%,
                #60A5FA
            );
            border: 1px solid color-mix(
                in srgb,
                var(--fintech-border) 70%,
                #60A5FA
            );
        }
        .st-key-pricing_risk_assessed [data-testid="stMetricValue"] {
            color: var(--st-blue-text-color, #2563EB) !important;
        }
        
        /* Rose: negative worst-case */
        .st-key-pricing_risk_negative {
            background: color-mix(
                in srgb,
                var(--fintech-card) 92%,
                #FB7185
            );
            border: 1px solid color-mix(
                in srgb,
                var(--fintech-border) 70%,
                #FB7185
            );
        }
        .st-key-pricing_risk_negative [data-testid="stMetricValue"] {
            color: var(--st-red-text-color, #BE123C) !important;
        }
        
        /* Teal: no loss in tested scenarios */
        .st-key-pricing_risk_nonnegative {
            background: color-mix(
                in srgb,
                var(--fintech-card) 92%,
                #34D399
            );
            border: 1px solid color-mix(
                in srgb,
                var(--fintech-border) 70%,
                #34D399
            );
        }
        .st-key-pricing_risk_nonnegative [data-testid="stMetricValue"] {
           color: var(--st-green-text-color, #047857) !important;
        }
        
        /* Larger, more prominent KPI values */
        .st-key-pricing_risk_assessed [data-testid="stMetricValue"],
        .st-key-pricing_risk_negative [data-testid="stMetricValue"],
        .st-key-pricing_risk_nonnegative [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.04em;
        }
        @media (max-width: 900px) {
            .st-key-pricing_risk_assessed,
            .st-key-pricing_risk_negative,
            .st-key-pricing_risk_nonnegative {
                min-height: 130px;
            }
        }

        /* ============================================
           16. RESPONSIVE CONTENT-SAFE OVERRIDES
           ============================================ */

        /* Never split currency or quantity figures mid-number. */
        [data-testid="stMetricValue"],
        .fintech-kpi-value {
            overflow-wrap: normal !important;
            word-break: normal !important;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }

        /* KPI columns may occupy multiple rows instead of becoming
           narrow enough to break large values. The rule applies only
           to rows containing metrics or the overview's custom KPIs. */
        @media (max-width: 1100px) {
            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]),
            [data-testid="stHorizontalBlock"]:has(.fintech-kpi-value),
            [data-testid="stHorizontalBlock"]:has(.st-key-pricing_risk_assessed) {
                flex-wrap: wrap !important;
            }

            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"],
            [data-testid="stHorizontalBlock"]:has(.fintech-kpi-value) > [data-testid="stColumn"],
            [data-testid="stHorizontalBlock"]:has(.st-key-pricing_risk_assessed) > [data-testid="stColumn"] {
                flex: 1 1 230px !important;
                width: auto !important;
                min-width: min(100%, 230px) !important;
            }

            [data-testid="stMetricValue"],
            .fintech-kpi-value {
                font-size: clamp(1.2rem, 2.3vw, 1.85rem) !important;
            }

            /* Don't let the risk-card label hide its meaning. */
            .st-key-pricing_risk_assessed [data-testid="stMetricLabel"] p,
            .st-key-pricing_risk_negative [data-testid="stMetricLabel"] p,
            .st-key-pricing_risk_nonnegative [data-testid="stMetricLabel"] p {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: break-word !important;
            }

            .st-key-pricing_risk_assessed,
            .st-key-pricing_risk_negative,
            .st-key-pricing_risk_nonnegative {
                min-height: 145px;
            }
        }

        @media (max-width: 640px) {
            [data-testid="stMain"] .block-container {
                padding: 1rem 0.8rem 2.5rem;
            }

            [data-testid="stMetric"],
            .st-key-pricing_risk_assessed,
            .st-key-pricing_risk_negative,
            .st-key-pricing_risk_nonnegative {
                padding: 0.85rem;
            }

            [data-testid="stMetricValue"],
            .fintech-kpi-value {
                font-size: clamp(1.15rem, 5vw, 1.65rem) !important;
            }

            /* Keep dense financial tables scrollable, not squashed. */
            [data-testid="stDataFrame"] {
                max-width: 100%;
            }

            [data-testid="stVegaLiteChart"],
            [data-testid="stArrowVegaLiteChart"] {
                max-width: 100%;
                overflow-x: auto;
                padding: 0.35rem;
            }
        }

        /* Responsive overview KPI cards */
P
        .fintech-overview-grid {
            display: grid;
            grid-template-columns: repeat(
                auto-fit,
                minmax(min(100%, 230px), 1fr)
            );
            gap: 1rem;
            width: 100%;
            margin-bottom: 1.5rem;
        }

        .fintech-overview-card {
            box-sizing: border-box;
            min-width: 0;
            min-height: 145px;
            padding: 1.15rem;
            border: 1px solid var(--fintech-border) !important;
            border-radius: 14px;
            background: var(--fintech-card) !important;
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

        .fintech-overview-icon {
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

        .fintech-overview-label {
            min-width: 0;
            color: var(--fintech-muted);
            font-size: 0.86rem;
            font-weight: 600;
            line-height: 1.35;
        }

        .fintech-overview-value {
            min-width: 0;
            max-width: 100%;
            color: var(--fintech-text);
            font-size: clamp(1.15rem, 2vw, 1.85rem);
            font-weight: 800;
            letter-spacing: -0.04em;
            line-height: 1.2;
            white-space: nowrap;
            overflow-x: auto;
            font-variant-numeric: tabular-nums;
        }

        .fintech-overview-caption {
            color: var(--fintech-muted);
            font-size: 0.82rem;
            line-height: 1.4;
            margin-top: auto;
        }

        @media (max-width: 600px) {
            .fintech-overview-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Preserve original four-column KPI layout */

        .st-key-kpi_card_0,
        .st-key-kpi_card_1,
        .st-key-kpi_card_2,
        .st-key-kpi_card_3 {
            min-width: 0;
        }

        /* Prevent financial values from splitting across lines */
        .st-key-kpi_card_0 .fintech-kpi-value,
        .st-key-kpi_card_1 .fintech-kpi-value,
        .st-key-kpi_card_2 .fintech-kpi-value,
        .st-key-kpi_card_3 .fintech-kpi-value {
            font-size: clamp(0.8rem, 1.3vw, 1.6rem) !important;
            white-space: nowrap;
            overflow-x: auto;
            overflow-wrap: normal;
            letter-spacing: -0.04em;
        }

        /* Keep labels legible inside narrower cards */
        .st-key-kpi_card_0 .fintech-kpi-label,
        .st-key-kpi_card_1 .fintech-kpi-label,
        .st-key-kpi_card_2 .fintech-kpi-label,
        .st-key-kpi_card_3 .fintech-kpi-label {
            font-size: 0.8rem !important;
        }

        /* Smaller typography when available screen space is limited */
        @media (max-width: 1100px) {
            .st-key-kpi_card_0 .fintech-kpi-value,
            .st-key-kpi_card_1 .fintech-kpi-value,
            .st-key-kpi_card_2 .fintech-kpi-value,
            .st-key-kpi_card_3 .fintech-kpi-value {
                font-size: 0.9rem !important;
            }
        }
        
        </style>
        """,
        unsafe_allow_html=True,
    )