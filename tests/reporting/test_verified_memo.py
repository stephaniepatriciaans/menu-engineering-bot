"""Regression tests for deterministic reports independent of AI prose."""

import pandas as pd
import pytest

from reporting.verified_memo import build_verified_memo


def _summary():
    return pd.DataFrame({
        "item": ["POSTAGE", "Manual", "PARTY BUNTING", "PAPER CRAFT"],
        "total_revenue": [200.0, 30.0, 100.0, 50.0],
        "possible_operational_charge": [True, True, False, False],
        "reliability_review_reason": ["Charge-like", "Charge-like", "", ""],
        "elasticity_source": ["estimated", "estimated", "estimated", "category_prior"],
        "elasticity_confidence": ["Low", "Low", "High", "Prior"],
        "elasticity": [0.0, -0.25, -1.82, -1.0],
        "price_points": [20, 13, 14, 1],
        "observations": [500, 130, 565, 1],
        "price_variation_%": [600, 700, 321, 0],
    })


def test_verified_report_counts_and_units():
    result = build_verified_memo(_summary(), "GBP", cost_basis="unavailable")
    assert "**Items in analysis:** 4." in result
    assert "**Charge-like item labels flagged:** 2." in result
    assert "POSTAGE" in result and "Manual" in result
    assert "**High / Low / Other estimated-confidence labels:** 1 / 2 / 0." in result
    assert "**Items without item-level historical estimates:** 1." in result
    assert "Price points" in result
    assert "Obs." in result
    assert "-1.82" in result
    assert "£380.00" in result
    assert "unit costs are unavailable" in result


def test_verified_report_refuses_to_infer_observations_from_price_points():
    summary = _summary().drop(columns=["observations"])
    result = build_verified_memo(summary, "GBP")
    assert "Price points" in result
    assert "| Obs. |" not in result
    assert "count distinct prices" in result


def test_verified_report_nonstandard_dataset_and_missing_fields():
    source = pd.DataFrame({"item": ["Latte", "Tea"], "total_revenue": [15, 20]})
    before = source.copy(deep=True)
    result = build_verified_memo(source, "USD")
    assert "Operational-charge review flags are not available" in result
    assert "Item-level elasticity evidence labels are unavailable" in result
    pd.testing.assert_frame_equal(source, before)


def test_verified_report_escapes_tables_and_limits_rows():
    summary = _summary()
    summary.loc[2, "item"] = "PARTY | BUNTING"
    result = build_verified_memo(summary, "GBP", max_items=1)
    assert r"PARTY \| BUNTING" in result
    assert result.count("PARTY ") == 1
    with pytest.raises(ValueError, match="max_items"):
        build_verified_memo(summary, "GBP", max_items=0)


def test_verified_report_does_not_invent_financial_summary_with_missing_revenue():
    summary = pd.DataFrame({"item": ["Tea"], "total_revenue": [None]})
    result = build_verified_memo(summary, "USD")
    assert "Sum of item-level gross sales revenue" not in result
