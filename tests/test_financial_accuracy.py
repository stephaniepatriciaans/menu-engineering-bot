"""Numerical accuracy tests for financial calculations"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analysis


def test_financial_calculations_with_complete_costs(monkeypatch):
    """Verify revenue, costs, margins, and historical profit."""

    # Avoid elasticity estimation influencing this financial test.
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
            "2026-01-01",
            "2026-01-02",
            "2026-01-01",
            "2026-01-02",
        ]),
        "item": ["Latte", "Latte", "Tea", "Tea"],
        "category": ["Coffee", "Coffee", "Tea", "Tea"],
        "price": [5.0, 6.0, 3.0, 3.0],
        "units_sold": [10, 5, 4, 6],
        "unit_cost": [2.0, 2.5, 1.0, 1.0],
    })

    original = df.copy(deep=True)

    summary = analysis.build_item_summary(df)

    assert len(summary) == 2

    item_rows = summary.set_index("item").to_dict(
        orient="index"
    )

    latte = item_rows["Latte"]
    tea = item_rows["Tea"]

    # LATTE
    # Revenue = (5 * 10) + (6 * 5) = 80
    assert latte["total_revenue"] == pytest.approx(80.0)

    # Total units = 10 + 5 = 15
    assert latte["total_units_sold"] == pytest.approx(15.0)

    # Average daily units = 15 / 2 = 7.5
    assert latte["avg_daily_units"] == pytest.approx(7.5)

    # Current selling price is the latest price.
    assert latte["price"] == pytest.approx(6.0)

    # Current unit cost is the latest unit cost.
    assert latte["unit_cost"] == pytest.approx(2.5)

    # Current contribution margin = 6 - 2.5 = 3.5
    assert latte["contribution_margin_amount"] == pytest.approx(
        3.5
    )

    # Contribution margin % = 3.5 / 6 * 100 = 58.3
    assert latte["contribution_margin_%"] == pytest.approx(
        58.3
    )

    # Historical total cost = (2 * 10) + (2.5 * 5) = 32.5
    # Historical contribution profit = 80 - 32.5 = 47.5
    assert latte["total_profit"] == pytest.approx(47.5)

    # TEA
    # Revenue = (3 * 4) + (3 * 6) = 30
    assert tea["total_revenue"] == pytest.approx(30.0)

    # Total units = 4 + 6 = 10
    assert tea["total_units_sold"] == pytest.approx(10.0)

    # Average daily units = 10 / 2 = 5
    assert tea["avg_daily_units"] == pytest.approx(5.0)

    # Margin = 3 - 1 = 2
    assert tea["contribution_margin_amount"] == pytest.approx(
        2.0
    )

    # Margin % = 2 / 3 * 100 = 66.7
    assert tea["contribution_margin_%"] == pytest.approx(
        66.7
    )

    # Contribution profit = 30 - 10 = 20
    assert tea["total_profit"] == pytest.approx(20.0)

    # Summary should be sorted by profit when costs are complete.
    assert list(summary["item"]) == ["Latte", "Tea"]

    # Original transactions should remain unchanged.
    pd.testing.assert_frame_equal(df, original)


def test_financial_calculations_with_missing_costs(monkeypatch):
    """Verify incomplete cost data does not fabricate profits."""

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
            "2026-01-01",
            "2026-01-02",
        ]),
        "item": ["Latte", "Tea"],
        "category": ["Coffee", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [10, 5],
        "unit_cost": [2.0, float("nan")],
    })

    summary = analysis.build_item_summary(df)

    # Revenue remains available without complete costs.
    assert summary["total_revenue"].sum() == pytest.approx(
        65.0
    )

    # Existing application policy:
    # Missing any unit cost disables profit metrics globally.
    financial_columns = [
        "unit_cost",
        "contribution_margin_amount",
        "contribution_margin_%",
        "total_profit",
    ]

    for column in financial_columns:
        assert summary[column].isna().all()

    # Quadrants must not be assigned without complete costs.
    assert summary["quadrant"].isna().all()

    # Without complete costs, sort by revenue.
    assert list(summary["item"]) == ["Latte", "Tea"]
