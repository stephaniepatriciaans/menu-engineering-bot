import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import format_currency
from ui.table_formatters import (
    display_item_table,
    display_moves_table,
)


def test_item_table_without_cost():
    original = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.5],
        "total_revenue": [110.0],
    })
    before = original.copy(deep=True)

    result = display_item_table(
        original, "USD", has_cost=False
    )

    assert result.loc[0, "price"] == format_currency(5.5, "USD")
    assert result.loc[0, "total_revenue"] == format_currency(
        110.0, "USD"
    )
    assert_frame_equal(original, before)


def test_item_table_with_cost():
    original = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.5],
        "total_revenue": [110.0],
        "unit_cost": [2.0],
        "contribution_margin_amount": [3.5],
        "total_profit": [70.0],
    })

    result = display_item_table(
        original, "USD", has_cost=True
    )

    for col in [
        "price",
        "total_revenue",
        "unit_cost",
        "contribution_margin_amount",
        "total_profit",
    ]:
        assert result.loc[0, col] == format_currency(
            original.loc[0, col], "USD"
        )


def test_moves_table_preserves_original():
    original = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [12.0],
        "pricing_reliability": ["Exploratory"],
    })
    before = original.copy(deep=True)

    result = display_moves_table(original, "USD")

    assert result.loc[0, "old_price"] == format_currency(5.0, "USD")
    assert result.loc[0, "new_price"] == format_currency(5.5, "USD")
    assert result.loc[0, "daily_profit_delta"] == format_currency(
        12.0, "USD"
    )
    assert result.loc[0, "pricing_reliability"] == "Exploratory"
    assert_frame_equal(original, before)
