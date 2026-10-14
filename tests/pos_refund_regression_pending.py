"""Regression tests for POS transaction edge cases."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation import validate_sales_df


def test_refund_rows_are_identified_without_losing_sales():
    """Refunds should be recognized separately from sales."""

    data = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
        ],
        "item": [
            "Latte",
            "Latte",
            "Tea",
        ],
        "price": [5.0, 5.0, 3.0],
        "units_sold": [2, -1, 3],
        "category": [
            "Coffee",
            "Coffee",
            "Tea",
        ],
    })

    cleaned, errors, warnings = validate_sales_df(data)

    assert cleaned is not None
    assert errors == []

    # Ordinary sales remain unchanged.
    assert cleaned.loc[0, "units_sold"] == 2
    assert cleaned.loc[2, "units_sold"] == 3

    # A negative quantity identifies a refund.
    assert cleaned.loc[1, "units_sold"] == -1

    # The application should make the refund explicit.
    assert any("refund" in message.lower() for message in warnings)
