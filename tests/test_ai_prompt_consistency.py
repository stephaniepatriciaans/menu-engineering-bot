"""Numerical and metadata consistency tests for the AI memo prompt."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent import build_elasticity_summary, build_user_prompt


def extract_json_section(prompt: str, heading: str):
    """Read a JSON section from the generated AI prompt."""
    content = prompt.split(f"{heading}\n", 1)[1]
    content = content.split("\n\n", 1)[0]
    return json.loads(content)


def test_ai_prompt_preserves_financial_results():
    """The AI prompt must retain computed financial values."""

    summary = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "category": ["Coffee", "Tea"],
        "price": [5.0, 3.0],
        "avg_daily_units": [10.0, 5.0],
        "total_units_sold": [100.0, 50.0],
        "total_revenue": [500.0, 150.0],
        "unit_cost": [2.0, 1.0],
        "contribution_margin_%": [60.0, 66.7],
        "total_profit": [300.0, 100.0],
        "quadrant": ["Star", "Puzzle"],
        "elasticity": [-1.2, -1.4],
        "elasticity_source": [
            "estimated",
            "category_prior",
        ],
        "elasticity_confidence": [
            "High",
            "Prior",
        ],
        "price_points": [5, 1],
        "observations": [40, 2],
        "price_variation_%": [20.0, 0.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "pct_change_recommended": [10.0],
        "daily_profit_delta": [0.8],
        "quadrant": ["Star"],
        "elasticity": [-1.2],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
    })

    original_summary = summary.copy(deep=True)
    original_moves = moves.copy(deep=True)

    prompt = build_user_prompt(
        summary,
        moves,
        metadata={
            "business_name": "Test Cafe",
            "dataset_name": "January Sales",
            "currency": "USD",
            "cost_basis": "actual",
            "cost_is_assumption": False,
        },
        capabilities={
            "profit_analysis": True,
            "price_optimization": True,
        },
    )

    item_records = extract_json_section(
        prompt,
        "ITEM SUMMARY (deterministic calculations):",
    )

    move_records = extract_json_section(
        prompt,
        "PRICE RECOMMENDATIONS "
        "(deterministic simulation results):",
    )

    elasticity_info = extract_json_section(
        prompt,
        "ELASTICITY RELIABILITY SUMMARY:",
    )

    # The original computed values must be preserved.
    assert item_records[0]["item"] == "Latte"
    assert item_records[0]["total_revenue"] == pytest.approx(
        500.0
    )
    assert item_records[0]["total_profit"] == pytest.approx(
        300.0
    )

    assert move_records[0]["new_price"] == pytest.approx(
        5.5
    )
    assert move_records[0]["daily_profit_delta"] == (
        pytest.approx(0.8)
    )

    # Verify the reliability summary.
    assert elasticity_info["total_items"] == 2
    assert elasticity_info["historically_estimated_items"] == 1
    assert elasticity_info["category_prior_items"] == 1
    assert elasticity_info["high_confidence_estimates"] == 1

    # Source data must remain unchanged.
    assert_frame_equal(summary, original_summary)
    assert_frame_equal(moves, original_moves)


def test_ai_prompt_without_profit_data():
    """Missing cost data must not generate financial claims."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "category": ["Coffee"],
        "price": [5.0],
        "avg_daily_units": [10.0],
        "total_units_sold": [100.0],
        "total_revenue": [500.0],
        "elasticity": [-1.4],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    prompt = build_user_prompt(
        summary,
        moves_df=None,
        metadata={
            "business_name": "Test Cafe",
            "currency": "USD",
            "cost_basis": "unavailable",
            "cost_is_assumption": False,
        },
        capabilities={
            "profit_analysis": False,
            "price_optimization": False,
        },
    )

    item_records = extract_json_section(
        prompt,
        "ITEM SUMMARY (deterministic calculations):",
    )

    # Revenue and volume are still available.
    assert item_records[0]["total_revenue"] == pytest.approx(
        500.0
    )
    assert item_records[0]["total_units_sold"] == pytest.approx(
        100.0
    )

    # No unit cost or profit has been invented.
    assert "unit_cost" not in item_records[0]
    assert "total_profit" not in item_records[0]

    # The prompt explicitly forbids profit-impact claims.
    assert "PRICE RECOMMENDATIONS: unavailable." in prompt
    assert "Do not make profit-impact claims." in prompt

    elasticity_info = build_elasticity_summary(summary)

    assert elasticity_info["historically_estimated_items"] == 0
    assert elasticity_info["category_prior_items"] == 1


def test_ai_prompt_includes_pricing_reliability():
    """Pricing reliability fields must reach the AI unchanged."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "total_revenue": [500.0],
        "elasticity": [-1.4],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "pct_change_recommended": [10.0],
        "daily_profit_delta": [0.8],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["Prior"],
        "pricing_reliability": [
            "Exploratory — category assumption"
        ],
        "reliability_reason": [
            "Elasticity is assumed from the product category."
        ],
        "requires_review": [True],
    })

    prompt = build_user_prompt(
        summary,
        moves,
        metadata={
            "business_name": "Test Cafe",
            "currency": "USD",
            "cost_basis": "estimated",
            "cost_is_assumption": True,
        },
        capabilities={
            "profit_analysis": True,
            "price_optimization": True,
        },
    )

    records = extract_json_section(
        prompt,
        "PRICE RECOMMENDATIONS "
        "(deterministic simulation results):",
    )

    assert len(records) == 1

    result = records[0]

    assert result["pricing_reliability"] == (
        "Exploratory — category assumption"
    )

    assert result["reliability_reason"] == (
        "Elasticity is assumed from the product category."
    )

    assert result["requires_review"] is True

    assert result["daily_profit_delta"] == pytest.approx(
        0.8
    )


def test_ai_system_prompt_explains_profit_limitations():
    """The AI instructions must distinguish simulated and net profit."""

    from agent import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.lower()

    assert "contribution profit" in prompt
    assert "net profit" in prompt
    assert "daily_profit_delta" in prompt

    assert "pricing_reliability" in prompt
    assert "reliability_reason" in prompt
    assert "requires_review" in prompt

    assert "percentage change is zero" in prompt


def test_ai_prompt_includes_pricing_scenarios():
    """The AI prompt should preserve numerical sensitivity results."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "total_revenue": [500.0],
        "elasticity": [-1.2],
        "elasticity_source": ["estimated"],
        "elasticity_confidence": ["High"],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
        "best_case_daily_profit_delta": [1.8],
        "base_case_daily_profit_delta": [0.8],
        "worst_case_daily_profit_delta": [-0.2],
        "scenario_uncertainty_pct": [25.0],
        "worst_case_loss": [True],
    })

    prompt = build_user_prompt(
        summary,
        moves,
        metadata={"currency": "USD"},
        capabilities={"profit_analysis": True},
    )

    records = extract_json_section(
        prompt,
        "PRICE RECOMMENDATIONS "
        "(deterministic simulation results):",
    )

    assert len(records) == 1

    result = records[0]

    assert result["best_case_daily_profit_delta"] == (
        pytest.approx(1.8)
    )
    assert result["base_case_daily_profit_delta"] == (
        pytest.approx(0.8)
    )
    assert result["worst_case_daily_profit_delta"] == (
        pytest.approx(-0.2)
    )
    assert result["scenario_uncertainty_pct"] == (
        pytest.approx(25.0)
    )
    assert result["worst_case_loss"] is True


def test_ai_system_prompt_labels_sensitivity_limitations():
    """AI instructions must not represent scenarios as guarantees."""

    from agent import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.lower()

    assert "sensitivity analyses" in prompt
    assert "confidence intervals" in prompt
    assert "worst_case_loss" in prompt
    assert "guarantees" in prompt or "guaranteed" in prompt

def test_ai_prompt_includes_selection_mode():
    """Claude should receive the actual pricing selection mode."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "total_revenue": [500.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
        "selection_mode": ["conservative"],
    })

    prompt = build_user_prompt(
        summary,
        moves,
        metadata={"currency": "USD"},
        capabilities={"profit_analysis": True},
    )

    records = extract_json_section(
        prompt,
        "PRICE RECOMMENDATIONS "
        "(deterministic simulation results):",
    )

    assert records[0]["selection_mode"] == "conservative"


def test_ai_system_prompt_explains_selection_modes():
    """The AI must distinguish central and conservative selection."""

    from agent import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.lower()

    assert "selection_mode" in prompt
    assert "base_case" in prompt
    assert "conservative" in prompt
    assert "worst-case" in prompt
    
def test_ai_system_prompt_requires_exact_financial_values():
    """Claude must be instructed to preserve exact financial amounts."""
    from agent import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.lower()

    assert "preserve all monetary values exactly" in prompt
    assert "two decimal places" in prompt
    assert "never round monetary totals" in prompt
    assert "never truncate" in prompt
    assert "never assign one item's financial values" in prompt