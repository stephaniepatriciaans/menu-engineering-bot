"""Regression tests for percentage-based POS discounts."""

import pandas as pd
import pytest

from pos_transactions import calculate_percentage_discounted_sales


def test_percentage_discount_calculation():
    df = pd.DataFrame({
        "price": [5.0, 3.0],
        "units_sold": [2, 1],
        "discount_percent": [20.0, 10.0],
    })

    result = calculate_percentage_discounted_sales(df)

    assert result["gross_line_amount"].sum() == pytest.approx(13.0)
    assert result["discount_amount"].sum() == pytest.approx(2.30)
    assert result["realized_line_amount"].sum() == pytest.approx(10.70)
    assert result.loc[0, "effective_unit_price"] == pytest.approx(4.0)


@pytest.mark.parametrize("percent", [-1, 101, float("nan"), "invalid"])
def test_invalid_percentages_are_rejected(percent):
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_percent": [percent],
    })

    with pytest.raises(ValueError):
        calculate_percentage_discounted_sales(df)


def test_percentage_discount_does_not_mutate_input():
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_percent": [20.0],
    })

    original = df.copy(deep=True)

    calculate_percentage_discounted_sales(df)

    pd.testing.assert_frame_equal(df, original)


def test_full_discount_produces_zero_realized_revenue():
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_percent": [100.0],
    })

    result = calculate_percentage_discounted_sales(df)

    assert result.loc[0, "discount_amount"] == pytest.approx(10.0)
    assert result.loc[0, "realized_line_amount"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("percent", "expected_discount", "expected_revenue"),
    [
        (0.0, 0.0, 10.0),
        (20.0, 2.0, 8.0),
        (50.0, 5.0, 5.0),
        (100.0, 10.0, 0.0),
    ],
)
def test_percentage_discount_boundaries(
    percent,
    expected_discount,
    expected_revenue,
):
    """Verify percentage calculations at valid boundaries."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_percent": [percent],
    })

    result = calculate_percentage_discounted_sales(df)

    assert result.loc[0, "gross_line_amount"] == pytest.approx(10.0)

    assert result.loc[0, "discount_amount"] == pytest.approx(
        expected_discount
    )

    assert result.loc[0, "realized_line_amount"] == pytest.approx(
        expected_revenue
    )


@pytest.mark.parametrize(
    "invalid_value",
    [None, float("inf"), -float("inf"), "unknown"],
)
def test_percentage_discount_rejects_nonfinite_values(invalid_value):
    """Missing and nonfinite percentages must be rejected."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_percent": [invalid_value],
    })

    with pytest.raises(
        ValueError,
        match="finite numeric values",
    ):
        calculate_percentage_discounted_sales(df)


def test_zero_quantity_has_no_realized_revenue():
    """Zero quantity cannot generate sales revenue."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [0],
        "discount_percent": [20.0],
    })

    result = calculate_percentage_discounted_sales(df)

    assert result.loc[0, "gross_line_amount"] == 0
    assert result.loc[0, "discount_amount"] == 0
    assert result.loc[0, "realized_line_amount"] == 0
    assert pd.isna(result.loc[0, "effective_unit_price"])
