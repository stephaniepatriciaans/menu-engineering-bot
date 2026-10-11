import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from analysis import simulate_price_change


def make_item(price=3.25, unit_cost=1.00, units=20.0, elasticity=-0.8):
    return pd.Series({
        "item": "Test Latte",
        "price": price,
        "unit_cost": unit_cost,
        "avg_daily_units": units,
        "elasticity": elasticity,
    })


def test_price_rounding_and_actual_percentage():
    result = simulate_price_change(make_item(), 0.15)

    assert result["old_price"] == pytest.approx(3.25)
    assert result["new_price"] == pytest.approx(3.74)

    actual_change = (3.74 - 3.25) / 3.25 * 100

    assert result["pct_change_recommended"] == pytest.approx(
        round(actual_change, 1)
    )


def test_profit_uses_rounded_price():
    result = simulate_price_change(make_item(), 0.15)

    actual_change = (3.74 - 3.25) / 3.25
    expected_units = 20.0 * (1 - 0.8 * actual_change)
    expected_profit = expected_units * (3.74 - 1.00)

    assert result["new_daily_profit_est"] == pytest.approx(
        round(expected_profit, 2)
    )


def test_no_price_change():
    result = simulate_price_change(make_item(), 0.0)

    assert result["new_price"] == pytest.approx(3.25)
    assert result["pct_change_recommended"] == pytest.approx(0.0)
    assert result["daily_profit_delta"] == pytest.approx(0.0)


def test_missing_cost_raises_error():
    with pytest.raises(ValueError):
        simulate_price_change(make_item(unit_cost=float("nan")), 0.15)


def test_invalid_price_change_raises_error():
    with pytest.raises(ValueError):
        simulate_price_change(make_item(), -1.0)
