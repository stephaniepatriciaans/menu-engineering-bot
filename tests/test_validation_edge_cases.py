"""Regression tests for financial and transaction validation."""

import pandas as pd
import pytest

from validation import (
    audit_source_transactions,
    validate_sales_df,
)


def make_sales_df(**overrides):
    """Create one valid canonical sales record."""
    values = {
        "date": "2026-01-15",
        "item": "Latte",
        "category": "Drinks",
        "price": 5.50,
        "unit_cost": 1.75,
        "units_sold": 2,
    }
    values.update(overrides)
    return pd.DataFrame([values])


@pytest.mark.parametrize("price", [0, -1, -10.50])
def test_rejects_nonpositive_prices(price):
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(price=price)
    )

    assert cleaned is None
    assert any("Price must be greater than 0" in e for e in errors)


@pytest.mark.parametrize("units", [-1, -5])
def test_rejects_negative_units(units):
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(units_sold=units)
    )

    assert cleaned is None
    assert any("Units sold cannot be negative" in e for e in errors)


def test_allows_zero_units():
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(units_sold=0)
    )

    assert cleaned is not None
    assert errors == []
    assert cleaned.iloc[0]["units_sold"] == 0


def test_rejects_negative_unit_cost():
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(unit_cost=-1.25)
    )

    assert cleaned is None
    assert any("Unit cost cannot be negative" in e for e in errors)


def test_warns_when_cost_exceeds_price():
    cleaned, errors, warnings = validate_sales_df(
        make_sales_df(price=5.00, unit_cost=7.00)
    )

    assert cleaned is not None
    assert errors == []
    assert any("negative margins" in w for w in warnings)


def test_missing_cost_disables_full_profit_analysis():
    cleaned, errors, warnings = validate_sales_df(
        make_sales_df(unit_cost=pd.NA)
    )

    assert cleaned is not None
    assert errors == []
    assert pd.isna(cleaned.iloc[0]["unit_cost"])
    assert any(
        "Unit cost is unavailable" in w for w in warnings
    )


def test_partially_missing_cost_produces_warning():
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-15",
                "item": "Latte",
                "category": "Drinks",
                "price": 5.50,
                "unit_cost": 1.75,
                "units_sold": 2,
            },
            {
                "date": "2026-01-15",
                "item": "Mocha",
                "category": "Drinks",
                "price": 6.00,
                "unit_cost": None,
                "units_sold": 1,
            },
        ]
    )

    cleaned, errors, warnings = validate_sales_df(df)

    assert cleaned is not None
    assert errors == []
    assert any(
        "only available for part" in w for w in warnings
    )


def test_invalid_date_is_rejected():
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(date="not-a-date")
    )

    assert cleaned is None
    assert any("invalid dates" in e for e in errors)


def test_missing_item_name_is_rejected():
    cleaned, errors, _ = validate_sales_df(
        make_sales_df(item="")
    )

    assert cleaned is None
    assert any("missing item names" in e for e in errors)


def test_blank_category_is_replaced():
    cleaned, errors, warnings = validate_sales_df(
        make_sales_df(category="")
    )

    assert cleaned is not None
    assert errors == []
    assert cleaned.iloc[0]["category"] == "Uncategorized"
    assert any("blank categories" in w for w in warnings)


def test_duplicate_rows_are_preserved():
    df = pd.concat(
        [make_sales_df(), make_sales_df()],
        ignore_index=True,
    )

    cleaned, errors, warnings = validate_sales_df(df)

    assert cleaned is not None
    assert errors == []
    assert len(cleaned) == 2
    assert any("identical values" in w for w in warnings)


def test_future_date_generates_warning():
    future = (
        pd.Timestamp.today() + pd.Timedelta(days=30)
    ).strftime("%Y-%m-%d")

    cleaned, errors, warnings = validate_sales_df(
        make_sales_df(date=future)
    )

    assert cleaned is not None
    assert errors == []
    assert any("future" in w for w in warnings)


def test_old_date_generates_warning():
    cleaned, errors, warnings = validate_sales_df(
        make_sales_df(date="2000-01-01")
    )

    assert cleaned is not None
    assert errors == []
    assert any("more than 10 years old" in w for w in warnings)


def test_source_audit_flags_repeated_transaction_ids():
    raw = pd.DataFrame(
        {
            "transaction_id": ["A001", "A001", "A002"],
            "item": ["Latte", "Mocha", "Tea"],
        }
    )

    original = raw.copy(deep=True)
    messages = audit_source_transactions(raw)

    assert any(
        "share transaction_id" in message
        for message in messages
    )
    pd.testing.assert_frame_equal(raw, original)


def test_source_audit_flags_missing_transaction_ids():
    raw = pd.DataFrame(
        {
            "transaction_id": ["A001", None, ""],
            "item": ["Latte", "Mocha", "Tea"],
        }
    )

    messages = audit_source_transactions(raw)

    assert any(
        "2 rows" in message and "no transaction_id" in message
        for message in messages
    )


def test_source_audit_handles_no_transaction_id_column():
    raw = pd.DataFrame(
        {
            "item": ["Latte", "Mocha"],
            "price": [5.50, 6.00],
        }
    )

    messages = audit_source_transactions(raw)

    assert any(
        "no transaction_id column" in message
        for message in messages
    )


def test_source_audit_preserves_identical_records():
    raw = pd.DataFrame(
        {
            "transaction_id": ["A001", "A001"],
            "item": ["Latte", "Latte"],
        }
    )

    original = raw.copy(deep=True)
    messages = audit_source_transactions(raw)

    assert any(
        "identical full-source rows" in message
        for message in messages
    )
    assert len(raw) == 2
    pd.testing.assert_frame_equal(raw, original)
