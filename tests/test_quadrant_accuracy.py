"""Numerical tests for menu quadrant classification."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analysis


@pytest.fixture
def mock_elasticity(monkeypatch):
    """Keep elasticity separate from quadrant testing."""
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


def test_all_four_quadrants(mock_elasticity):
    """Each of the four quadrant types is classified correctly."""

    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"] * 4),
        "item": ["Star Item", "Puzzle Item", "Plowhorse Item", "Dog Item"],
        "category": ["Food"] * 4,
        "price": [10.0] * 4,
        "unit_cost": [2.0, 2.0, 8.0, 8.0],
        "units_sold": [100, 10, 100, 10],
    })

    summary = analysis.build_item_summary(df).set_index("item")

    expected = {
        "Star Item": "Star",
        "Puzzle Item": "Puzzle",
        "Plowhorse Item": "Plowhorse",
        "Dog Item": "Dog",
    }

    for item, quadrant in expected.items():
        assert summary.loc[item, "quadrant"] == quadrant

    assert summary["quadrant"].value_counts().to_dict() == {
        "Star": 1,
        "Puzzle": 1,
        "Plowhorse": 1,
        "Dog": 1,
    }


def test_median_boundary_is_classified_as_high(mock_elasticity):
    """Values exactly at both medians use the high/high quadrant."""

    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"] * 3),
        "item": ["Low", "Boundary", "High"],
        "category": ["Food"] * 3,
        "price": [10.0] * 3,
        "unit_cost": [8.0, 5.0, 2.0],
        "units_sold": [10, 20, 30],
    })

    summary = analysis.build_item_summary(df).set_index("item")

    # Median popularity is 20 units per day.
    # Median contribution margin is 50%.
    assert float(summary["avg_daily_units"].median()) == pytest.approx(20.0)
    assert float(summary["contribution_margin_%"].median()) == pytest.approx(50.0)

    # Boundary qualifies as high margin and high popularity.
    assert summary.loc["Boundary", "quadrant"] == "Star"
    assert summary.loc["Low", "quadrant"] == "Dog"
    assert summary.loc["High", "quadrant"] == "Star"
