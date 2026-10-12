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

from ui.table_formatters import (
    display_item_table,
    display_moves_table,
)

st.set_page_config(
    page_title="Menu Engineering Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_dashboard_styles()


def mapping_selectors(
    raw_df: pd.DataFrame,
    prefix: str = "sales",
) -> dict[str, str | None]:
    """
    Render column mapping controls with:
    - Automatic detection
    - Dataset mapping presets
    - Manual column selection
    - Mapping confidence feedback
    """
    detected = detect_column_mapping(raw_df.columns)

    preset_names = ["Automatic detection"] + list(
        KNOWN_MAPPING_PRESETS.keys()
    )

    preset = st.selectbox(
        "Column mapping preset",
        preset_names,
        key=f"{prefix}_preset",
    )

    if preset != "Automatic detection":
        preset_mapping = apply_known_preset(
            raw_df.columns,
            preset,
        )
        detected.update(preset_mapping)

    options = [NOT_AVAILABLE] + [
        str(col) for col in raw_df.columns
    ]

    labels = {
        "date": "Date (required)",
        "item": "Item (required)",
        "category": "Category (optional)",
        "price": "Price (required)",
        "unit_cost": "Unit Cost (optional)",
        "units_sold": "Units Sold (required)",
        "transaction_time": "Transaction Time (optional)",
    }

    result: dict[str, str | None] = {}
    columns = st.columns(3)

    for idx, field in enumerate(CANONICAL_FIELDS):
        preselected = detected.get(field) or NOT_AVAILABLE

        choice = columns[idx % 3].selectbox(
            labels[field],
            options,
            index=(
                options.index(preselected)
                if preselected in options
                else 0
            ),
            key=f"{prefix}_{preset}_map_{field}",
        )

        result[field] = (
            None if choice == NOT_AVAILABLE else choice
        )

    with st.expander("View column mapping confidence"):
        confidence = mapping_confidence(
            raw_df.columns,
            result,
        )

        for field in CANONICAL_FIELDS:
            selected = result.get(field) or "Not mapped"
            st.write(
                f"**{field}** → {selected} ({confidence[field]})"
            )

        st.caption(
            "Confidence describes column-name similarity, not proof "
            "that a field contains the correct data. "
            "Please verify the mappings before analysis."
        )

    return result


def capability_line(ok: bool, label: str, reason: str = "") -> str:
    icon = "✓" if ok else "✗"
    suffix = f" — {reason}" if reason else ""
    return f"{icon} {label}{suffix}"
    
st.title("Menu Engineering Bot")
st.caption(
    "Universal menu/POS data adapter + deterministic pricing analytics + AI explanation. "
    "The numerical engine never delegates calculations to the LLM."
)

with st.sidebar:
    st.header("Business settings")
    business_name = st.text_input("Business name", value="My Food-Service Business")
    dataset_name = st.text_input("Dataset name", value="Menu Sales Dataset")
    currency = st.selectbox("Currency", list(CURRENCY_CONFIG.keys()), index=0)

    st.header("Price simulation")
    max_decrease = st.slider("Maximum price decrease", 0, 30, 10, 5, format="-%d%%")
    max_increase = st.slider("Maximum price increase", 0, 30, 15, 5, format="+%d%%")

    st.header("1. Load dataset")
    source = st.radio(
        "Data source",
        ["Full Demo Dataset — Synthetic Cafe", "Upload my own CSV"],
    )
    uploaded = None
    if source == "Upload my own CSV":
        uploaded = st.file_uploader("Upload sales/POS CSV", type=["csv"])


# --------------------------------------------------
# Load dataset
# --------------------------------------------------

raw_df: pd.DataFrame | None = None

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
        # Read the original uploaded CSV
        uploaded.seek(0)
        raw_df = read_delimited_csv(uploaded)

        # Audit source transactions before column mapping
        source_audit_messages = audit_source_transactions(
            raw_df
        )

        # Display transaction audit results
        with st.expander("Source transaction audit"):
            for message in source_audit_messages:
                st.write(message)

            st.caption(
                "This audit checks for identical source records "
                "and repeated transaction IDs. "
                "Repeated IDs may be normal for multi-item orders. "
                "No records are automatically removed."
            )

    except Exception as exc:
        st.error(
            f"Could not read or audit the CSV: {exc}"
        )
        st.stop()

else:
    st.info(
        "Upload a CSV to begin. "
        "You do not need to rename its columns first."
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

cost_basis = (
    "provided_cost_column"
    if canonical_df["unit_cost"].notna().all()
    else "unavailable"
)

cost_is_assumption = False

with st.expander("💰 Optional Cost Settings", expanded=False):

    if not canonical_df["unit_cost"].notna().all():

        st.write(
            "Unit cost is not fully available. "
            "Only provide real cost data or explicitly choose "
            "a scenario assumption."
        )

        cost_option = st.radio(
            "Cost handling",
            [
                "Continue without unit cost",
                "Upload a separate menu-cost CSV",
                "Scenario analysis using estimated cost percentage",
            ],
        )

        if cost_option == "Upload a separate menu-cost CSV":

            cost_upload = st.file_uploader(
                "Upload menu-cost CSV",
                type=["csv"],
                key="cost_upload",
            )

            if cost_upload is not None:
                try:
                    cost_upload.seek(0)

                    raw_cost_df = read_delimited_csv(
                        cost_upload
                    )

                    cost_detected = detect_column_mapping(
                        raw_cost_df.columns
                    )

                    cost_options = [
                        NOT_AVAILABLE,
                        *[str(c) for c in raw_cost_df.columns],
                    ]

                    c1, c2 = st.columns(2)

                    item_default = (
                        cost_detected.get("item")
                        or NOT_AVAILABLE
                    )

                    cost_default = (
                        cost_detected.get("unit_cost")
                        or NOT_AVAILABLE
                    )

                    cost_item_col = c1.selectbox(
                        "Cost file: Item",
                        cost_options,
                        index=(
                            cost_options.index(item_default)
                            if item_default in cost_options
                            else 0
                        ),
                    )

                    cost_value_col = c2.selectbox(
                        "Cost file: Unit Cost",
                        cost_options,
                        index=(
                            cost_options.index(cost_default)
                            if cost_default in cost_options
                            else 0
                        ),
                    )

                    if (
                        cost_item_col != NOT_AVAILABLE
                        and cost_value_col != NOT_AVAILABLE
                    ):

                        canonical_df, cost_warnings = (
                            merge_cost_reference(
                                canonical_df,
                                raw_cost_df,
                                cost_item_col,
                                cost_value_col,
                            )
                        )

                        cost_basis = "separate_menu_cost_csv"

                        for warning in cost_warnings:
                            st.warning(warning)

                except Exception as exc:
                    st.error(
                        f"Could not use the cost CSV: {exc}"
                    )

        elif (
            cost_option
            == "Scenario analysis using estimated cost percentage"
        ):

            estimated_pct = st.slider(
                "Estimated cost as % of price",
                5,
                95,
                30,
                1,
            )

            canonical_df = apply_estimated_cost_percentage(
                canonical_df,
                estimated_pct / 100,
            )

            cost_basis = (
                f"assumption_{estimated_pct}_percent_of_price"
            )

            cost_is_assumption = True

            st.warning(
                f"Scenario assumption enabled: unit cost is modeled "
                f"as {estimated_pct}% of selling price. "
                "These are not actual business costs."
            )

    else:
        st.success(
            "Complete unit cost data is available. "
            "Profit-based analysis can use the provided costs."
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

        # Modern Fintech — complete Sales Trends card
        with st.container(border=True):

            render_chart_header(
                "Sales Performance Over Time",
                "Explore revenue and sales volume across different time periods.",
            )

            # Dashboard controls
            control_col1, control_col2 = st.columns(
                [3, 1],
                gap="medium",
                vertical_alignment="bottom",
            )

            with control_col1:
                time_grouping = st.radio(
                    "Group sales by",
                    options=[
                        "Daily",
                        "Weekly",
                        "Monthly",
                        "Yearly",
                    ],
                    index=2,
                    horizontal=True,
                    key="sales_time_grouping",
                )

            with control_col2:
                metric_choice = st.selectbox(
                    "Metric",
                    options=["Revenue", "Units Sold"],
                    key="sales_trend_metric",
                )

            # Preserve the existing aggregation.
            grouped_sales = aggregate_sales_by_period(
                df,
                time_grouping,
            )

            # Select the metric.
            if metric_choice == "Revenue":
                y_column = "revenue"
                y_label = f"Revenue ({currency})"
            else:
                y_column = "units_sold"
                y_label = "Units Sold"

            # Create the time-series chart.
            fig = px.line(
                grouped_sales,
                x="period",
                y=y_column,
                markers=True,
                title=f"{time_grouping} {metric_choice} Trend",
                labels={
                    "period": "Period Starting",
                    y_column: y_label,
                },
            )

            fig.update_layout(
                hovermode="x unified",
                xaxis_title="Date",
                yaxis_title=y_label,
            )

            # Apply styling once.
            fig = style_chart(
                fig,
                title=f"{time_grouping} {metric_choice} Trend",
            )

            with st.container(border=True):
                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={"displayModeBar": False},
                )


            # Display the aggregated data.
            with st.expander("View sales data by period"):
                display_sales = grouped_sales.copy()
                
                display_sales["period"] = (
                    display_sales["period"].dt.strftime("%Y-%m-%d")
                )
                
                display_sales["revenue"] = display_sales[
                    "revenue"
                ].map(lambda x: format_currency(x, currency))

                st.dataframe(
                    display_sales,
                    width="stretch",
                    hide_index=True,
                )

    # -----------------------------------------------------------------
    # Feature 9: Popular Items navigation tab
    # -----------------------------------------------------------------
    with revenue_tabs[3]:

        # Outer card — entire Popular Items section
        with st.container(border=True):

            render_chart_header(
                "Top Selling Menu Items",
                "Discover which menu items sell the most units.",
            )

            # Preserve existing top-selling item calculations.
            top_volume = summary.nlargest(
                min(15, len(summary)),
                "total_units_sold",
            )

            popular_items_chart = px.bar(
                top_volume,
                x="total_units_sold",
                y="item",
                orientation="h",
                title="Top Items by Units Sold",
                labels={
                    "total_units_sold": "Units Sold",
                    "item": "Menu Item",
                },
            )

            # Apply reusable Modern Fintech chart styling.
            popular_items_chart = style_chart(
                popular_items_chart,
                title="Top Items by Units Sold",
            )

            # Inner card — chart only
            with st.container(border=True):
                st.plotly_chart(
                    popular_items_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )


    # -----------------------------------------------------------------
    # Feature 9: Day Analysis navigation tab
    # -----------------------------------------------------------------
    with revenue_tabs[1]:

        # =============================================================
        # CARD 1 — Weekday vs. Weekend Performance
        # =============================================================
        with st.container(border=True):

            render_chart_header(
                "Weekday vs. Weekend Performance",
                "Compare Monday–Friday with Saturday–Sunday. "
                "Averages use days with recorded sales.",
            )

            # Preserve the existing analysis calculation.
            day_type_summary = compare_weekday_weekend(df)

            # Display metrics for each day type.
            comparison_cols = st.columns(2, gap="medium")

            for index, day_type in enumerate(["Weekday", "Weekend"]):
                result = day_type_summary[
                    day_type_summary["day_type"] == day_type
                ]

                with comparison_cols[index]:
                    st.markdown(f"#### {day_type}s")

                    if result.empty:
                        st.info(
                            "No sales recorded for this day type."
                        )
                        continue

                    row = result.iloc[0]

                    st.metric(
                        "Total Revenue",
                        format_currency(
                            row["total_revenue"],
                            currency,
                        ),
                    )

                    st.metric(
                        "Total Units Sold",
                        f"{row['total_units']:,.0f}",
                    )

                    st.metric(
                        "Average Revenue per Sales Day",
                        format_currency(
                            row["avg_daily_revenue"],
                            currency,
                        ),
                    )

                    st.caption(
                        "Days with recorded sales: "
                        f"{int(row['days_with_sales'])}"
                    )

            # Weekday vs. weekend chart.
            fig_weekend = px.bar(
                day_type_summary,
                x="day_type",
                y="avg_daily_revenue",
                color="day_type",
                title="Average Revenue per Sales Day",
                labels={
                    "day_type": "Day Type",
                    "avg_daily_revenue": (
                        f"Average Revenue ({currency})"
                    ),
                },
                category_orders={
                    "day_type": ["Weekday", "Weekend"],
                },
            )

            fig_weekend.update_layout(
                showlegend=False,
            )

            fig_weekend = style_chart(
                fig_weekend,
                title="Average Revenue per Sales Day",
            )

            with st.container(border=True):
                st.plotly_chart(
                    fig_weekend,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            # Keep data table inside the card.
            with st.expander(
                "View weekday vs. weekend data",
                expanded=False,
            ):
                comparison_table = day_type_summary.copy()

                for column in [
                    "total_revenue",
                    "avg_daily_revenue",
                ]:
                    comparison_table[column] = (
                        comparison_table[column].map(
                            lambda value: format_currency(
                                value,
                                currency,
                            )
                        )
                    )

                st.dataframe(
                    comparison_table,
                    width="stretch",
                    hide_index=True,
                )

        # =============================================================
        # CARD 2 — Monday–Sunday Performance
        # =============================================================
        with st.container(border=True):

            render_chart_header(
                "Sales Performance by Day of Week",
                "Compare Monday through Sunday using your selected "
                "date range and menu categories. Averages use days "
                "with recorded sales.",
            )

            # Preserve the existing day-of-week calculation.
            day_summary = analyze_day_of_week(df)

            day_metric = st.selectbox(
                "Compare days by",
                options=[
                    "Total Revenue",
                    "Total Units Sold",
                    "Average Daily Revenue",
                    "Average Daily Units",
                ],
                key="day_of_week_metric",
            )

            day_metric_columns = {
                "Total Revenue": "total_revenue",
                "Total Units Sold": "total_units",
                "Average Daily Revenue": "avg_daily_revenue",
                "Average Daily Units": "avg_daily_units",
            }

            selected_column = day_metric_columns[day_metric]

            day_chart = px.bar(
                day_summary,
                x="day_name",
                y=selected_column,
                category_orders={
                    "day_name": [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ],
                },
                labels={
                    "day_name": "Day of Week",
                    selected_column: day_metric,
                },
                title=f"{day_metric} by Day of Week",
            )

            day_chart.update_layout(
                xaxis_title="Day of Week",
                yaxis_title=(
                    f"{day_metric} ({currency})"
                    if "Revenue" in day_metric
                    else day_metric
                ),
            )

            day_chart = style_chart(
                day_chart,
                title=f"{day_metric} by Day of Week",
            )

            with st.container(border=True):
                st.plotly_chart(
                    day_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            # Highlight strongest and weakest days using
            # average daily revenue, not total revenue.
            best_day = day_summary.loc[
                day_summary["avg_daily_revenue"].idxmax()
            ]

            slowest_day = day_summary.loc[
                day_summary["avg_daily_revenue"].idxmin()
            ]

            best_col, slowest_col = st.columns(
                2,
                gap="medium",
            )

            with best_col:
                st.metric(
                    "Highest Avg. Revenue Day",
                    best_day["day_name"],
                    (
                        f"{currency}"
                        f"{best_day['avg_daily_revenue']:,.2f}/day"
                    ),
                )

            with slowest_col:
                st.metric(
                    "Lowest Avg. Revenue Day",
                    slowest_day["day_name"],
                    (
                        f"{currency}"
                        f"{slowest_day['avg_daily_revenue']:,.2f}/day"
                    ),
                )

            # Keep the Monday–Sunday data table inside the card.
            with st.expander(
                "View Monday–Sunday Sales Data",
                expanded=False,
            ):
                display_days = day_summary[
                    [
                        "day_name",
                        "total_revenue",
                        "total_units",
                        "days_with_sales",
                        "avg_daily_revenue",
                        "avg_daily_units",
                    ]
                ].copy()

                display_days.columns = [
                    "Day",
                    "Total Revenue",
                    "Total Units",
                    "Days With Sales",
                    "Avg. Daily Revenue",
                    "Avg. Daily Units",
                ]

                st.dataframe(
                    display_days,
                    width="stretch",
                    hide_index=True,
                )



    # ================================================================
    # HOURLY ANALYSIS TAB
    # ================================================================
    with revenue_tabs[2]:

        # ------------------------------------------------------------
        # CARD 1 — Peak-Hour Analysis
        # ------------------------------------------------------------
        with st.container(border=True):

            render_chart_header(
                "Peak-Hour Analysis",
                "Identify busy hours using transaction timestamps. "
                "Results reflect your selected date range and categories.",
            )

            if df["transaction_datetime"].notna().any():

                hourly_summary = analyze_peak_hours(df)

                hour_metric = st.selectbox(
                    "Analyze peak hours by",
                    options=[
                        "Revenue",
                        "Units Sold",
                        "Sales Records",
                    ],
                    key="peak_hour_metric",
                )

                hour_columns = {
                    "Revenue": "total_revenue",
                    "Units Sold": "total_units",
                    "Sales Records": "sales_rows",
                }

                selected_hour_column = hour_columns[hour_metric]

                hourly_summary["hour_label"] = (
                    hourly_summary["hour"]
                    .map(lambda hour: f"{hour:02d}:00")
                )

                peak_chart = px.bar(
                    hourly_summary,
                    x="hour_label",
                    y=selected_hour_column,
                    labels={
                        "hour_label": "Hour of Day",
                        selected_hour_column: hour_metric,
                    },
                    title=f"{hour_metric} by Hour of Day",
                )

                peak_chart.update_layout(
                    xaxis_title="Hour of Day",
                    yaxis_title=(
                        f"Revenue ({currency})"
                        if hour_metric == "Revenue"
                        else hour_metric
                    ),
                )

                peak_chart = style_chart(
                    peak_chart,
                    title=f"{hour_metric} by Hour of Day",
                )

                # Inner chart card
                with st.container(border=True):
                    st.plotly_chart(
                        peak_chart,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                if not hourly_summary.empty:
                    busiest_hour = hourly_summary.loc[
                        hourly_summary[selected_hour_column].idxmax()
                    ]

                    st.metric(
                        f"Peak Hour by {hour_metric}",
                        busiest_hour["hour_label"],
                    )

                with st.expander(
                    "View Hourly Sales Data",
                    expanded=False,
                ):
                    display_hourly = hourly_summary[
                        [
                            "hour_label",
                            "total_revenue",
                            "total_units",
                            "sales_rows",
                        ]
                    ].rename(
                        columns={
                            "hour_label": "Hour",
                            "total_revenue": "Revenue",
                            "total_units": "Units Sold",
                            "sales_rows": "Sales Records",
                        }
                    )

                    st.dataframe(
                        display_hourly,
                        width="stretch",
                        hide_index=True,
                    )

            else:
                st.info(
                    "Peak-hour analysis is unavailable because "
                    "the dataset does not contain usable transaction times."
                )

        # ------------------------------------------------------------
        # CARD 2 — Hourly Revenue Analysis
        # ------------------------------------------------------------
        with st.container(border=True):

            render_chart_header(
                "Hourly Revenue Analysis",
                "Compare average hourly revenue across days with "
                "recorded sales in that hour. Days without recorded "
                "sales for an hour are excluded from that hour's average.",
            )

            if df["transaction_datetime"].notna().any():

                hourly_revenue = analyze_hourly_revenue(df)

                hourly_revenue["hour_label"] = (
                    hourly_revenue["hour"]
                    .map(lambda hour: f"{hour:02d}:00")
                )

                revenue_chart = px.line(
                    hourly_revenue,
                    x="hour_label",
                    y="avg_daily_revenue",
                    markers=True,
                    labels={
                        "hour_label": "Hour of Day",
                        "avg_daily_revenue": (
                            f"Average Revenue ({currency})"
                        ),
                    },
                    title="Average Revenue by Hour",
                )

                revenue_chart.update_layout(
                    xaxis_title="Hour of Day",
                    yaxis_title=f"Average Revenue ({currency})",
                )

                revenue_chart = style_chart(
                    revenue_chart,
                    title="Average Revenue by Hour",
                )

                # Inner chart card
                with st.container(border=True):
                    st.plotly_chart(
                        revenue_chart,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                if not hourly_revenue.empty:
                    highest_hour = hourly_revenue.loc[
                        hourly_revenue["avg_daily_revenue"].idxmax()
                    ]

                    st.metric(
                        "Highest Average Revenue Hour",
                        highest_hour["hour_label"],
                    )

                with st.expander(
                    "View Hourly Revenue Data",
                    expanded=False,
                ):
                    display_hourly_revenue = hourly_revenue[
                        [
                            "hour_label",
                            "total_revenue",
                            "days_with_sales",
                            "avg_daily_revenue",
                        ]
                    ].rename(
                        columns={
                            "hour_label": "Hour",
                            "total_revenue": "Total Revenue",
                            "days_with_sales": "Days With Sales",
                            "avg_daily_revenue": (
                                "Avg. Revenue per Active Day"
                            ),
                        }
                    )

                    st.dataframe(
                        display_hourly_revenue,
                        width="stretch",
                        hide_index=True,
                    )

            else:
                st.info(
                    "Hourly revenue analysis is unavailable because "
                    "the dataset does not contain usable transaction times."
                )


# ================================================================
# ELASTICITY RELIABILITY TAB
# ================================================================
with analysis_tabs[1]:

    with st.container(border=True):

        render_chart_header(
            "Elasticity Reliability",
            "Review how each item's demand elasticity was determined "
            "and assess the reliability of those estimates.",
        )

        st.info(
            "'estimated' means the item had enough historical "
            "price/quantity variation for an item-level log-log estimate. "
            "'category_prior' and 'default_prior' are labeled assumptions, "
            "not measured demand curves."
        )

        # Inner table card
        with st.container(border=True):

            st.dataframe(
                summary[
                    [
                        "item",
                        "category",
                        "elasticity",
                        "elasticity_source",
                        "elasticity_confidence",
                        "price_points",
                        "observations",
                        "price_variation_%",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )


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
