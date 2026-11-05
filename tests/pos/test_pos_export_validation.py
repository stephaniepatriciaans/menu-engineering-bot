"""Accounting contract tests: no auto-refund deductions for ambiguous POS exports."""

from decimal import Decimal

import pandas as pd
import pytest

from pos.export_validation import audit_pos_export


def make_export() -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["s1", "s2", "r1", "c1"],
        "price": [10, 5, 10, 20],
        "units_sold": [2, 1, -1, 1],
        "status": ["completed", "completed", "refunded", "cancelled"],
        "signed_amount": [20, 5, -10, 20],
    })


def audit(df: pd.DataFrame, **kwargs: object):
    defaults = {
        "price_basis": "listed",
        "amount_column": "signed_amount",
        "status_column": "status",
        "event_id_column": "event_id",
        "refund_convention": "separate_signed_events",
        "source_amount_basis": "pre_tax_sales",
        "expected_net_sales": "15.00",
        "verified_conventions": True,
    }
    defaults.update(kwargs)
    return audit_pos_export(df, **defaults)


def test_matched_signed_refund_and_cancelled_exclusion():
    result = audit(make_export())
    assert result.outcome == "matched"
    assert result.eligible_sales == Decimal("25.00")
    assert result.signed_refund_events == Decimal("-10.00")
    assert result.proposed_net_sales == Decimal("15.00")
    assert result.cancelled_rows == 1


def test_partial_signed_refund():
    df = make_export()
    df.loc[2, "signed_amount"] = -3.00
    df.loc[2, "price"] = 3.00
    result = audit(df, expected_net_sales="22.00")
    assert result.outcome == "matched"
    assert result.signed_refund_events == Decimal("-3.00")


def test_status_only_original_is_not_deducted():
    df = make_export().iloc[[0, 1]].copy()
    df.loc[df.index[0], "status"] = "refunded"
    result = audit(df)
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None
    assert any("positive" in finding for finding in result.findings)


def test_unknown_convention_never_claims_net_sales():
    result = audit(make_export(), refund_convention="unknown")
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None


def test_unknown_amount_basis_blocks_net():
    result = audit(make_export(), source_amount_basis="unknown")
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None


def test_duplicate_event_id_blocks_double_deduction():
    df = make_export()
    df.loc[2, "event_id"] = "s1"
    result = audit(df)
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None


def test_summary_mismatch_is_reported():
    result = audit(make_export(), expected_net_sales="14.99")
    assert result.outcome == "mismatch"
    assert result.difference == Decimal("0.01")


def test_unconfirmed_rules_never_get_matched_status():
    result = audit(make_export(), verified_conventions=False)
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None


def test_missing_expected_summary_never_gets_matched_status():
    result = audit(make_export(), expected_net_sales=None)
    assert result.outcome == "review_required"


def test_unknown_price_basis_never_gets_matched_status():
    result = audit(make_export(), price_basis="unknown")
    assert result.outcome == "review_required"


def test_input_is_not_mutated():
    df = make_export()
    original = df.copy(deep=True)
    audit(df)
    pd.testing.assert_frame_equal(df, original)


def test_overlapping_discount_not_silently_stacked():
    df = make_export()
    df["line_discount"] = [1, 0, 0, 0]
    df["percent"] = [10, 0, 0, 0]
    with pytest.raises(ValueError, match="Overlapping"):
        audit(df, line_discount_column="line_discount", percent_column="percent")


def test_order_coupon_exact_cents_and_matching_summary():
    df = pd.DataFrame({
        "event_id": ["a", "b", "c"],
        "price": [1.00, 1.00, 1.00],
        "units_sold": [1, 1, 1],
        "status": ["completed"] * 3,
        "signed_amount": [0.99, 1.00, 1.00],
        "order_id": ["o1"] * 3,
        "coupon": [0.01] * 3,
    })
    result = audit(
        df,
        expected_net_sales="2.99",
        order_id_column="order_id",
        order_discount_column="coupon",
    )
    assert result.outcome == "matched"
    assert result.eligible_sales == Decimal("2.99")


def test_malformed_expected_amount_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        audit(make_export(), expected_net_sales="NaN")


def test_positive_sale_amount_mismatch_blocks_verification():
    df = make_export()
    df.loc[0, "signed_amount"] = 99
    result = audit(df)
    assert result.outcome == "review_required"
    assert result.proposed_net_sales is None
    assert any("signed sale amounts" in item for item in result.findings)


def test_amount_and_coupon_mismatch_blocks_verification():
    df = pd.DataFrame({
        "event_id": ["a", "b"], "price": [5.00, 5.00],
        "units_sold": [1, 1], "status": ["completed", "completed"],
        "signed_amount": [5.00, 5.00], "order_id": ["o1", "o1"],
        "coupon": [1.00, 1.00],
    })
    result = audit(df, expected_net_sales="9.00", order_id_column="order_id", order_discount_column="coupon")
    assert result.outcome == "review_required"


def test_missing_signed_amount_column_holds_net():
    result = audit(make_export(), amount_column=None)
    assert result.outcome == "review_required"


def test_only_unique_events_eligible():
    df = make_export()
    df.loc[1, "event_id"] = None
    result = audit(df)
    assert result.outcome == "review_required"
