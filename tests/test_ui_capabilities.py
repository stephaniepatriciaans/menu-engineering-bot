"""Tests for dataset capability reporting"""

import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.capabilities import build_capability_report, capability_line


def make_capabilities(
    *,
    profit_enabled: bool = True,
) -> dict[str, bool]:
    """Create controlled dataset capability flags."""

    return {
        "revenue_analysis": True,
        "popularity_analysis": True,
        "sales_trend_analysis": True,
        "price_variation_analysis": True,
        "profit_analysis": profit_enabled,
        "menu_engineering_quadrants": profit_enabled,
        "price_optimization": profit_enabled,
    }


def test_capability_line_formats_status():
    """Capability labels show the correct status and reason."""

    assert capability_line(True, "Revenue") == "✓ Revenue"
    assert capability_line(False, "Profit") == "✗ Profit"

    assert capability_line(
        False,
        "Profit",
        "missing costs",
    ) == "✗ Profit — missing costs"


def test_capability_report_counts_elasticity_evidence():
    """Elasticity counts are derived from the supplied summary."""

    summary = pd.DataFrame({
        "item": ["Latte", "Tea", "Cookie", "Sandwich"],
        "elasticity_source": [
            "estimated",
            "estimated",
            "category_prior",
            "default_prior",
        ],
        "elasticity_confidence": [
            "high",
            "low",
            "low",
            "low",
        ],
    })

    original = summary.copy(deep=True)

    report = build_capability_report(
        summary,
        make_capabilities(),
        cost_is_assumption=False,
    )

    elasticity_line = next(
        line
        for line in report
        if "Historical elasticity estimation" in line
    )

    assert elasticity_line.startswith("✓")
    assert "2 of 4 items estimated" in elasticity_line
    assert "1 low confidence" in elasticity_line
    assert "1 category priors" in elasticity_line
    assert "1 default priors" in elasticity_line

    # The builder must not mutate its source data.
    assert_frame_equal(summary, original)


def test_capability_report_disables_profit_without_costs():
    """Missing costs must never be reported as profit-ready."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["low"],
    })

    report = build_capability_report(
        summary,
        make_capabilities(profit_enabled=False),
        cost_is_assumption=False,
    )

    for label in (
        "Profit analysis",
        "Menu Engineering Quadrants",
        "Profit-based price recommendations",
    ):
        matching = [
            line
            for line in report
            if label in line
        ]

        assert len(matching) == 1
        assert matching[0].startswith("✗")
        assert "unit cost missing or incomplete" in matching[0]


def test_capability_report_labels_assumed_costs():
    """Estimated costs must be explicitly described as assumptions."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "elasticity_source": ["category_prior"],
    })

    report = build_capability_report(
        summary,
        make_capabilities(),
        cost_is_assumption=True,
    )

    assert any(
        "Profit analysis — cost is a scenario assumption" in line
        for line in report
    )

    assert any(
        "Menu Engineering Quadrants — based on assumed costs" in line
        for line in report
    )

    assert any(
        "Profit-based price recommendations — scenario only" in line
        for line in report
    )


def test_capability_report_handles_missing_elasticity_columns():
    """Incomplete summaries must not cause capability reporting errors."""

    summary = pd.DataFrame({
        "item": ["Latte", "Tea"],
    })

    original = summary.copy(deep=True)

    report = build_capability_report(
        summary,
        make_capabilities(),
        cost_is_assumption=False,
    )

    elasticity_line = next(
        line
        for line in report
        if "Historical elasticity estimation" in line
    )

    assert elasticity_line.startswith("✗")
    assert "No historical estimates among 2 items" in elasticity_line

    assert_frame_equal(summary, original)
