"""Integration tests for AI memo generation and financial auditing."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import agent


def test_generated_memo_with_audit_accepts_valid_claims(
    monkeypatch,
):
    """Correct AI financial claims produce no audit warnings."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
    })

    def fake_generate_menu_memo(*args, **kwargs):
        return (
            "Latte costs $5.00. "
            "Increase Latte to $5.50. "
            "Latte adds $0.80 per day."
        )

    monkeypatch.setattr(
        agent,
        "generate_menu_memo",
        fake_generate_menu_memo,
    )

    result = agent.generate_menu_memo_with_audit(
        summary_df=summary,
        moves_df=moves,
    )

    assert result["requires_review"] is False
    assert result["audit"]["finding_count"] == 0
    assert result["audit"]["findings"] == []
    assert "Increase Latte to $5.50" in result["memo"]


def test_generated_memo_with_audit_flags_wrong_claims(
    monkeypatch,
):
    """Incorrect AI claims must appear in the audit report."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "total_revenue": [500.0],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "daily_profit_delta": [0.8],
    })

    def fake_generate_menu_memo(*args, **kwargs):
        return (
            "Latte costs $6.00. "
            "Increase Latte to $7.00. "
            "Latte adds $8.00 per day."
        )

    monkeypatch.setattr(
        agent,
        "generate_menu_memo",
        fake_generate_menu_memo,
    )

    result = agent.generate_menu_memo_with_audit(
        summary_df=summary,
        moves_df=moves,
    )

    audit = result["audit"]

    assert result["requires_review"] is True
    assert audit["finding_count"] >= 3

    counts = audit["findings_by_type"]

    assert counts["current_price_mismatch"] == 1
    assert counts["recommended_price_mismatch"] == 1
    assert counts["profit_impact_mismatch"] == 1

    # Audit warnings must not silently alter Claude's memo.
    assert "Increase Latte to $7.00" in result["memo"]
