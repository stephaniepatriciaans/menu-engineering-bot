"""Regression tests for optimized menu-quality processing."""

import pandas as pd

from data_pipeline.menu_quality import (
    _map_unique_values,
    audit_menu_quality,
    normalized_item_key,
)


def test_unique_mapping_preserves_rows_and_index():
    """Repeated values must retain their original positions."""
    series = pd.Series(
        ["LATTE", "Latte", None, "LATTE"],
        index=[10, 20, 30, 40],
    )

    result = _map_unique_values(
        series,
        normalized_item_key,
    )

    assert result.index.tolist() == [10, 20, 30, 40]
    assert result.tolist() == [
        "latte",
        "latte",
        None,
        "latte",
    ]


def test_optimized_menu_quality_preserves_counts():
    """Check representative spelling, price, and duplicate behavior."""
    df = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-01",
        ],
        "item": [
            "LATTE",
            "Latte",
            "LATTE",
            "LATTE",
        ],
        "price": [5.0, 5.5, 5.0, 5.0],
        "units_sold": [1, 2, 1, 1],
    })

    mapping = {
        "date": "date",
        "item": "item",
        "category": None,
        "price": "price",
        "unit_cost": None,
        "units_sold": "units_sold",
    }

    result = audit_menu_quality(df, mapping)

    assert result.inspected_rows == 4
    assert result.repeated_item_spelling_groups == 1
    assert len(result.multi_price_items) == 1
    assert result.exact_duplicate_candidates == 2
    assert result.missing_item_rows == 0

    prices = result.multi_price_items.iloc[0]
    assert prices["distinct_prices"] == 2
    assert prices["lowest_price"] == "5.00"
    assert prices["highest_price"] == "5.50"
