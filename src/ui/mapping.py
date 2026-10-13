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