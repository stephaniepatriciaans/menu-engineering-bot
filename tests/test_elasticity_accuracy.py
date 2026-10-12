"""Numerical accuracy tests for price elasticity estimation."""

import sys
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analysis


def test_estimated_elasticity_recovers_known_slope():
    """A log-log regression should recover known elasticity."""

    # Generate 40 days with varying prices.
    prices = np.linspace(8.0, 12.0, 40)

    # Synthetic demand with true elasticity = -1.5.
    # Q = 100 * (P / 10) ** -1.5
    quantities = 100 * (prices / 10.0) ** -1.5

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=40,
            freq="D",
        ),
        "price": prices,
        "units_sold": quantities,
    })

    result = analysis.estimate_elasticity(
        df,
        category="Coffee",
    )

    elasticity = cast(float, result["elasticity"])

    # The fitted slope should recover the known value.
    assert elasticity == pytest.approx(-1.5, abs=0.01)

    # Adequate evidence should produce a historical estimate.
    assert result["elasticity_source"] == "estimated"
    assert result["elasticity_confidence"] == "High"

    assert result["observations"] == 40
    assert result["price_points"] == 40

    # Price range = (12 - 8) / 8 * 100 = 50%.
    assert result["price_variation_pct"] == pytest.approx(
        50.0
    )


def test_insufficient_price_history_uses_category_prior():
    """Insufficient evidence must not be labeled estimated."""

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-01-02",
        ]),
        "price": [5.0, 5.0],
        "units_sold": [20, 25],
    })

    result = analysis.estimate_elasticity(
        df,
        category="Coffee",
        category_priors={"Coffee": -1.4},
    )

    elasticity = cast(float, result["elasticity"])

    assert elasticity == pytest.approx(-1.4)

    assert result["elasticity_source"] == "category_prior"
    assert result["elasticity_confidence"] == "Prior"

    assert result["price_points"] == 1
    assert result["observations"] == 2
    assert result["price_variation_pct"] == pytest.approx(
        0.0
    )