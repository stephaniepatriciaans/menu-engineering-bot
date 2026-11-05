"""Regression tests for deterministic narrative reconciliation."""

from __future__ import annotations

import pandas as pd

from reporting.memo_consistency import reconcile_memo_consistency


def test_review_count_and_complete_item_list_are_deterministic():
    summary = pd.DataFrame({
        "item": ["POSTAGE", "Manual", "AMAZON FEE", "CARRIAGE", "Latte"],
        "total_revenue": [78.10, 12.0, 3.0, 2.0, 100.0],
        "possible_operational_charge": [True, True, True, True, False],
    })
    memo = (
        "## Key Observations\n\n"
        "Three items require classification review before any pricing action "
        "is taken: POSTAGE and Manual.\n\nNext paragraph."
    )
    fixed = reconcile_memo_consistency(memo, summary, "GBP")
    assert "4 charge-like item labels" in fixed
    assert "AMAZON FEE (£3.00)" in fixed
    assert "CARRIAGE (£2.00)" in fixed
    assert "Latte" not in fixed
    assert "Three items" not in fixed
    assert "Next paragraph." in fixed


def test_other_confidence_is_explained_without_changing_numbers():
    summary = pd.DataFrame({
        "item": ["A", "B", "C", "D", "E"],
        "elasticity_source": ["estimated"] * 4 + ["category_prior"],
        "elasticity_confidence": ["High", "Low", "Medium", None, "Prior"],
    })
    memo = "Estimated items (1 rated high-confidence, 1 low-confidence)."
    fixed = reconcile_memo_consistency(memo, summary, "GBP")
    assert "and 2 with other or missing confidence labels" in fixed


def test_unrecognized_prose_is_preserved_for_human_review():
    summary = pd.DataFrame({"item": ["X"], "possible_operational_charge": [True]})
    memo = "Unknown claim about eighteen items."
    assert reconcile_memo_consistency(memo, summary, "USD") == memo
