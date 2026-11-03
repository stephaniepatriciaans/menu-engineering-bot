"""Regression tests for POS line-level discounts."""

import pandas as pd
import pytest

from pos_transactions import calculate_discounted_sales


def test_discounted_sale_calculates_realized_revenue():
    df = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [2.0],
    })

    result = calculate_discounted_sales(df)

    assert result.loc[0, "gross_line_amount"] == 10.0
    assert result.loc[0, "realized_line_amount"] == 8.0
    assert result.loc[0, "effective_unit_price"] == 4.0


def test_discounted_sales_preserve_original_data():
    df = pd.DataFrame({
        "price": [5.0, 3.0],
        "units_sold": [2, 1],
        "discount_amount": [2.0, 0.0],
    })

    original = df.copy(deep=True)

    calculate_discounted_sales(df)

    pd.testing.assert_frame_equal(df, original)


def test_discount_cannot_exceed_gross_sales():
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [11.0],
    })

    with pytest.raises(ValueError, match="exceed gross"):
        calculate_discounted_sales(df)


def test_negative_discount_is_rejected():
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [-1.0],
    })

    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_discounted_sales(df)


def test_zero_quantity_with_zero_discount():
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [0],
        "discount_amount": [0.0],
    })

    result = calculate_discounted_sales(df)

    assert result.loc[0, "gross_line_amount"] == 0
    assert result.loc[0, "realized_line_amount"] == 0
    assert pd.isna(result.loc[0, "effective_unit_price"])


@pytest.mark.parametrize(
    "invalid_discount",
    [None, float("nan"), "unknown", float("inf"), -float("inf")],
)
def test_invalid_discount_values_are_rejected(invalid_discount):
    """Missing, nonnumeric, and nonfinite discounts are invalid."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [invalid_discount],
    })

    with pytest.raises(
        ValueError,
        match="finite numeric values",
    ):
        calculate_discounted_sales(df)

def test_missing_discount_column_is_rejected():
    """A selected but absent discount field must not be ignored."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
    })

    with pytest.raises(
        ValueError,
        match="Missing discount calculation fields",
    ):
        calculate_discounted_sales(df)


def test_refund_candidate_cannot_enter_discount_calculator():
    """Refund candidates must be separated before discount analysis."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [-1],
        "discount_amount": [0.0],
    })

    with pytest.raises(
        ValueError,
        match="nonnegative quantities",
    ):
        calculate_discounted_sales(df)
