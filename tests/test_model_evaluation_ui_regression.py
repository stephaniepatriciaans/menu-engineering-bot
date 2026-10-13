"""Streamlit smoke/regression test for the Model Evaluation tab."""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

APP = '''
import pandas as pd
from ui.sections.model_evaluation import render_model_evaluation

df = pd.DataFrame({
    "date": pd.date_range("2026-01-01", periods=10),
    "item": ["Tea"] * 10,
    "price": [3.0] * 10,
    "units_sold": [10.0, 12.0, 9.0, 11.0, 10.0,
                   14.0, 13.0, 15.0, 11.0, 16.0],
})
render_model_evaluation(df)
'''


def test_dashboard_shows_baseline_only_results_without_elasticity():
    """The UI must not hide baseline metrics when comparisons are zero."""
    at = AppTest.from_string(APP, default_timeout=20).run()
    assert not at.exception

    at.button(key="run_model_evaluation").click().run()
    assert not at.exception

    metrics = {widget.label: widget.value for widget in at.metric}
    assert str(metrics["Baseline Evaluated"]) == "1"
    assert str(metrics["Two-Model Comparisons"]) == "0"
    assert str(metrics["Baseline Only"]) == "1"
    assert metrics["Baseline Coverage"] == "100.0%"
    assert metrics["Comparison Coverage"] == "0.0%"
    assert "Mean Baseline MAE" in metrics
    assert "Mean Baseline RMSE" in metrics
    assert "Mean Baseline WAPE" in metrics

