"""Streamlit UI for mapping uploaded dataset columns."""

import pandas as pd
import streamlit as st

from config import CANONICAL_FIELDS
from data_adapter import (
    KNOWN_MAPPING_PRESETS,
    NOT_AVAILABLE,
    apply_known_preset,
    detect_column_mapping,
    mapping_confidence,
)


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


def discount_amount_selector(
    raw_df: pd.DataFrame,
    prefix: str = "sales",
    mapping: dict[str, str | None] | None = None,
) -> str | None:
    """Select an optional line-level monetary discount column."""
    from config import POS_COLUMN_ALIASES

    excluded_columns: set[str] = set()

    if mapping is not None:
        excluded_columns = {
            column
            for column in (
                mapping.get("price"),
                mapping.get("units_sold"),
            )
            if column is not None
        }

    options = [NOT_AVAILABLE] + [
        str(column)
        for column in raw_df.columns
        if str(column) not in excluded_columns
    ]

    aliases = {
        alias.strip().lower()
        for alias in POS_COLUMN_ALIASES["discount_amount"]
    }

    detected = next(
        (
            str(column)
            for column in raw_df.columns
            if (
                str(column).strip().lower() in aliases
                and str(column) not in excluded_columns
            )
        ),
        None,
    )

    selected = st.selectbox(
        "Discount Amount (optional, per transaction row)",
        options,
        index=options.index(detected) if detected else 0,
        key=f"{prefix}_discount_amount",
        help=(
            "Select the total monetary discount for each row. "
            "Do not select percentages, per-unit discounts, "
            "price columns, or already-discounted totals."
        ),
    )

    return None if selected == NOT_AVAILABLE else selected

def discount_percent_selector(
    raw_df: pd.DataFrame,
    prefix: str = "sales",
    mapping: dict[str, str | None] | None = None,
    discount_amount_column: str | None = None,
) -> str | None:
    """Select an optional line-level percentage discount column.

    A value of 20 represents 20%, not 0.20.
    """
    from config import POS_COLUMN_ALIASES

    excluded_columns: set[str] = set()

    if mapping is not None:
        excluded_columns.update(
            column
            for column in (
                mapping.get("price"),
                mapping.get("units_sold"),
            )
            if column is not None
        )

    if discount_amount_column is not None:
        excluded_columns.add(discount_amount_column)

    options = [NOT_AVAILABLE] + [
        str(column)
        for column in raw_df.columns
        if str(column) not in excluded_columns
    ]

    aliases = {
        alias.strip().lower()
        for alias in POS_COLUMN_ALIASES["discount_percent"]
    }

    detected = next(
        (
            str(column)
            for column in raw_df.columns
            if (
                str(column).strip().lower() in aliases
                and str(column) not in excluded_columns
            )
        ),
        None,
    )

    selected = st.selectbox(
        "Discount Percentage (optional, per transaction row)",
        options,
        index=options.index(detected) if detected else 0,
        key=f"{prefix}_discount_percent",
        help=(
            "Select a percentage discount column where "
            "20 means 20%. Do not select monetary discounts, "
            "prices, or already-discounted totals."
        ),
    )

    return None if selected == NOT_AVAILABLE else selected
