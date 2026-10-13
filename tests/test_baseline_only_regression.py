"""Regression checks for independent baseline-only evaluation."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_evaluation import (
    build_model_evaluation_report,
    evaluate_all_items,
    summarize_model_coverage,
)


def constant_price_sales() -> pd.DataFrame:
    """Five recorded days, no price variation, known forecast errors."""
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5),
        "item": ["Tea"] * 5,
        "price": [3.0] * 5,
        "units_sold": [10.0, 10.0, 10.0, 14.0, 16.0],
    })


def test_constant_price_item_gets_baseline_scores():
    """Constant prices block elasticity, not historical-average errors."""
    result = evaluate_all_items(
        constant_price_sales(), train_fraction=0.6
    ).iloc[0]

    assert result["status"] == "baseline_only"
    assert result["train_days"] == 3
    assert result["test_days"] == 2
    # The training mean is 10; test actuals are 14 and 16.
    assert result["baseline_mae"] == pytest.approx(5.0)
    assert result["baseline_rmse"] == pytest.approx(26.0**0.5)
    assert result["baseline_wape"] == pytest.approx(10 / 30 * 100)
    for field in ("elasticity_mae", "elasticity_rmse", "elasticity_wape"):
        assert pd.isna(result[field])


def test_baseline_and_comparison_coverage_use_different_denominators():
    """Only fully evaluated items contribute to head-to-head results."""
    results = pd.DataFrame({
        "item": ["Latte", "Tea", "Matcha", "Juice"],
        "status": [
            "evaluated", "baseline_only", "baseline_only",
            "insufficient_evidence",
        ],
        "elasticity_lower_mae": [True, None, None, None],
    })
    coverage = summarize_model_coverage(results)

    assert coverage["total_items"] == 4
    assert coverage["evaluated_items"] == 1
    assert coverage["baseline_only_items"] == 2
    assert coverage["baseline_evaluated_items"] == 3
    assert coverage["insufficient_evidence_items"] == 1
    assert coverage["baseline_coverage_pct"] == pytest.approx(75.0)
    assert coverage["evaluation_coverage_pct"] == pytest.approx(25.0)
    assert coverage["elasticity_better_items"] == 1
    assert coverage["elasticity_better_pct"] == pytest.approx(100.0)


def test_report_preserves_baseline_only_in_serializable_items():
    """Report exposes baseline-only values without invented elasticity scores."""
    report = build_model_evaluation_report(
        constant_price_sales(), train_fraction=0.6
    )
    coverage = report["coverage"]
    item = report["items"][0]

    assert coverage["baseline_evaluated_items"] == 1
    assert coverage["evaluated_items"] == 0
    assert coverage["baseline_coverage_pct"] == pytest.approx(100.0)
    assert coverage["evaluation_coverage_pct"] == pytest.approx(0.0)
    assert coverage["elasticity_better_pct"] is None
    assert report["evaluated_items"] == 0
    assert item["status"] == "baseline_only"
    assert item["baseline_mae"] == pytest.approx(5.0)
    assert pd.isna(item["elasticity_mae"])
