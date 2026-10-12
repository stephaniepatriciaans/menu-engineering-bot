"""Tests for safe AI memo exports."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memo_export import build_memo_export


def test_memo_export_includes_financial_warnings():
    """Flagged claims must accompany the exported memo."""

    memo = (
        "# AI Decision Memo\n\n"
        "Increase Latte to $7.00."
    )

    audit = {
        "requires_review": True,
        "finding_count": 1,
        "findings": [
            {
                "claim": "Increase Latte to $7.00",
                "reason": (
                    "Recommended price differs from "
                    "the calculated price of $5.50."
                ),
                "requires_review": True,
            }
        ],
    }

    exported = build_memo_export(memo, audit)

    assert "# AI Decision Memo" in exported
    assert "Increase Latte to $7.00." in exported
    assert "Review required" in exported
    assert "calculated price of $5.50" in exported
    assert "human review" in exported


def test_memo_export_does_not_claim_full_verification():
    """A clean audit must not be presented as a guarantee."""

    memo = "# AI Decision Memo\n\nReview menu performance."

    audit = {
        "requires_review": False,
        "finding_count": 0,
        "findings": [],
    }

    exported = build_memo_export(memo, audit)

    assert "No issues detected by automated checks" in exported
    assert "does not guarantee" in exported
    assert "pattern-based checks" in exported
    assert exported.startswith(memo)

def test_memo_export_preserves_claims_and_review_reasons():
    """Export must preserve multiple audit findings."""

    memo = "# Decision Memo\n\nReview Latte pricing."

    audit = {
        "requires_review": True,
        "finding_count": 2,
        "findings": [
            {
                "claim": "Latte price $7.00",
                "reason": "Expected price is $5.50.",
            },
            {
                "claim": "Latte profit $8.00",
                "reason": "Expected daily change is $0.80.",
            },
        ],
    }

    exported = build_memo_export(memo, audit)

    assert exported.startswith(memo)
    assert "Review required" in exported
    assert "Latte price $7.00" in exported
    assert "Expected price is $5.50." in exported
    assert "Latte profit $8.00" in exported
    assert "Expected daily change is $0.80." in exported