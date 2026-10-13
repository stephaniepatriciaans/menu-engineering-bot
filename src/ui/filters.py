"""Reusable Streamlit controls for filtering sales data"""

from datetime import date

import pandas as pd
import streamlit as st

from dashboard_utils import filter_by_date_range


def render_date_filter(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, date, date]:
    """Select a date range and return the filtered sales records."""

    result = df.copy()
    result["date"] = pd.to_datetime(
        result["date"],
        errors="coerce",
    )

    # Block datasets without usable dates.
    if result["date"].isna().all():
        st.error(
            "No valid transaction dates were found in this dataset."
        )
        st.stop()
        raise ValueError("No valid transaction dates.")

    # Warn about invalid dates without inventing dates.
    missing_dates = int(result["date"].isna().sum())

    if missing_dates:
        st.warning(
            f"{missing_dates:,} rows have invalid dates "
            "and will be excluded from date-based analysis."
        )
        result = result.dropna(subset=["date"]).copy()

    min_date = result["date"].min().date()
    max_date = result["date"].max().date()

    selected_range = st.date_input(
        "Select a date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Choose the period you want to analyze.",
        key="sales_date_range",
    )

    # Streamlit may temporarily return only one date.
    if (
        not isinstance(selected_range, (tuple, list))
        or len(selected_range) != 2
    ):
        st.info("Please select both a start date and an end date.")
        st.stop()
        raise ValueError("Incomplete date range selection.")

    start_date, end_date = selected_range

    filtered = filter_by_date_range(
        result,
        start_date,
        end_date,
    )

    if filtered.empty:
        st.warning(
            "No sales records exist for the selected date range."
        )
        st.stop()
        raise ValueError("No sales records in selected date range.")

    st.caption(
        f"Selected period: {start_date:%B %d, %Y} "
        f"to {end_date:%B %d, %Y} "
        f"— {len(filtered):,} sales rows."
    )

    return filtered, start_date, end_date


def render_category_filter(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Display category filters and return filtered sales data.

    The original DataFrame is never modified.
    Downstream summaries and pricing recommendations should
    use the returned DataFrame.
    """

    from config import CATEGORY_GROUPS, classify_menu_item

    result = df.copy()

    # Determine the broad category for each menu item.
    result["category_group"] = [
        classify_menu_item(category, item)
        for category, item in zip(
            result["category"],
            result["item"],
        )
    ]

    # --------------------------------------------------
    # Broad food category selection
    # --------------------------------------------------
    st.header("Filter menu by category")

    present_groups = set(result["category_group"].dropna())

    available_groups = [
        group
        for group in CATEGORY_GROUPS
        if group in present_groups
    ]

    selected_groups = st.multiselect(
        "Select food categories",
        options=available_groups,
        default=available_groups,
        help="Choose Savory, Dessert, Drinks, or Other.",
    )

    result = result.loc[
        result["category_group"].isin(selected_groups)
    ].copy()

    # --------------------------------------------------
    # Detailed category selection
    # --------------------------------------------------
    available_categories = sorted(
        result["category"].dropna().astype(str).unique()
    )

    selected_categories = st.multiselect(
        "Filter by detailed category (optional)",
        options=available_categories,
        default=available_categories,
        help="For example: Coffee, Tea, Bakery, or Sandwich.",
    )

    result = result.loc[
        result["category"].isin(selected_categories)
    ].copy()

    # --------------------------------------------------
    # Validate the selection
    # --------------------------------------------------
    if result.empty:
        st.warning(
            "No menu items match your selected categories. "
            "Please select at least one category."
        )
        st.stop()
        raise ValueError("No menu items match the selected categories.")

    st.caption(
        f"Showing {len(result):,} sales rows across "
        f"{result['item'].nunique():,} unique menu items."
    )

    return result
