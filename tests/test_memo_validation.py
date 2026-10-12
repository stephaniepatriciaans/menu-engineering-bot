"""Tests for detecting unsupported AI memo monetary claims."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memo_validation import (
    audit_generated_memo,
    audit_item_price_claims,
    audit_item_profit_impact_claims,
    audit_item_scenario_claims,
    audit_memo_financial_claims,
    audit_recommended_price_claims,
)


def test_memo_audit_accepts_known_financial_amounts():
    """Amounts present in deterministic outputs should not be flagged."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
        "total_profit": [300.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
        "worst_case_daily_profit_delta": [-0.2],
    })

    memo = (
        "The Latte price is $5.50. "
        "The base scenario adds $0.80 per day. "
        "The pessimistic scenario could lose $0.20 per day."
    )

    findings = audit_memo_financial_claims(
        memo,
        summary,
        moves,
    )

    assert findings == []


def test_memo_audit_flags_unfamiliar_financial_amount():
    """A monetary amount absent from computed data requires review."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
        "total_profit": [300.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
    })

    memo = (
        "Raising Latte prices will increase daily profit "
        "by $8.00."
    )

    findings = audit_memo_financial_claims(
        memo,
        summary,
        moves,
    )

    assert len(findings) == 1
    assert findings[0]["claim"] == "$8.00"
    assert findings[0]["amount"] == 8.0
    assert findings[0]["requires_review"] is True


def test_item_price_audit_accepts_correct_prices():
    """Correct item-price claims should not be flagged."""

    summary = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "price": [5.50, 3.00],
    })

    memo = (
        "Latte costs $5.50. "
        "Tea is priced at $3.00."
    )

    findings = audit_item_price_claims(
        memo,
        summary,
    )

    assert findings == []


def test_item_price_audit_flags_swapped_prices():
    """A valid amount for another item is still incorrect."""

    summary = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "price": [5.50, 3.00],
    })

    memo = (
        "Latte costs $3.00. "
        "Tea is priced at $5.50."
    )

    findings = audit_item_price_claims(
        memo,
        summary,
    )

    assert len(findings) == 2

    by_item = {
        finding["item"]: finding
        for finding in findings
    }

    assert by_item["Latte"]["claimed_price"] == 3.00
    assert by_item["Latte"]["expected_price"] == 5.50

    assert by_item["Tea"]["claimed_price"] == 5.50
    assert by_item["Tea"]["expected_price"] == 3.00


def test_recommended_price_audit_accepts_correct_price():
    """A correct proposed selling price should not be flagged."""

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
    })

    memo = "Increase Latte to $5.50."

    findings = audit_recommended_price_claims(
        memo,
        moves,
    )

    assert findings == []


def test_recommended_price_audit_flags_incorrect_price():
    """A proposed price must match the computed recommendation."""

    moves = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "old_price": [5.0, 3.0],
        "new_price": [5.5, 3.3],
    })

    memo = (
        "Increase Latte to $6.00. "
        "Set Tea price to $3.30."
    )

    findings = audit_recommended_price_claims(
        memo,
        moves,
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding["item"] == "Latte"
    assert finding["claimed_price"] == pytest.approx(6.0)
    assert finding["expected_price"] == pytest.approx(5.5)
    assert finding["requires_review"] is True


def test_profit_impact_audit_accepts_correct_item_claims():
    """Correct item-specific daily changes must not be flagged."""

    moves = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "daily_profit_delta": [0.80, 1.50],
    })

    memo = (
        "Latte adds $0.80 per day. "
        "Tea increases daily contribution profit by $1.50."
    )

    findings = audit_item_profit_impact_claims(
        memo,
        moves,
    )

    assert findings == []


def test_profit_impact_audit_flags_swapped_item_claims():
    """An amount belonging to another item must still be flagged."""

    moves = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "daily_profit_delta": [0.80, 1.50],
    })

    memo = (
        "Latte adds $1.50 per day. "
        "Tea increases daily contribution profit by $0.80."
    )

    findings = audit_item_profit_impact_claims(
        memo,
        moves,
    )

    assert len(findings) == 2

    by_item = {
        finding["item"]: finding
        for finding in findings
    }

    assert by_item["Latte"]["claimed_daily_profit_delta"] == (
        pytest.approx(1.50)
    )
    assert by_item["Latte"]["expected_daily_profit_delta"] == (
        pytest.approx(0.80)
    )

    assert by_item["Tea"]["claimed_daily_profit_delta"] == (
        pytest.approx(0.80)
    )
    assert by_item["Tea"]["expected_daily_profit_delta"] == (
        pytest.approx(1.50)
    )


def test_unified_memo_audit_combines_findings():
    """Different mismatch types must appear in one report."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
        "total_profit": [300.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
    })

    memo = (
        "Latte costs $6.00. "
        "Increase Latte to $7.00. "
        "Latte adds $8.00 per day."
    )

    report = audit_generated_memo(
        memo,
        summary,
        moves,
    )

    assert report["requires_review"] is True

    counts = report["findings_by_type"]

    assert counts["current_price_mismatch"] == 1
    assert counts["recommended_price_mismatch"] == 1
    assert counts["profit_impact_mismatch"] == 1

    assert report["finding_count"] >= 3


def test_unified_memo_audit_accepts_supported_claims():
    """Matching monetary claims should produce no findings."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
        "total_profit": [300.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
    })

    memo = (
        "Latte costs $5.00. "
        "Increase Latte to $5.50. "
        "Latte adds $0.80 per day."
    )

    report = audit_generated_memo(
        memo,
        summary,
        moves,
    )

    assert report["requires_review"] is False
    assert report["finding_count"] == 0
    assert report["findings"] == []


def test_scenario_audit_accepts_correct_item_values():
    """Correct base/worst-case results should not be flagged."""

    moves = pd.DataFrame({
        "item": ["Latte", "Matcha Latte"],
        "base_case_daily_profit_delta": [14.03, 3.90],
        "worst_case_daily_profit_delta": [4.34, -1.44],
    })

    memo = (
        "**Latte** — base-case $14.03 "
        "(worst case $4.34)\n"
        "**Matcha Latte** — base-case gain of $3.90 "
        "(worst case -$1.44)"
    )

    findings = audit_item_scenario_claims(
        memo,
        moves,
    )

    assert findings == []


def test_scenario_audit_flags_swapped_item_values():
    """Amounts from another item must be reported as mismatches."""

    moves = pd.DataFrame({
        "item": ["Latte", "Cold Brew"],
        "base_case_daily_profit_delta": [14.03, 11.88],
        "worst_case_daily_profit_delta": [4.34, 4.02],
    })

    memo = (
        "**Latte** — base-case $11.88 "
        "(worst case $4.02)"
    )

    findings = audit_item_scenario_claims(
        memo,
        moves,
    )

    assert len(findings) == 2

    by_scenario = {
        finding["scenario"]: finding
        for finding in findings
    }

    assert by_scenario["base_case"][
        "expected_daily_profit_delta"
    ] == pytest.approx(14.03)

    assert by_scenario["worst_case"][
        "expected_daily_profit_delta"
    ] == pytest.approx(4.34)

    assert all(
        finding["item"] == "Latte"
        for finding in findings
    )


def test_unified_audit_includes_scenarios_without_duplicate_findings(
    monkeypatch,
):
    """Every audit category must appear exactly once in findings."""
    import memo_validation as memo_module

    financial_finding = {
        "claim": "$999.00",
        "reason": "Unsupported amount",
        "requires_review": True,
    }

    scenario_finding = {
        "item": "Latte",
        "scenario": "worst_case",
        "claim": "worst-case $50.00",
        "reason": "Incorrect scenario result",
        "requires_review": True,
    }

    monkeypatch.setattr(
        memo_module,
        "audit_memo_financial_claims",
        lambda *args: [financial_finding],
    )
    monkeypatch.setattr(
        memo_module,
        "audit_item_scenario_claims",
        lambda *args: [scenario_finding],
    )
    monkeypatch.setattr(
        memo_module,
        "audit_item_price_claims",
        lambda *args: [],
    )
    monkeypatch.setattr(
        memo_module,
        "audit_recommended_price_claims",
        lambda *args: [],
    )
    monkeypatch.setattr(
        memo_module,
        "audit_item_profit_impact_claims",
        lambda *args: [],
    )

    report = memo_module.audit_generated_memo(
        memo="Test memo",
        summary_df=pd.DataFrame(),
        moves_df=pd.DataFrame(),
    )

    assert report["requires_review"] is True
    assert report["finding_count"] == 2
    assert report["findings_by_type"]["unfamiliar_amount"] == 1
    assert report["findings_by_type"]["scenario_mismatch"] == 1
    assert report["findings"] == [
        financial_finding,
        scenario_finding,
    ]


def test_memo_audit_handles_empty_financial_data():
    """Amounts must be flagged when no financial evidence exists."""
    report = audit_generated_memo(
        memo="The expected revenue is $999.00.",
        summary_df=pd.DataFrame(),
        moves_df=pd.DataFrame(),
    )

    assert report["requires_review"] is True
    assert report["findings_by_type"]["unfamiliar_amount"] == 1


def test_item_price_audit_ignores_invalid_source_price():
    """Invalid source prices must not be treated as verified values."""
    summary = pd.DataFrame(
        {
            "item": ["Latte"],
            "price": ["not-a-number"],
        }
    )

    findings = audit_item_price_claims(
        "Latte costs $5.00",
        summary,
    )

    assert findings == []


def test_recommended_price_audit_handles_missing_columns():
    """No recommendation claims can be checked without new_price."""
    moves = pd.DataFrame(
        {
            "item": ["Latte"],
            "old_price": [5.00],
        }
    )

    findings = audit_recommended_price_claims(
        "Increase Latte to $6.00",
        moves,
    )

    assert findings == []
