"""Regression tests for the model evaluation results table."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections.model_evaluation import prepare_evaluation_table


@pytest.fixture
def sample_results():
    """Create results with and without elasticity evaluation."""
    return pd.DataFrame([
        {
            "item": "Latte",
            "status": "evaluated",
            "reason": "",
            "baseline_mae": 5.0,
            "baseline_rmse": 6.0,
            "baseline_wape": 10.0,
            "elasticity_mae": 4.0,
            "elasticity_rmse": 5.0,
            "elasticity_wape": 8.0,
        },
        {
            "item": "Tea",
            "status": "baseline_only",
            "reason": "Insufficient price variation",
            "baseline_mae": 2.5,
            "baseline_rmse": 3.0,
            "baseline_wape": 12.0,
            "elasticity_mae": None,
            "elasticity_rmse": None,
            "elasticity_wape": None,
        },
        {
            "item": "Matcha",
            "status": "insufficient_evidence",
            "reason": "Insufficient observations",
            "baseline_mae": None,
            "baseline_rmse": None,
            "baseline_wape": None,
            "elasticity_mae": None,
            "elasticity_rmse": None,
            "elasticity_wape": None,
        },
    ])


def test_status_labels_are_readable(sample_results):
    """Internal statuses become readable dashboard labels."""
    display = prepare_evaluation_table(sample_results)

    assert display["Evaluation Status"].tolist() == [
        "Both Models Evaluated",
        "Baseline Only",
        "Insufficient Data",
    ]


def test_baseline_metrics_remain_visible(sample_results):
    """Baseline-only items retain their numeric forecast errors."""
    display = prepare_evaluation_table(sample_results)
    tea = display.loc[display["Menu Item"] == "Tea"].iloc[0]

    assert tea["Baseline MAE"] == pytest.approx(2.5)
    assert tea["Baseline RMSE"] == pytest.approx(3.0)
    assert tea["Baseline WAPE (%)"] == pytest.approx(12.0)


def test_missing_elasticity_metrics_remain_missing(sample_results):
    """Unsupported elasticity results must never become zero."""
    display = prepare_evaluation_table(sample_results)
    tea = display.loc[display["Menu Item"] == "Tea"].iloc[0]

    assert pd.isna(tea["Elasticity MAE"])
    assert pd.isna(tea["Elasticity RMSE"])
    assert pd.isna(tea["Elasticity WAPE (%)"])


def test_original_results_remain_unchanged(sample_results):
    """Display formatting must not modify exported evaluation data."""
    original = sample_results.copy(deep=True)

    prepare_evaluation_table(sample_results)

    pd.testing.assert_frame_equal(sample_results, original)
    assert sample_results.loc[1, "status"] == "baseline_only"
    assert sample_results.loc[1, "baseline_mae"] == 2.5


def test_empty_results_are_supported():
    """Preparing an empty table should not crash."""
    empty = pd.DataFrame(columns=[
        "item",
        "status",
        "baseline_mae",
        "elasticity_mae",
    ])

    result = prepare_evaluation_table(empty)

    assert result.empty
    assert "Evaluation Status" in result.columns
    assert "Baseline MAE" in result.columns
