"""Numerical accuracy tests for pricing simulations."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import(
    recommend_price_moves,
    simulate_price_change,
    simulate_pricing_scenarios,
)


def test_price_increase_calculates_demand_and_profit():
    """Verify a 10% price increase using known financial values."""

    item = pd.Series({
        "item": "Latte",
        "price": 5.00,
        "unit_cost": 2.00,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    result = simulate_price_change(
        item,
        pct_change=0.10,
    )

    # New price = 5.00 * 1.10 = 5.50
    assert result["old_price"] == pytest.approx(5.00)
    assert result["new_price"] == pytest.approx(5.50)

    # Actual price increase = 10%
    assert result["pct_change_recommended"] == pytest.approx(
        10.0
    )

    # Demand change = -1.2 * 10% = -12%
    # New daily units = 10 * 0.88 = 8.8
    assert result["old_daily_units_est"] == pytest.approx(
        10.0
    )
    assert result["new_daily_units_est"] == pytest.approx(
        8.8
    )

    # Old daily contribution profit:
    # 10 * (5.00 - 2.00) = 30.00
    assert result["old_daily_profit_est"] == pytest.approx(
        30.00
    )

    # New daily contribution profit:
    # 8.8 * (5.50 - 2.00) = 30.80
    assert result["new_daily_profit_est"] == pytest.approx(
        30.80
    )

    # Change in daily profit = 30.80 - 30.00 = 0.80
    assert result["daily_profit_delta"] == pytest.approx(
        0.80
    )


def test_price_rounding_and_missing_cost_validation():
    """Verify cent rounding and rejection of unavailable costs."""

    item = pd.Series({
        "item": "Tea",
        "price": 1.01,
        "unit_cost": 0.40,
        "avg_daily_units": 100.0,
        "elasticity": -1.0,
    })

    result = simulate_price_change(
        item,
        pct_change=0.05,
    )

    # Requested price = 1.01 * 1.05 = 1.0605
    # Rounded actual selling price = 1.06
    assert result["new_price"] == pytest.approx(1.06)

    # Actual change = (1.06 - 1.01) / 1.01
    actual_change = (1.06 - 1.01) / 1.01

    assert result["pct_change_recommended"] == pytest.approx(
        round(actual_change * 100, 1)
    )

    # Demand must use the actual rounded price change.
    expected_units = 100 * (1 - actual_change)

    assert result["new_daily_units_est"] == pytest.approx(
        round(expected_units, 1)
    )

    # Profit calculations use unrounded demand.
    old_profit = 100 * (1.01 - 0.40)
    new_profit = expected_units * (1.06 - 0.40)

    assert result["old_daily_profit_est"] == pytest.approx(
        round(old_profit, 2)
    )
    assert result["new_daily_profit_est"] == pytest.approx(
        round(new_profit, 2)
    )
    assert result["daily_profit_delta"] == pytest.approx(
        round(new_profit - old_profit, 2)
    )

    # Missing costs must not produce fabricated profit.
    item_without_cost = item.copy()
    item_without_cost["unit_cost"] = float("nan")

    with pytest.raises(
        ValueError,
        match="requires unit cost data",
    ):
        simulate_price_change(
            item_without_cost,
            pct_change=0.05,
        )


def test_price_simulation_rejects_nonfinite_inputs():
    """Invalid numeric inputs must not reach profit calculations."""

    row = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    for invalid_change in [
        float("nan"),
        float("inf"),
        float("-inf"),
    ]:
        with pytest.raises(ValueError):
            simulate_price_change(row, invalid_change)

    bad_units = row.copy()
    bad_units["avg_daily_units"] = float("inf")

    with pytest.raises(
        ValueError,
        match="Average daily units",
    ):
        simulate_price_change(bad_units, 0.10)

    bad_elasticity = row.copy()
    bad_elasticity["elasticity"] = float("nan")

    with pytest.raises(
        ValueError,
        match="Elasticity must be finite",
    ):
        simulate_price_change(bad_elasticity, 0.10)


def test_price_simulation_rejects_price_rounding_to_zero():
    """A positive price must remain positive after cent rounding."""

    row = pd.Series({
        "item": "Tiny Sample",
        "price": 0.001,
        "unit_cost": 0.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    with pytest.raises(
        ValueError,
        match="Original price must round",
    ):
        simulate_price_change(row, 0.10)


def test_pricing_respects_maximum_increase():
    """Recommendations must not exceed the allowed price increase."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-0.5],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
        "quadrant": ["Star"],
    })

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.05, 0.10, 0.20],
        max_price_increase=0.10,
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    assert recommendation["new_price"] <= 5.50
    assert recommendation["new_price"] == pytest.approx(5.50)


def test_pricing_respects_minimum_margin():
    """Recommendations must satisfy the minimum contribution margin."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [4.0],
        "avg_daily_units": [10.0],
        "elasticity": [-0.5],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
        "quadrant": ["Plowhorse"],
    })

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.05, 0.10, 0.20],
        min_margin_pct=30.0,
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    price = float(recommendation["new_price"])
    margin_pct = (price - 4.0) / price * 100

    assert margin_pct >= 30.0
    assert price == pytest.approx(6.0)


def test_pricing_rejects_invalid_constraints():
    """Invalid constraint settings must raise clear errors."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-0.5],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    for invalid_limit in [-0.1, float("nan"), float("inf")]:
        with pytest.raises(
            ValueError,
            match="Maximum price increase",
        ):
            recommend_price_moves(
                summary,
                max_price_increase=invalid_limit,
            )

    for invalid_margin in [-1.0, 101.0, float("nan")]:
        with pytest.raises(
            ValueError,
            match="Minimum margin",
        ):
            recommend_price_moves(
                summary,
                min_margin_pct=invalid_margin,
            )


def test_pricing_returns_no_move_when_constraints_impossible():
    """Do not suggest an item price that violates the margin floor."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [4.5],
        "avg_daily_units": [10.0],
        "elasticity": [-0.5],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.05, 0.10],
        max_price_increase=0.10,
        min_margin_pct=50.0,
    )

    assert moves.empty


def test_pricing_constraint_uses_actual_rounded_price():
    """A rounded candidate must satisfy the maximum increase."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [0.99],
        "unit_cost": [0.20],
        "avg_daily_units": [10.0],
        "elasticity": [-0.1],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
        max_price_increase=0.10,
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    # $0.99 * 1.10 = $1.089 rounds to $1.09.
    # Actual increase is about 10.10%, above the 10% cap.
    # Therefore the candidate must be excluded.
    assert recommendation["new_price"] == pytest.approx(0.99)
    assert recommendation["daily_profit_delta"] == pytest.approx(0.0)


def test_pricing_scenarios_order_profit_for_price_increase():
    """Best/base/worst cases should reflect elasticity sensitivity."""

    row = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    scenarios = simulate_pricing_scenarios(
        row,
        pct_change=0.10,
        elasticity_uncertainty=0.25,
    )

    assert scenarios["scenario"].tolist() == [
        "best_case",
        "base_case",
        "worst_case",
    ]

    by_scenario = scenarios.set_index(
        "scenario"
    ).to_dict(orient="index")

    best = by_scenario["best_case"]["daily_profit_delta"]
    base = by_scenario["base_case"]["daily_profit_delta"]
    worst = by_scenario["worst_case"]["daily_profit_delta"]

    assert best > base > worst

    assert by_scenario["best_case"]["assumed_elasticity"] == (
        pytest.approx(-0.9)
    )

    assert by_scenario["base_case"]["assumed_elasticity"] == (
        pytest.approx(-1.2)
    )

    assert by_scenario["worst_case"]["assumed_elasticity"] == (
        pytest.approx(-1.5)
    )


def test_pricing_scenarios_reject_invalid_uncertainty():
    """Invalid sensitivity parameters must not produce scenarios."""

    row = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    for invalid in [
        -0.1,
        1.1,
        float("nan"),
        float("inf"),
    ]:
        with pytest.raises(
            ValueError,
            match="Elasticity uncertainty",
        ):
            simulate_pricing_scenarios(
                row,
                pct_change=0.10,
                elasticity_uncertainty=invalid,
            )


def test_pricing_scenarios_order_profit_for_price_decrease():
    """Best and worst must remain correct when prices decrease."""

    row = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    scenarios = simulate_pricing_scenarios(
        row,
        pct_change=-0.10,
        elasticity_uncertainty=0.25,
    )

    by_scenario = scenarios.set_index(
        "scenario"
    ).to_dict(orient="index")

    best = by_scenario["best_case"]["daily_profit_delta"]
    base = by_scenario["base_case"]["daily_profit_delta"]
    worst = by_scenario["worst_case"]["daily_profit_delta"]

    assert best >= base >= worst

    # With a price decrease, stronger demand response
    # produces the more favorable profit scenario.
    assert by_scenario["best_case"]["assumed_elasticity"] == (
        pytest.approx(-1.5)
    )

    assert by_scenario["base_case"]["assumed_elasticity"] == (
        pytest.approx(-1.2)
    )

    assert by_scenario["worst_case"]["assumed_elasticity"] == (
        pytest.approx(-0.9)
    )


def test_pricing_scenarios_zero_change_has_no_profit_impact():
    """Unchanged prices should yield zero profit difference."""

    row = pd.Series({
        "item": "Latte",
        "price": 5.0,
        "unit_cost": 2.0,
        "avg_daily_units": 10.0,
        "elasticity": -1.2,
    })

    scenarios = simulate_pricing_scenarios(
        row,
        pct_change=0.0,
        elasticity_uncertainty=0.25,
    )

    assert scenarios["scenario"].tolist() == [
        "best_case",
        "base_case",
        "worst_case",
    ]

    assert scenarios["daily_profit_delta"].tolist() == (
        pytest.approx([0.0, 0.0, 0.0])
    )


def test_recommendation_includes_sensitivity_scenarios():
    """Recommendations must include alternative profit outcomes."""

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

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    assert recommendation["best_case_daily_profit_delta"] >= (
        recommendation["base_case_daily_profit_delta"]
    )

    assert recommendation["base_case_daily_profit_delta"] >= (
        recommendation["worst_case_daily_profit_delta"]
    )

    assert recommendation["scenario_uncertainty_pct"] == (
        pytest.approx(25.0)
    )

    assert bool(recommendation["requires_review"]) is True


def test_recommendation_flags_pessimistic_profit_loss():
    """A candidate can be positive centrally but negative pessimistically."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-2.0],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
        "quadrant": ["Star"],
    })

    moves = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
    )

    assert len(moves) == 1

    recommendation = moves.iloc[0]

    assert recommendation["base_case_daily_profit_delta"] >= 0

    if recommendation["worst_case_daily_profit_delta"] < 0:
        assert bool(recommendation["worst_case_loss"]) is True

    assert bool(recommendation["requires_review"]) is True


def test_recommendation_supports_configurable_uncertainty():
    """Sensitivity width should change without changing the base case."""

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

    narrow = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
        elasticity_uncertainty=0.10,
    )

    wide = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.10],
        elasticity_uncertainty=0.50,
    )

    assert len(narrow) == 1
    assert len(wide) == 1

    narrow_row = narrow.iloc[0]
    wide_row = wide.iloc[0]

    assert narrow_row["scenario_uncertainty_pct"] == (
        pytest.approx(10.0)
    )
    assert wide_row["scenario_uncertainty_pct"] == (
        pytest.approx(50.0)
    )

    assert narrow_row["base_case_daily_profit_delta"] == (
        pytest.approx(
            wide_row["base_case_daily_profit_delta"]
        )
    )

    narrow_range = (
        narrow_row["best_case_daily_profit_delta"]
        - narrow_row["worst_case_daily_profit_delta"]
    )

    wide_range = (
        wide_row["best_case_daily_profit_delta"]
        - wide_row["worst_case_daily_profit_delta"]
    )

    assert wide_range > narrow_range


def test_recommendation_rejects_invalid_uncertainty():
    """Reject invalid sensitivity settings before simulating prices."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-1.2],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
    })

    for invalid in [
        -0.1,
        1.1,
        float("nan"),
        float("inf"),
    ]:
        with pytest.raises(
            ValueError,
            match="Elasticity uncertainty",
        ):
            recommend_price_moves(
                summary,
                elasticity_uncertainty=invalid,
            )


def test_conservative_mode_prefers_safer_price():
    """Conservative mode can choose a different candidate."""

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

    base = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.05, 0.10, 0.20],
        selection_mode="base_case",
    )

    conservative = recommend_price_moves(
        summary,
        price_changes=[0.0, 0.05, 0.10, 0.20],
        selection_mode="conservative",
    )

    assert len(base) == 1
    assert len(conservative) == 1

    base_row = base.iloc[0]
    conservative_row = conservative.iloc[0]

    # Conservative selection should not have a worse
    # pessimistic result than the base-case selection.
    assert (
        conservative_row["worst_case_daily_profit_delta"]
        >= base_row["worst_case_daily_profit_delta"]
    )


def test_pricing_rejects_invalid_selection_mode():
    """Unknown selection modes must be rejected."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "unit_cost": [2.0],
        "avg_daily_units": [10.0],
        "elasticity": [-1.2],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
    })

    with pytest.raises(
        ValueError,
        match="Selection mode",
    ):
        recommend_price_moves(
            summary,
            selection_mode="unknown",
        )
