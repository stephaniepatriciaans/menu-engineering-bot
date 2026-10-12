"""Streamlit front end for the universal Menu Engineering Bot."""

from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(__file__))

from analysis import build_item_summary, load_sales, recommend_price_moves

from dashboard_utils import (
    SORTING_OPTIONS,
    sort_menu_items,
    filter_by_date_range,
    aggregate_sales_by_period,
    compare_weekday_weekend,
    analyze_day_of_week,
    add_transaction_datetime,
    analyze_peak_hours,
    analyze_hourly_revenue,
)

from config import (
    CANONICAL_FIELDS,
    CURRENCY_CONFIG,
    CATEGORY_GROUPS,
    category_group,
    classify_menu_item,
    format_currency,
)

from data_adapter import (
    NOT_AVAILABLE,
    KNOWN_MAPPING_PRESETS,
    apply_known_preset,
    mapping_confidence,
    adapt_to_canonical,
    apply_estimated_cost_percentage,
    detect_column_mapping,
    merge_cost_reference,
    read_delimited_csv,
    validate_mapping,
)
from validation import (
    determine_capabilities,
    validate_sales_df,
    audit_source_transactions,
)

from pdf_report import generate_memo_pdf

from ui.components import (
    render_kpi_cards,
    render_business_header,
    render_data_quality_summary,
    render_validation_overview,
    render_chart_header,
)
from ui.styles import apply_dashboard_styles
from ui.charts import style_chart
from ui.mapping import mapping_selectors
from ui.sidebar import render_sidebar
from ui.cost_settings import render_cost_settings

from ui.sections.sales_trends import render_sales_trends
from ui.sections.popular_items import render_popular_items
from ui.sections.day_analysis import render_day_analysis
from ui.sections.hourly_analysis import render_hourly_analysis
from ui.sections.elasticity_reliability import render_elasticity_reliability

from ui.data_upload import (
    load_uploaded_sales,
    render_source_audit,
)

from ui.table_formatters import (
    display_item_table,
    display_moves_table,
    safe_format_currency,
)

st.set_page_config(
    page_title="Menu Engineering Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_dashboard_styles()


def capability_line(ok: bool, label: str, reason: str = "") -> str:
    icon = "✓" if ok else "✗"
    suffix = f" — {reason}" if reason else ""
    return f"{icon} {label}{suffix}"
    
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


# --------------------------------------------------
# Load dataset
# --------------------------------------------------

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

    except Exception as exc:
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


# -----------------------------------------------------------------
# Feature 2: Data Setup & Column Mapping
# -----------------------------------------------------------------

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


# --------------------------------------------------
# Validate column mapping — visible outside expander
# --------------------------------------------------

mapping_errors = validate_mapping(mapping, raw_df.columns)

if mapping_errors:
    st.error(
        "Dataset column mapping needs attention. "
        "Open Data Setup & Column Mapping to correct the selections."
    )

    for error in mapping_errors:
        st.error(error)

    st.stop()


# --------------------------------------------------
# Adapt dataset to canonical schema
# --------------------------------------------------

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


# --------------------------------------------------
# Optional cost handling
# --------------------------------------------------

canonical_df, cost_basis, cost_is_assumption = (
    render_cost_settings(canonical_df)
)

# --------------------------------------------------
# Feature 3: Validate Dataset
# --------------------------------------------------

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

# --------------------------------------------------
# Date range filtering
# --------------------------------------------------
with st.expander("⚙️ Sales Filters", expanded=False):

    st.subheader("Filter sales by date")

    # Preserve validated data before filtering
    df = df.copy()

    # Make sure dates are pandas datetime values
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if df["date"].isna().all():
        st.error(
            "No valid transaction dates were found in this dataset."
        )
        st.stop()

    if df["date"].isna().any():
        missing_dates = int(df["date"].isna().sum())
        st.warning(
            f"{missing_dates:,} rows have invalid dates "
            "and will be excluded from date-based analysis."
        )
        df = df.dropna(subset=["date"]).copy()

    # Determine available dates from the uploaded dataset
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    # Date range selector
    selected_date_range = st.date_input(
        "Select a date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Choose the period you want to analyze.",
        key="sales_date_range",
    )

    # Streamlit may temporarily return only one date
    # while the user is selecting a range.
    if len(selected_date_range) != 2:
        st.info("Please select both a start date and an end date.")
        st.stop()

    start_date, end_date = selected_date_range


    # Apply the tested, inclusive date range filter.
    df = filter_by_date_range(
        df,
        start_date,
        end_date,
    )

    if df.empty:
        st.warning(
            "No sales records exist for the selected date range."
        )
        st.stop()

    st.caption(
        f"Selected period: {start_date:%B %d, %Y} "
        f"to {end_date:%B %d, %Y} "
        f"— {len(df):,} sales rows."
    )


    # --------------------------------------------------
    # Category Filters
    # --------------------------------------------------
    st.header("Filter menu by category")

    # Make sure the category grouping is available
    # after validation, even if validation removes
    # extra columns.
    df = df.copy()

    df["category_group"] = [
        classify_menu_item(category, item)
        for category, item in zip(df["category"], df["item"])
    ]

    # Show the main category filter
    available_groups = [
        group
        for group in CATEGORY_GROUPS
        if group in df["category_group"].unique()
    ]

    selected_groups = st.multiselect(
        "Select food categories",
        options=available_groups,
        default=available_groups,
        help="Choose Savory, Dessert, Drinks, or Other.",
    )

    # Apply broad-category filtering
    filtered_df = df[
        df["category_group"].isin(selected_groups)
    ].copy()

    # Optional detailed category filter
    available_categories = sorted(
        filtered_df["category"].dropna().astype(str).unique()
    )

    selected_categories = st.multiselect(
        "Filter by detailed category (optional)",
        options=available_categories,
        default=available_categories,
        help="For example: Coffee, Tea, Bakery, or Sandwich.",
    )

    filtered_df = filtered_df[
        filtered_df["category"].isin(selected_categories)
    ].copy()

    if filtered_df.empty:
        st.warning(
            "No menu items match your selected categories. "
            "Please select at least one category."
        )
        st.stop()

    # Update the dataframe used by downstream analyses.
    df = filtered_df

    st.caption(
        f"Showing {len(df):,} sales rows across "
        f"{df['item'].nunique():,} unique menu items."
    )

    # Recalculate capabilities and item summaries
    # using the selected categories.
    capabilities = determine_capabilities(df)
    summary = build_item_summary(df)

    # This is stricter than simply seeing multiple prices: it reflects whether the
    # estimator actually accepted at least one item-level historical estimate.
    capabilities["historical_elasticity_estimation"] = bool(
        not summary.empty and (summary["elasticity_source"] == "estimated").any()
    )

    # -----------------------------------------------------------------
    # Feature 7: Create transaction timestamps for hourly analysis.
    # -----------------------------------------------------------------
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


# --------------------------------------------------
# Dataset capabilities
# --------------------------------------------------

# Count how many items have historical elasticity estimates.
estimated_count = int(
    (summary["elasticity_source"] == "estimated").sum()
)

total_items = len(summary)

# Count items using assumed elasticity values.
category_prior_count = int(
    (summary["elasticity_source"] == "category_prior").sum()
)

default_prior_count = int(
    (summary["elasticity_source"] == "default_prior").sum()
)

# Count low-confidence historical estimates.
low_confidence_count = int(
    (
        (summary["elasticity_source"] == "estimated")
        & (
            summary["elasticity_confidence"]
            .astype(str)
            .str.lower() == "low"
        )
    ).sum()
)

# Build the complete dataset capability report.
capability_text = [
    capability_line(
        capabilities["revenue_analysis"],
        "Revenue analysis",
    ),

    capability_line(
        capabilities["popularity_analysis"],
        "Popularity analysis",
    ),

    capability_line(
        capabilities["sales_trend_analysis"],
        "Sales trend analysis",
    ),

    capability_line(
        capabilities["price_variation_analysis"],
        "Price variation analysis",
    ),

    capability_line(
        estimated_count > 0,
        "Historical elasticity estimation",
        (
            f"{estimated_count} of {total_items} items estimated "
            f"({low_confidence_count} low confidence); "
            f"{category_prior_count} category priors, "
            f"{default_prior_count} default priors"
            if estimated_count > 0
            else (
                f"No historical estimates among {total_items} items; "
                f"{category_prior_count} category priors, "
                f"{default_prior_count} default priors"
            )
        ),
    ),

    capability_line(
        capabilities["profit_analysis"],
        "Profit analysis",
        (
            "unit cost missing or incomplete"
            if not capabilities["profit_analysis"]
            else (
                "cost is a scenario assumption"
                if cost_is_assumption
                else ""
            )
        ),
    ),

    capability_line(
        capabilities["menu_engineering_quadrants"],
        "Menu Engineering Quadrants",
        (
            "unit cost missing or incomplete"
            if not capabilities["menu_engineering_quadrants"]
            else (
                "based on assumed costs"
                if cost_is_assumption
                else ""
            )
        ),
    ),

    capability_line(
        capabilities["price_optimization"],
        "Profit-based price recommendations",
        (
            "unit cost missing or incomplete"
            if not capabilities["price_optimization"]
            else (
                "scenario only"
                if cost_is_assumption
                else ""
            )
        ),
    ),
]

# --------------------------------------------------
# Modern Fintech — Active Filter Summary
# --------------------------------------------------

st.caption(
    f"📅 {start_date:%b %d, %Y} – {end_date:%b %d, %Y}"
    f"   |   🗂️ {len(selected_groups)} food groups"
    f"   |   🧾 {len(df):,} sales records"
)

# --------------------------------------------------
# Modern Fintech — Collapsible Dataset Capabilities
# --------------------------------------------------

with st.expander("View Dataset Capabilities", expanded=False):
    st.caption(
        "See which analyses are supported by your dataset "
        "and why certain features may be unavailable."
    )

    st.code(
        "\n".join(capability_text),
        language=None,
    )


# --------------------------------------------------
# Calculate Analytics
# --------------------------------------------------

render_business_header(
    business_name=business_name,
    start_date=start_date,
    end_date=end_date,
    menu_item_count=df["item"].nunique(),
)

# Reusable KPI cards from src/ui/components.py
render_kpi_cards(df, currency)

# --------------------------------------------------
# Display Dashboard
# --------------------------------------------------

st.header("Sales Analytics")
analysis_tabs = st.tabs(["Revenue & Popularity", "Elasticity Reliability", "Menu Quadrants", "Item Detail"])

with analysis_tabs[0]:
    revenue_tabs = st.tabs([
        "Sales Trends",
        "Day Analysis",
        "Hourly Analysis",
        "Popular Items",
    ])


    # -----------------------------------------------------------------
    # Feature 9: Sales Trends navigation tab
    # -----------------------------------------------------------------
    with revenue_tabs[0]:
        render_sales_trends(df, currency)
        
    # -----------------------------------------------------------------
    # Feature 9: Popular Items navigation tab
    # -----------------------------------------------------------------
    with revenue_tabs[3]:
        render_popular_items(summary)

    # -----------------------------------------------------------------
    # Feature 9: Day Analysis navigation tab
    # -----------------------------------------------------------------
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

    with st.container(border=True):

        render_chart_header(
            "Menu Engineering Quadrants",
            "Evaluate menu performance using popularity "
            "and contribution margin.",
        )

        if capabilities["menu_engineering_quadrants"]:

            quadrant_chart = px.scatter(
                summary,
                x="avg_daily_units",
                y="contribution_margin_%",
                color="quadrant",
                size="total_profit",
                hover_name="item",
                hover_data=[
                    "category",
                    "price",
                    "elasticity_source",
                    "elasticity_confidence",
                ],
                labels={
                    "avg_daily_units": "Avg Daily Units Sold",
                    "contribution_margin_%": (
                        "Contribution Margin %"
                    ),
                },
            )

            quadrant_chart.add_vline(
                x=summary["avg_daily_units"].median(),
                line_dash="dash",
                line_color="gray",
            )

            quadrant_chart.add_hline(
                y=summary["contribution_margin_%"].median(),
                line_dash="dash",
                line_color="gray",
            )

            quadrant_chart = style_chart(
                quadrant_chart,
                title="Menu Engineering Quadrants",
            )

            # Inner chart card
            with st.container(border=True):

                st.plotly_chart(
                    quadrant_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            if cost_is_assumption:
                st.warning(
                    "Quadrants use the estimated cost-percentage "
                    "scenario, not actual unit costs."
                )

        else:
            st.info(
                "Menu quadrants require complete unit cost data "
                "because margin is one axis of the classification."
            )


# ================================================================
# MENU ITEM EXPLORER TAB
# ================================================================
with analysis_tabs[3]:

    with st.container(border=True):

        render_chart_header(
            "Menu Item Explorer",
            "Explore menu items by revenue, sales volume, or name. "
            "Category filters are applied automatically.",
        )

        # Sorting options from dashboard_utils.py
        selected_sort = st.selectbox(
            "Sort menu items by",
            options=list(SORTING_OPTIONS.keys()),
            index=0,
            key="menu_item_sort",
        )

        # Preserve the tested sorting function.
        sorted_summary = sort_menu_items(
            summary,
            selected_sort,
        )

        has_cost = capabilities["profit_analysis"]

        columns = [
            "item",
            "category",
            "price",
            "avg_daily_units",
            "total_units_sold",
            "total_revenue",
        ]

        if has_cost:
            columns += [
                "unit_cost",
                "contribution_margin_amount",
                "contribution_margin_%",
                "total_profit",
                "quadrant",
            ]

        columns += [
            "elasticity",
            "elasticity_source",
            "elasticity_confidence",
        ]

        # Inner table card
        with st.container(border=True):

            st.dataframe(
                display_item_table(
                    sorted_summary[columns],
                    currency,
                    has_cost,
                ),
                width="stretch",
                hide_index=True,
            )

        st.caption(
            f"Displaying {len(sorted_summary):,} menu items. "
            f"Sorted by: {selected_sort}."
        )

st.header("Pricing Recommendations")
price_changes = [value / 100 for value in range(-max_decrease, max_increase + 1, 5)]
if 0.0 not in price_changes:
    price_changes.append(0.0)
moves = recommend_price_moves(summary, price_changes) if capabilities["price_optimization"] else pd.DataFrame()

if moves.empty:
    st.info(
        "Profit-based price recommendations are disabled because complete unit cost data is unavailable. "
        "The app will not fabricate cost or profit figures."
    )
else:
    st.caption(
        f"Candidate moves are tested from -{max_decrease}% to +{max_increase}% in 5% steps. "
        "Demand response uses historical estimates when reliable enough, otherwise a clearly labeled prior."
    )
    if cost_is_assumption:
        st.warning("These price/profit recommendations are scenario results based on your estimated cost percentage.")
    move_columns = [
        "item", "old_price", "new_price", "pct_change_recommended", "daily_profit_delta",
        "quadrant", "elasticity_source", "elasticity_confidence", "pricing_reliability",
        "reliability_reason",
    ]
    st.warning(
        "Pricing results are exploratory simulations, "
        "not validated pricing decisions. "
        "Low-confidence historical estimates and assumed "
        "elasticities require additional review."
    )
    
    # Main pricing recommendations table
    display_columns = [
        col for col in move_columns
        if col != "reliability_reason"
    ]

    st.dataframe(
        display_moves_table(
            moves[display_columns],
            currency,
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "pricing_reliability": st.column_config.TextColumn(
                "Pricing Reliability",
                width="large",
            ),
        },
    )

# Detailed explanations shown separately
with st.expander("View pricing reliability explanations"):
    for _, row in moves.iterrows():
        st.markdown(f"**{row['item']}**")
        st.write(row["reliability_reason"])
        st.divider()


# --------------------------------------------------
# 7. Generate AI decision memo
# --------------------------------------------------

st.header("AI Decision Memo")

metadata = {
    "business_name": business_name,
    "dataset_name": dataset_name,
    "currency": currency,
    "cost_basis": cost_basis,
    "cost_is_assumption": cost_is_assumption,
    "available_analysis": [
        name
        for name, available in capabilities.items()
        if available
    ],
}

# Create a stable fingerprint of the memo inputs.
# If the dataset, settings, or analysis results change,
# the previous memo will no longer be displayed.
import hashlib
import json

memo_context = {
    "metadata": metadata,
    "capabilities": capabilities,
    "summary": summary.to_json(
        orient="records",
        date_format="iso",
    ),
    "moves": moves.to_json(
        orient="records",
        date_format="iso",
    ),
}

context_bytes = json.dumps(
    memo_context,
    sort_keys=True,
    default=str,
).encode("utf-8")

context_id = hashlib.sha256(context_bytes).hexdigest()

# Initialize Streamlit session state.
if "generated_memo" not in st.session_state:
    st.session_state.generated_memo = None

if "generated_memo_context" not in st.session_state:
    st.session_state.generated_memo_context = None

# Clear outdated memos when the source inputs change.
if st.session_state.generated_memo_context != context_id:
    st.session_state.generated_memo = None
    st.session_state.generated_memo_context = None

# Check Anthropic API configuration.
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning(
        "No ANTHROPIC_API_KEY is configured. "
        "All deterministic analytics still work; "
        "only memo generation is disabled."
    )

else:
    # Generate or regenerate the memo.
    if st.button(
        "Generate decision memo",
        type="primary",
    ):
        try:
            from agent import generate_menu_memo

            with st.spinner(
                "Generating memo from computed results..."
            ):
                memo = generate_menu_memo(
                    summary,
                    moves,
                    metadata=metadata,
                    capabilities=capabilities,
                )

            # Persist the memo across Streamlit reruns.
            st.session_state.generated_memo = memo
            st.session_state.generated_memo_context = context_id

            st.success(
                "AI decision memo generated successfully!"
            )

        except Exception as exc:
            st.error(
                "Could not generate the AI memo. "
                "The analytics above are unaffected."
            )
            st.code(str(exc))


# --------------------------------------------------
# Display and download the generated memo
# --------------------------------------------------

if (
    st.session_state.generated_memo is not None
    and st.session_state.generated_memo_context == context_id
):
    memo = st.session_state.generated_memo

    st.markdown("### Decision Memo")

    # Escape dollar signs only for Streamlit display.
    # Keep the original memo unchanged for downloads.
    display_memo = memo.replace("$", r"\$")

    st.markdown(display_memo)

    st.divider()

    st.subheader("Download decision memo")

    # Make a safe filename from the business name.
    import re

    safe_business_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        business_name.strip(),
    ).strip("_") or "business"

# --------------------------------------------------
# Download decision memo
# --------------------------------------------------
    # Create three download columns
    download_col1, download_col2, download_col3 = st.columns(3)

    # Markdown download
    with download_col1:
        st.download_button(
            label="Download Markdown (.md)",
            data=memo.encode("utf-8"),
            file_name=f"{safe_business_name}_decision_memo.md",
            mime="text/markdown",
            width="stretch",
        )

    # Download Plain text
    with download_col2:
        st.download_button(
            label="Download Text (.txt)",
            data=memo.encode("utf-8"),
            file_name=f"{safe_business_name}_decision_memo.txt",
            mime="text/plain",
            width="stretch",
        )

    # Download PDF
    with download_col3:
        try:
            pdf_bytes = generate_memo_pdf(
                memo=memo,
                business_name=business_name,
                dataset_name=dataset_name,
            )

            st.download_button(
                label="Download PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{safe_business_name}_decision_memo.pdf",
                mime="application/pdf",
                width="stretch",
            )

        except Exception as exc:
            st.error(f"Could not generate PDF: {exc}")


    st.caption(
        "This memo is AI-generated from the computed analysis. "
        "Verify all recommendations before making business decisions. "
        "Estimated costs and uncertain price elasticities "
        "should not be treated as confirmed results."
    )
