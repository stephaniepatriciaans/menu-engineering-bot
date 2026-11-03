"""Regression tests for refund disclosures in memo exports."""

import pytest

from reporting.memo_export import build_memo_export


def test_refund_disclosure_in_export():
    """Refund candidates must be disclosed in downloaded memos."""
    memo = "# Menu Pricing Decision Memo\n\nLatte sales revenue: $15."
    original = memo

    export = build_memo_export(
        memo,
        audit=None,
        refund_candidate_count=1,
    )

    assert memo == original
    assert export.count("## POS Transaction Accounting Disclosure") == 1
    assert "1 negative-quantity transaction(s)" in export
    assert "excluded from sales-only analysis" in export
    assert "must not be interpreted as net" in export
    assert "## Financial Audit & Review Status" in export
    assert export.index(
        "POS Transaction Accounting Disclosure"
    ) < export.index("Menu Pricing Decision Memo")

    assert export.count(
        "## POS Transaction Accounting Disclosure"
    ) == 1


def test_no_refund_disclosure_for_regular_sales():
    """Normal datasets must not receive an irrelevant warning."""
    export = build_memo_export(
        "# Menu Pricing Decision Memo",
        audit=None,
        refund_candidate_count=0,
    )

    assert "POS Transaction Accounting Disclosure" not in export


def test_refund_disclosure_with_financial_audit():
    """Refund disclosure and financial audit must coexist."""
    audit = {
        "requires_review": False,
        "findings": [],
    }

    export = build_memo_export(
        "# Menu Pricing Decision Memo",
        audit=audit,
        refund_candidate_count=2,
    )

    assert "2 negative-quantity transaction(s)" in export
    assert export.count("## Financial Audit & Review Status") == 1
    assert export.index("POS Transaction Accounting Disclosure") < (
        export.index("Financial Audit & Review Status")
    )


def test_negative_refund_count_is_rejected():
    """Negative transaction counts are invalid."""
    with pytest.raises(ValueError, match="cannot be negative"):
        build_memo_export(
            "Memo",
            audit=None,
            refund_candidate_count=-1,
        )
