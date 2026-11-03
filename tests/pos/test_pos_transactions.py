"""Regression tests for POS refund candidate accounting."""

import pandas as pd
import pytest

from pos.transactions import (
    split_pos_transactions,
    summarize_pos_transactions,
)


def test_sale_and_refund_candidate_accounting():
    df = pd.DataFrame({
        "price": [5.0, 5.0, 3.0],
        "units_sold": [3, -1, 2],
    })

    result = summarize_pos_transactions(df)

    assert result["sale_rows"] == 2
    assert result["refund_candidate_rows"] == 1
    assert result["gross_units"] == 5
    assert result["refund_units"] == 1
    assert result["net_units"] == 4
    assert result["gross_revenue"] == 21
    assert result["refund_value"] == 5
    assert result["net_revenue"] == 16


def test_refund_summary_does_not_modify_source():
    df = pd.DataFrame({
        "price": [5.0, 5.0],
        "units_sold": [3, -1],
    })
    original = df.copy(deep=True)

    summarize_pos_transactions(df)

    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("quantity", [float("nan"), float("inf")])
def test_invalid_transaction_quantity_is_rejected(quantity):
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [quantity],
    })

    with pytest.raises(ValueError, match="finite"):
        summarize_pos_transactions(df)


def test_nonpositive_price_is_rejected():
    df = pd.DataFrame({
        "price": [0.0],
        "units_sold": [-1],
    })

    with pytest.raises(ValueError, match="greater than zero"):
        summarize_pos_transactions(df)


def test_split_preserves_sales_and_refund_candidates():
    """Separate rows without losing or modifying transactions."""
    df = pd.DataFrame({
        "item": ["Latte", "Latte", "Tea", "Mocha"],
        "price": [5.0, 5.0, 3.0, 6.0],
        "units_sold": [3, -1, 2, 0],
    })

    original = df.copy(deep=True)

    sales, refund_candidates = split_pos_transactions(df)

    assert sales["units_sold"].tolist() == [3, 2, 0]
    assert refund_candidates["units_sold"].tolist() == [-1]

    assert len(sales) + len(refund_candidates) == len(df)

    # Original row identities and values remain intact.
    assert set(sales.index).isdisjoint(
        set(refund_candidates.index)
    )
    assert set(sales.index).union(
        set(refund_candidates.index)
    ) == set(df.index)

    pd.testing.assert_frame_equal(df, original)


def test_split_rejects_invalid_quantities():
    """Missing and nonfinite quantities must not be classified."""
    df = pd.DataFrame({
        "price": [5.0, 3.0],
        "units_sold": [2, float("nan")],
    })

    with pytest.raises(ValueError, match="finite"):
        split_pos_transactions(df)
