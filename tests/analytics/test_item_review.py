"""Regression tests for review-only labels on unusual POS items."""

import pandas as pd

from analytics.analysis import build_item_summary
from analytics.item_review import (
    possible_operational_charge,
    review_item_reliability,
)


def test_operational_names_are_conservative_exact_matches():
    assert possible_operational_charge("DOTCOM POSTAGE")
    assert possible_operational_charge(" Manual ")
    assert not possible_operational_charge("Postage Stamp Collection")
    assert not possible_operational_charge("Manual Coffee Grinder")


def test_extreme_variation_cannot_be_high_confidence():
    confidence, reason, operational = review_item_reliability(
        "Latte", "estimated", "High", 7145950,
    )
    assert confidence == "Low"
    assert "Extreme historical price range" in reason
    assert not operational


def test_normal_estimates_and_priors_preserved():
    assert review_item_reliability("Latte", "estimated", "High", 50)[0] == "High"
    assert review_item_reliability("POSTAGE", "category_prior", "Prior", 999999)[0] == "Prior"


def test_charge_flag_does_not_remove_revenue():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-01"]),
        "item": ["POSTAGE", "COFFEE"],
        "category": ["Other", "Drink"],
        "price": [10.0, 5.0],
        "units_sold": [2.0, 3.0],
    })
    summary = build_item_summary(df).set_index("item")
    assert summary.loc["POSTAGE", "possible_operational_charge"]
    assert not summary.loc["COFFEE", "possible_operational_charge"]
    assert summary["total_revenue"].sum() == 35.0
