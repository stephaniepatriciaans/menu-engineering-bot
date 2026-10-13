"""Regression tests for analytics data-quality edge cases"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import (
    build_item_summary,
    recommend_price_moves,
    simulate_price_change,
)


def test_empty_dataset_returns_empty_analysis():
    """Empty data must not create fabricated analytics."""

    empty_sales = pd.DataFrame()

    summary = build_item_summary(empty_sales)

    assert isinstance(summary, pd.DataFrame)
    assert summary.empty

    moves = recommend_price_moves(summary)

    assert isinstance(moves, pd.DataFrame)
    assert moves.empty


def test_invalid_costs_and_prices_are_rejected():
    """Simulations must reject invalid financial inputs."""

    base_item = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    # Missing unit cost
    missing_cost = base_item.copy()
    missing_cost["unit_cost"] = float("nan")

    with pytest.raises(ValueError, match="requires unit cost"):
        simulate_price_change(missing_cost, 0.10)

    # Negative unit cost
    negative_cost = base_item.copy()
    negative_cost["unit_cost"] = -1.0

    with pytest.raises(ValueError, match="nonnegative"):
        simulate_price_change(negative_cost, 0.10)

    # Zero selling price
    zero_price = base_item.copy()
    zero_price["price"] = 0.0

    with pytest.raises(ValueError, match="positive"):
        simulate_price_change(zero_price, 0.10)

    # A 100% price decrease would produce a nonpositive price
    with pytest.raises(ValueError, match="above zero"):
        simulate_price_change(base_item, -1.0)


def test_elasticity_ignores_invalid_sales_records():
    """Invalid records must not influence elasticity estimation."""

    from analysis import estimate_elasticity

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "NaT",
        ]),
        "price": [5.0, 0.0, -2.0, 6.0],
        "units_sold": [20.0, 10.0, 15.0, 30.0],
    })

    result = estimate_elasticity(
        df,
        category="Coffee",
        category_priors={"Coffee": -1.4},
    )

    # Only the first record has a valid date,
    # positive price, and positive units.
    assert result["observations"] == 1
    assert result["price_points"] == 1
    assert result["price_variation_pct"] == pytest.approx(0.0)

    # Insufficient evidence requires a labeled prior.
    assert result["elasticity_source"] == "category_prior"
    assert result["elasticity_confidence"] == "Prior"
    assert result["elasticity"] == pytest.approx(-1.4)


def test_elasticity_with_no_valid_sales_uses_default_prior():
    """No valid records must not produce a historical estimate."""

    from analysis import estimate_elasticity

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-01-02",
            "NaT",
        ]),
        "price": [0.0, -5.0, 10.0],
        "units_sold": [10.0, 0.0, 20.0],
    })

    result = estimate_elasticity(
        df,
        category="UnknownTestCategory",
        category_priors={"Coffee": -1.4},
        default_prior=-1.7,
    )

    assert result["observations"] == 0
    assert result["price_points"] == 0
    assert result["price_variation_pct"] == pytest.approx(0.0)

    assert result["elasticity_source"] == "default_prior"
    assert result["elasticity_confidence"] == "Prior"
    assert result["elasticity"] == pytest.approx(-1.7)


def test_average_daily_units_uses_recorded_dates(monkeypatch):
    """Document the existing recorded-date averaging rule."""

    import analysis

    monkeypatch.setattr(
        analysis,
        "estimate_elasticity",
        lambda *args, **kwargs: {
            "elasticity": -1.2,
            "elasticity_source": "default_prior",
            "elasticity_confidence": "Prior",
            "price_points": 1,
            "observations": 1,
            "price_variation_pct": 0.0,
        },
    )

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-05",
            "2026-01-07",
        ]),
        "item": ["Latte", "Latte"],
        "category": ["Coffee", "Coffee"],
        "price": [5.0, 5.0],
        "units_sold": [10.0, 20.0],
    })

    summary = analysis.build_item_summary(df)

    assert len(summary) == 1

    item = summary.iloc[0]

    assert item["total_units_sold"] == pytest.approx(30.0)

    # Two distinct dates appear in the input, not three.
    assert item["avg_daily_units"] == pytest.approx(15.0)


def test_average_daily_units_counts_dates_without_item_sales(
    monkeypatch,
):
    """A date with another item's sales contributes to the denominator."""

    import analysis

    monkeypatch.setattr(
        analysis,
        "estimate_elasticity",
        lambda *args, **kwargs: {
            "elasticity": -1.2,
            "elasticity_source": "default_prior",
            "elasticity_confidence": "Prior",
            "price_points": 1,
            "observations": 1,
            "price_variation_pct": 0.0,
        },
    )

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-05",
            "2026-01-06",
            "2026-01-07",
        ]),
        "item": ["Latte", "Tea", "Latte"],
        "category": ["Coffee", "Tea", "Coffee"],
        "price": [5.0, 3.0, 5.0],
        "units_sold": [10.0, 5.0, 20.0],
    })

    summary = analysis.build_item_summary(df).set_index("item")

    latte_units = summary.loc[["Latte"], "avg_daily_units"].iloc[0]

    # Latte sells on two dates, but the dataset has
    # sales on three distinct dates.
    assert latte_units == pytest.approx(10.0)
