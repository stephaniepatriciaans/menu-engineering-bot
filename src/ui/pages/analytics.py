"""Streamlit workflow module extracted from app.py."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components import render_business_header, render_kpi_cards
from ui.pages.data_quality import QualityData
from ui.pages.data_setup import SetupData
from ui.sections.day_analysis import render_day_analysis
from ui.sections.elasticity_reliability import render_elasticity_reliability
from ui.sections.hourly_analysis import render_hourly_analysis
from ui.sections.menu_item_explorer import render_menu_item_explorer
from ui.sections.menu_quadrants import render_menu_quadrants
from ui.sections.model_evaluation import render_model_evaluation
from ui.sections.popular_items import render_popular_items
from ui.sections.pricing_recommendations import render_pricing_recommendations
from ui.sections.sales_trends import render_sales_trends
from ui.sidebar import SidebarSettings


def render_analytics(setup: SetupData, quality: QualityData, settings: SidebarSettings) -> pd.DataFrame:
    df = quality.df
    summary = quality.summary
    capabilities = quality.capabilities
    refund_candidates_df = quality.refund_candidates_df
    cost_is_assumption = quality.cost_is_assumption
    start_date = quality.start_date
    end_date = quality.end_date
    business_name = setup.business_name
    currency = settings.currency

    if quality.financial_preview is not None:
        preview = quality.financial_preview
        amount = preview.get("eligible_sales_revenue")
        st.subheader("POS sales reconciliation (separate from dashboard KPIs)")
        if amount is None:
            st.info("Verified eligible-sales revenue is unavailable for this price convention.")
        else:
            st.metric("Eligible-sales revenue (excluding review rows)", f"${amount:,.2f}")
            st.caption(
                "Operator-confirmed sale conventions" if preview.get("conventions_verified")
                else "Unverified preview. Not net revenue; excludes candidate refunds and cancellations."
            )
        st.caption("Main KPIs, profitability, elasticity and pricing still use the existing sales-only data pipeline.")

    # Calculate Analytics
    # ================================================================

    render_business_header(
        business_name=business_name,
        start_date=start_date,
        end_date=end_date,
        menu_item_count=df["item"].nunique(),
    )

    # Reusable KPI cards from src/ui/components.py
    render_kpi_cards(
        df,
        currency,
        has_refund_candidates=not refund_candidates_df.empty,
    )

    # ================================================================
    # Display Dashboard
    # ================================================================

    st.header("Sales Analytics")
    analysis_tabs = st.tabs(
        [
            "Revenue & Popularity",
            "Elasticity Reliability",
            "Menu Quadrants",
            "Item Detail",
            "Model Evaluation",
        ]
    )

    with analysis_tabs[0]:
        revenue_tabs = st.tabs([
            "Sales Trends",
            "Day Analysis",
            "Hourly Analysis",
            "Popular Items",
        ])


        # ================================================================
        # Feature 9: Sales Trends navigation tab
        # ================================================================
        with revenue_tabs[0]:
            render_sales_trends(df, currency)


        # ================================================================
        # Feature 9: Popular Items navigation tab
        # ================================================================
        with revenue_tabs[3]:
            render_popular_items(summary)


        # ================================================================
        # Feature 9: Day Analysis navigation tab
        # ================================================================
        with revenue_tabs[1]:
            render_day_analysis(df, currency)


        # ================================================================
        # HOURLY ANALYSIS TAB
        # ================================================================
        with revenue_tabs[2]:
            render_hourly_analysis(df, currency)


    # ================================================================
    # ELASTICITY RELIABILITY TAB
    # ================================================================
    with analysis_tabs[1]:
        render_elasticity_reliability(summary)


    # ================================================================
    # MENU ENGINEERING QUADRANTS TAB
    # ================================================================
    with analysis_tabs[2]:
        render_menu_quadrants(summary, capabilities, cost_is_assumption)


    # ================================================================
    # MENU ITEM EXPLORER TAB
    # ================================================================
    with analysis_tabs[3]:
        render_menu_item_explorer(summary, capabilities, currency)


    # ================================================================
    # MODEL EVALUATION TAB
    # ================================================================
    with analysis_tabs[4]:
        render_model_evaluation(df)


    # ================================================================
    # Pricing Recommendations
    # ================================================================
    with st.expander("Pricing simulation limits", expanded=False):
        left_limit, right_limit = st.columns(2)
        with left_limit:
            max_decrease = st.slider(
                "Maximum price decrease",
                min_value=0,
                max_value=30,
                value=settings.max_decrease,
                step=5,
                format="-%d%%",
                key="analytics_max_price_decrease",
            )
        with right_limit:
            max_increase = st.slider(
                "Maximum price increase",
                min_value=0,
                max_value=30,
                value=settings.max_increase,
                step=5,
                format="+%d%%",
                key="analytics_max_price_increase",
            )

    moves = render_pricing_recommendations(
        summary=summary,
        capabilities=capabilities,
        currency=currency,
        max_decrease=max_decrease,
        max_increase=max_increase,
        cost_is_assumption=cost_is_assumption,
    )

    return moves
