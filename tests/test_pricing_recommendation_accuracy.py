"""Numerical tests for selecting pricing recommendations"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import recommend_price_moves


def test_recommendation_selects_highest_profit_scenario():
    """Select the candidate with the highest profit improvement"""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-1.2],
        "quadrant": ["Star"],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
    })

    # Compare unchanged price with a 10% increase.
    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
    )

    assert len(moves) == 1

    result = moves.iloc[0]

    # 10% increase provides +$0.80 in daily contribution profit.
    assert result["new_price"] == pytest.approx(5.50)
    assert result["daily_profit_delta"] == pytest.approx(0.80)
    assert result["pct_change_recommended"] == pytest.approx(10.0)

    # Historical estimate still requires review.
    assert result["pricing_reliability"] == (
        "Historical estimate — review required"
    )
    assert bool(result["requires_review"]) is True


def test_recommendation_can_choose_no_price_change():
    """Do not force a price increase when it reduces profit."""

    summary = pd.DataFrame({
        "item": ["Tea"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-3.0],
        "quadrant": ["Plowhorse"],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    # The function automatically adds the unchanged-price candidate.
    moves = recommend_price_moves(
        summary,
        price_changes=[0.10],
    )

    assert len(moves) == 1

    result = moves.iloc[0]

    # At elasticity -3:
    # Old profit = 10 * (5 - 2) = 30
    # New profit = 7 * (5.50 - 2) = 24.50
    # Therefore, no change is better.
    assert result["new_price"] == pytest.approx(5.00)
    assert result["daily_profit_delta"] == pytest.approx(0.00)
    assert result["pct_change_recommended"] == pytest.approx(0.0)

    assert result["pricing_reliability"] == (
        "Exploratory — category assumption"
    )
    assert bool(result["requires_review"]) is True


def test_conservative_mode_selects_expected_price():
    """Conservative mode must select the highest worst-case profit."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-1.2],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
        "quadrant": ["Star"],
    })

    candidates = [0.0, 0.05, 0.10, 0.20]

    # Independently calculate each candidate's worst-case
    # result using the existing scenario simulator.
    row = summary.iloc[0]

    from analysis import simulate_pricing_scenarios

    candidate_results = []

    for pct in candidates:
        scenarios = simulate_pricing_scenarios(
            row,
            pct_change=pct,
            elasticity_uncertainty=0.25,
        )

        worst_row = scenarios.loc[
            scenarios["scenario"] == "worst_case"
        ].iloc[0]

        candidate_results.append({
            "price": float(worst_row["new_price"]),
            "worst_delta": float(
                worst_row["daily_profit_delta"]
            ),
        })

    expected = max(
        candidate_results,
        key=lambda result: result["worst_delta"],
    )

    moves = recommend_price_moves(
        summary,
        price_changes=candidates,
        elasticity_uncertainty=0.25,
        selection_mode="conservative",
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    assert recommendation["new_price"] == pytest.approx(
        expected["price"]
    )

    assert recommendation["worst_case_daily_profit_delta"] == (
        pytest.approx(expected["worst_delta"])
    )
