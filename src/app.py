"""Streamlit front end for the universal Menu Engineering Bot"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from pdf_report import generate_memo_pdf

load_dotenv()

sys.path.append(os.path.dirname(__file__))

# ================================================================
# FROM ANALYSIS
# ================================================================
from analysis import (
    build_item_summary,
    load_sales,
)

# ================================================================
# FROM CONFIG
# ================================================================
from config import (
    CANONICAL_FIELDS,
)

# ================================================================
# FROM DASHBOARD UTILS
# ================================================================
from dashboard_utils import (
    add_transaction_datetime,
)

# ================================================================
# FROM DATA ADAPTER
# ================================================================
from data_adapter import (
    adapt_to_canonical,
    validate_mapping,
)
from ui.capabilities import build_capability_report

# ================================================================
# FROM UI
# ================================================================
from ui.components import (
    render_business_header,
    render_kpi_cards,
    render_validation_overview,
)
from ui.cost_settings import render_cost_settings
from ui.data_upload import (
    load_uploaded_sales,
    render_source_audit,
)
from ui.filters import render_category_filter, render_date_filter
from ui.mapping import mapping_selectors

# ================================================================
# FROM UI SECTIONS
# ================================================================
from ui.sections.ai_decision_memo import render_ai_decision_memo
from ui.sections.day_analysis import render_day_analysis
from ui.sections.elasticity_reliability import render_elasticity_reliability
from ui.sections.hourly_analysis import render_hourly_analysis
from ui.sections.menu_item_explorer import render_menu_item_explorer
from ui.sections.menu_quadrants import render_menu_quadrants
from ui.sections.model_evaluation import render_model_evaluation
from ui.sections.popular_items import render_popular_items
from ui.sections.pricing_recommendations import render_pricing_recommendations
from ui.sections.sales_trends import render_sales_trends

# ================================================================
from ui.sidebar import render_sidebar
from ui.styles import apply_dashboard_styles

# ================================================================
# FROM VALIDATION
# ================================================================
from validation import (
    determine_capabilities,
    validate_sales_df,
)

# ================================================================
st.set_page_config(
    page_title="Menu Engineering Bot",
    page_icon="📊",
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

business_name = settings.business_name
dataset_name = settings.dataset_name
currency = settings.currency

max_decrease = settings.max_decrease
max_increase = settings.max_increase

source = settings.source
uploaded = settings.uploaded


# ================================================================
# Load dataset
# ================================================================

raw_df: pd.DataFrame | None = None

mapping: dict[str, str | None] = {
    field: None for field in CANONICAL_FIELDS
}

if source == "Full Demo Dataset — Synthetic Cafe":
    demo_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "cafe_sales.csv",
    )

    raw_df = load_sales(demo_path)

    # Map only columns that actually exist in the demo dataset.
    # Optional fields, such as transaction_time, may be missing.
    mapping = {
        field: field if field in raw_df.columns else None
        for field in CANONICAL_FIELDS
    }

    business_name = (
        business_name
        if business_name != "My Food-Service Business"
        else "Synthetic Cafe"
    )

    dataset_name = (
        dataset_name
        if dataset_name != "Menu Sales Dataset"
        else "Full Demo Dataset — Synthetic Cafe"
    )

    st.info(
        "Using the bundled synthetic dataset with complete "
        "price, cost, and quantity fields."
    )

elif uploaded is not None:
    try:
        raw_df, source_audit_messages = load_uploaded_sales(
            uploaded
        )

        render_source_audit(source_audit_messages)

    except Exception as exc:  # noqa: BLE001
        # CSV uploads can fail during parsing, decoding, or source auditing.
        # Show a user-friendly error instead of crashing the dashboard.
        st.error(
            f"Could not read or audit the CSV: {exc}"
        )
        st.stop()

else:
    st.info(
        "Upload a CSV to start"
        "You do not need to rename its columns first"
    )
    st.stop()


# ================================================================
# Feature 2: Data Setup & Column Mapping
# ================================================================

with st.expander("⚙️ Data Setup & Column Mapping", expanded=False):

    if source == "Upload my own CSV":
        st.write(
            "Automatic detection has preselected likely matches. "
            "Correct any mapping that is wrong."
        )

        with st.expander("Preview raw columns", expanded=False):
            st.dataframe(
                raw_df.head(10),
                width="stretch",
            )

        mapping = mapping_selectors(raw_df)

    else:
        st.success(
            "Bundled demo columns already match the canonical schema."
        )


# ================================================================
# Validate column mapping — visible outside expander
# ================================================================

mapping_errors = validate_mapping(mapping, raw_df.columns)

if mapping_errors:
    st.error(
        "Dataset column mapping needs attention. "
        "Open Data Setup & Column Mapping to correct the selections."
    )

    for error in mapping_errors:
        st.error(error)

    st.stop()


# ================================================================
# Adapt dataset to canonical schema
# ================================================================

try:
    canonical_df, adapter_warnings = adapt_to_canonical(
        raw_df,
        mapping,
    )

except ValueError as exc:
    st.error(
        "The dataset could not be standardized. "
        "Please review the column mapping."
    )
    st.error(str(exc))
    st.stop()


# ================================================================
# Optional cost handling
# ================================================================

canonical_df, cost_basis, cost_is_assumption = (
    render_cost_settings(canonical_df)
)

# ================================================================
# Feature 3: Validate Dataset
# ================================================================

st.subheader("Dataset Validation")

# Validate the canonical dataframe.
df, errors, validation_warnings = validate_sales_df(
    canonical_df
)

# Blocking errors must always remain visible.
if errors or df is None:
    st.error(
        "Dataset validation failed. "
        "Please review the errors below."
    )

    for error in errors:
        st.error(error)

    st.stop()

render_validation_overview(
    df=df,
    adapter_warnings=adapter_warnings,
    validation_warnings=validation_warnings,
)

# ================================================================
# Date range filtering
# ================================================================
with st.expander("⚙️ Sales Filters", expanded=False):

    st.subheader("Filter sales by date")

    # Date filtering is handled by the reusable UI module.
    df, start_date, end_date = render_date_filter(df)

    # Category Filters
    df = render_category_filter(df)

    # Recalculate capabilities and item summaries
    # using the selected categories.
    capabilities = determine_capabilities(df)
    summary = build_item_summary(df)

    # This is stricter than simply seeing multiple prices: it reflects whether the
    # estimator actually accepted at least one item-level historical estimate.
    capabilities["historical_elasticity_estimation"] = bool(
        not summary.empty and (summary["elasticity_source"] == "estimated").any()
    )


    # ================================================================
    # Feature 7: Create transaction timestamps for hourly analysis.
    # ================================================================
    df = add_transaction_datetime(df)

    valid_timestamp_count = int(
        df["transaction_datetime"].notna().sum()
    )

    if valid_timestamp_count > 0:
        st.caption(
            f"Transaction times available for "
            f"{valid_timestamp_count:,} of {len(df):,} sales rows."
        )
    else:
        st.info(
            "This dataset does not contain usable transaction times. "
            "Daily and category analysis remain available, "
            "but hourly analysis will be unavailable."
        )


# ================================================================
# Dataset capabilities
# ================================================================
# Build the dataset capability report from the filtered summary
# Reporting logic lives in ui/capabilities.py

capability_text = build_capability_report(
    summary=summary,
    capabilities=capabilities,
    cost_is_assumption=cost_is_assumption,
)


# ================================================================
# Active Filter Summary
# ================================================================
# Count the food groups remaining after category filtering
active_group_count = df["category_group"].nunique()

st.caption(
    f"📅 {start_date:%b %d, %Y} – {end_date:%b %d, %Y}"
    f"   |   🗂️ {active_group_count} food groups"
    f"   |   🧾 {len(df):,} sales records"
)


# ================================================================
# Modern Fintech — Collapsible Dataset Capabilities
# ================================================================

with st.expander("View Dataset Capabilities", expanded=False):
    st.caption(
        "See which analyses are supported by your dataset "
        "and why certain features may be unavailable."
    )

    for capability in capability_text:
        if capability.startswith("✓ "):
            available = True
            description = capability[2:]
        elif capability.startswith("✗ "):
            available = False
            description = capability[2:]
        else:
            available = False
            description = capability

        # Separate the capability name from its explanation.
        name, separator, reason = description.partition(" — ")

        with st.container(border=True):
            status_col, content_col = st.columns(
                [1, 12],
                gap="small",
                vertical_alignment="center",
            )

            with status_col:
                if available:
                    st.markdown("🟢")
                else:
                    st.markdown("🟠")

            with content_col:
                st.markdown(f"**{name}**")

                if separator and reason:
                    st.caption(reason)


# ================================================================
# Calculate Analytics
# ================================================================

render_business_header(
    business_name=business_name,
    start_date=start_date,
    end_date=end_date,
    menu_item_count=df["item"].nunique(),
)

# Reusable KPI cards from src/ui/components.py
render_kpi_cards(df, currency)

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
moves = render_pricing_recommendations(
    summary=summary,
    capabilities=capabilities,
    currency=currency,
    max_decrease=max_decrease,
    max_increase=max_increase,
    cost_is_assumption=cost_is_assumption,
)


# ================================================================
# 7. Generate AI decision memo
# ================================================================
render_ai_decision_memo(
    summary=summary,
    moves=moves,
    business_name=business_name,
    dataset_name=dataset_name,
    currency=currency,
    cost_basis=cost_basis,
    cost_is_assumption=cost_is_assumption,
    capabilities=capabilities,
    generate_memo_pdf=generate_memo_pdf,
)
