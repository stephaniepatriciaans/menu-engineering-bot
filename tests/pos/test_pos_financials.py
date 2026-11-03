"""Regression tests for universal POS financial normalization."""

import numpy as np
import pandas as pd
import pytest

from pos.financials import normalize_pos_financials


@pytest.fixture
def pos_data():
    """Generate reproducible POS transactions."""
    rng = np.random.default_rng(42)
    n = 100

    prices = rng.uniform(1.0, 100.0, size=n).round(2)
    quantities = rng.integers(1, 20, size=n)

    gross = prices * quantities

    return pd.DataFrame({
        "price": prices,
        "units_sold": quantities,
        "discount_amount": (
            gross * rng.uniform(0.0, 0.4, size=n)
        ).round(2),
        "discount_percent": rng.uniform(
            0.0, 40.0, size=n
        ).round(2),
    })


@pytest.mark.parametrize("discount_type", ["amount", "percent"])
def test_listed_prices_normalize_discounted_revenue(
    pos_data,
    discount_type,
):
    """Listed prices should produce correct realized revenue."""
    original = pos_data.copy(deep=True)

    result = normalize_pos_financials(
        pos_data,
        price_basis="listed",
        discount_type=discount_type,
    )

    gross = pos_data["price"] * pos_data["units_sold"]

    if discount_type == "amount":
        expected_discount = pos_data["discount_amount"]
    else:
        expected_discount = (
            gross * pos_data["discount_percent"] / 100.0
        )

    expected_realized = gross - expected_discount

    np.testing.assert_allclose(
        result["source_line_amount"],
        gross,
    )

    np.testing.assert_allclose(
        result["discount_applied"],
        expected_discount,
    )

    np.testing.assert_allclose(
        result["realized_line_amount"],
        expected_realized,
    )

    pd.testing.assert_frame_equal(pos_data, original)


def test_unknown_basis_does_not_infer_revenue(pos_data):
    """Unknown price conventions must not produce realized revenue."""
    result = normalize_pos_financials(
        pos_data,
        price_basis="unknown",
        discount_type="amount",
    )

    assert result["realized_line_amount"].isna().all()
    assert result["discount_applied"].isna().all()


def test_realized_basis_does_not_subtract_discounts_twice(pos_data):
    """Already-discounted prices must not be discounted again."""
    result = normalize_pos_financials(
        pos_data,
        price_basis="realized",
        discount_type="amount",
    )

    expected = pos_data["price"] * pos_data["units_sold"]

    np.testing.assert_allclose(
        result["realized_line_amount"],
        expected,
    )

    np.testing.assert_allclose(
        result["discount_applied"],
        0.0,
    )


def test_refund_candidates_are_identified():
    """Negative quantities must remain refund candidates."""
    rng = np.random.default_rng(123)
    n = 40

    prices = rng.uniform(1.0, 50.0, size=n)
    quantities = rng.integers(1, 10, size=n)

    # Mark a subset as refund candidates.
    quantities[::5] *= -1

    df = pd.DataFrame({
        "price": prices,
        "units_sold": quantities,
        "discount_amount": np.zeros(n),
    })

    result = normalize_pos_financials(
        df,
        price_basis="listed",
        discount_type="amount",
    )

    refund_mask = quantities < 0

    np.testing.assert_array_equal(
        result["is_refund_candidate"],
        refund_mask,
    )

    assert result.loc[
        refund_mask, "realized_line_amount"
    ].isna().all()

    assert result.loc[
        refund_mask, "discount_applied"
    ].isna().all()


def test_missing_required_discount_column_is_rejected(pos_data):
    """Missing mapped discount fields must not be ignored."""
    df = pos_data.drop(columns=["discount_amount"])

    with pytest.raises(ValueError, match="Missing POS financial fields"):
        normalize_pos_financials(
            df,
            price_basis="listed",
            discount_type="amount",
        )


@pytest.mark.parametrize(
    "discount_type",
    ["amount", "percent", "unsupported"],
)
def test_invalid_discount_inputs_are_rejected(
    pos_data,
    discount_type,
):
    """Invalid discount conventions must not silently pass."""
    if discount_type == "unsupported":
        with pytest.raises(ValueError, match="discount_type"):
            normalize_pos_financials(
                pos_data,
                price_basis="listed",
                discount_type=discount_type,
            )
    else:
        df = pos_data.copy()
        column = (
            "discount_amount"
            if discount_type == "amount"
            else "discount_percent"
        )
        df.loc[0, column] = -1.0

        with pytest.raises(ValueError):
            normalize_pos_financials(
                df,
                price_basis="listed",
                discount_type=discount_type,
            )


def test_invalid_price_basis_is_rejected(pos_data):
    with pytest.raises(ValueError, match="Price basis"):
        normalize_pos_financials(
            pos_data,
            price_basis="invalid",
            discount_type="amount",
        )
