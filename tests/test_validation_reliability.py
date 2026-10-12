"""Regression tests for sales validation and capability detection"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation import (
    audit_source_transactions,
    determine_capabilities,
    validate_sales_df,
)


def test_missing_optional_fields_preserve_revenue_analysis():
    """Missing optional data must not disable basic analytics."""

    raw = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "item": ["Latte", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [10, 20],
    })

    original = raw.copy(deep=True)

    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None
    assert len(validated) == 2

    # Optional columns should be filled safely.
    assert "category" in validated.columns
    assert "unit_cost" in validated.columns
    assert "transaction_time" in validated.columns

    assert (
        validated["category"] == "Uncategorized"
    ).all()

    assert validated["unit_cost"].isna().all()
    assert validated["transaction_time"].isna().all()

    assert any(
        "Category was not available" in message
        for message in _warnings
    )

    assert any(
        "Unit cost is unavailable" in message
        for message in _warnings
    )

    capabilities = determine_capabilities(validated)

    # Revenue and popularity remain available.
    assert capabilities["revenue_analysis"] is True
    assert capabilities["popularity_analysis"] is True
    assert capabilities["sales_trend_analysis"] is True

    # Never fabricate profit-based capabilities.
    assert capabilities["profit_analysis"] is False
    assert capabilities["menu_engineering_quadrants"] is False
    assert capabilities["price_optimization"] is False

    # Original uploaded data must not be modified.
    pd.testing.assert_frame_equal(raw, original)


def test_duplicate_transactions_are_flagged_not_deleted():
    """Potential duplicates should be retained for review."""

    raw = pd.DataFrame({
        "transaction_id": ["TX001", "TX001", "TX002"],
        "date": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
        ],
        "item": ["Latte", "Latte", "Tea"],
        "category": ["Coffee", "Coffee", "Tea"],
        "price": [5.0, 5.0, 3.0],
        "units_sold": [1, 1, 2],
        "unit_cost": [2.0, 2.0, 1.0],
    })

    original = raw.copy(deep=True)

    # Audit the original POS records.
    audit_messages = audit_source_transactions(raw)

    assert any(
        "identical full-source rows" in message
        for message in audit_messages
    )

    assert any(
        "share transaction_id values" in message
        for message in audit_messages
    )

    # Validate the canonical dataset.
    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None

    # Keep all three transaction rows.
    assert len(validated) == 3

    assert any(
        "identical values" in message
        for message in _warnings
    )

    capabilities = determine_capabilities(validated)

    # Complete costs allow profit-based calculations.
    assert capabilities["profit_analysis"] is True
    assert capabilities["menu_engineering_quadrants"] is True
    assert capabilities["price_optimization"] is True

    # No item has multiple distinct prices.
    assert capabilities["historical_elasticity_estimation"] is False

    pd.testing.assert_frame_equal(raw, original)


def test_validation_rejects_infinite_price_and_units():
    """Infinite prices and sales quantities must be rejected."""

    raw = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
        ],
        "item": ["Latte", "Tea", "Mocha"],
        "category": ["Coffee", "Tea", "Coffee"],
        "price": [float("inf"), 3.0, 5.0],
        "units_sold": [10.0, float("-inf"), 0.0],
        "unit_cost": [2.0, 1.0, 2.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert validated is None

    assert any(
        "invalid values in `price`" in message
        for message in errors
    )

    assert any(
        "invalid values in `units_sold`" in message
        for message in errors
    )

    # Zero units sold is legitimate and must not be rejected.
    zero_sales = raw.iloc[[2]].copy()

    validated_zero, zero_errors, _ = validate_sales_df(
        zero_sales
    )

    assert zero_errors == []
    assert validated_zero is not None
    assert validated_zero["units_sold"].iloc[0] == 0.0


def test_validation_rejects_infinite_unit_cost():
    """Optional costs may be missing, but cannot be infinite."""

    raw = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-02",
        ],
        "item": ["Latte", "Tea"],
        "category": ["Coffee", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [10.0, 20.0],
        "unit_cost": [float("inf"), 1.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert validated is None

    assert any(
        "non-finite unit costs" in message
        for message in errors
    )

    # Missing cost is still allowed.
    missing_cost = raw.copy()
    missing_cost.loc[0, "unit_cost"] = float("nan")

    validated_missing, missing_errors, _ = (
        validate_sales_df(missing_cost)
    )

    assert missing_errors == []
    assert validated_missing is not None
    assert validated_missing["unit_cost"].isna().any()


def test_combined_datetime_extracts_transaction_time():
    """Combined timestamps should preserve real transaction times."""

    raw = pd.DataFrame({
        "date": [
            "2026-01-05 14:30:00",
            "2026-01-06 09:15:00",
        ],
        "item": ["Latte", "Tea"],
        "category": ["Coffee", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [10.0, 5.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None

    assert validated["date"].dt.hour.tolist() == [0, 0]
    assert validated["transaction_time"].tolist() == [
        "14:30:00",
        "09:15:00",
    ]


def test_date_only_does_not_create_transaction_time():
    """Date-only data must not invent hourly sales information."""

    raw = pd.DataFrame({
        "date": [
            "2026-01-05",
            "2026-01-06",
        ],
        "item": ["Latte", "Tea"],
        "category": ["Coffee", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [10.0, 5.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None

    assert validated["date"].dt.hour.tolist() == [0, 0]
    assert validated["transaction_time"].isna().all()


def test_invalid_date_rejects_dataset():
    """Invalid calendar dates must not reach analytics."""

    raw = pd.DataFrame({
        "date": [
            "2026-01-05",
            "not-a-date",
            "2026-02-30",
        ],
        "item": ["Latte", "Tea", "Mocha"],
        "category": ["Coffee", "Tea", "Coffee"],
        "price": [5.0, 3.0, 6.0],
        "units_sold": [10.0, 5.0, 7.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert validated is None
    assert any(
        "2 rows have invalid dates" in message
        for message in errors
    )


def test_existing_transaction_time_is_preserved():
    """Explicit transaction times must not be overwritten."""

    raw = pd.DataFrame({
        "date": ["2026-01-05 14:30:00"],
        "transaction_time": ["16:45:00"],
        "item": ["Latte"],
        "category": ["Coffee"],
        "price": [5.0],
        "units_sold": [10.0],
    })

    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None

    assert validated["date"].iloc[0] == pd.Timestamp(
        "2026-01-05"
    )
    assert validated["transaction_time"].iloc[0] == "16:45:00"
