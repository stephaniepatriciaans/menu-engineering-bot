"""Part 7.2: synthetic POS export compatibility and accounting safeguards."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from pos.toast_style_validation import (
    POSFieldMap,
    adapt_pos_export,
    audit_mapped_pos_export,
)

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "examples"
    / "toast_style_sample.csv"
)


@pytest.fixture
def source() -> pd.DataFrame:
    return pd.read_csv(SAMPLE)


@pytest.fixture
def fields() -> POSFieldMap:
    return POSFieldMap(
        date="Business Date",
        item="Menu Item",
        category="Menu Category",
        price="Unit Price",
        quantity="Qty",
        status="Order Status",
        signed_amount="Signed Pre-tax Amount",
        event_id="Event ID",
        line_discount="Line Discount",
        order_id="Order ID",
    )


def confirmed(source: pd.DataFrame, fields: POSFieldMap, **changes: object):
    settings = {
        "price_basis": "listed",
        "refund_convention": "separate_signed_events",
        "source_amount_basis": "pre_tax_sales",
        "expected_net_sales": "14.00",
        "verified_conventions": True,
    }
    settings.update(changes)
    return audit_mapped_pos_export(source, fields, **settings)


def test_fixture_exists_and_preserves_all_four_rows(source, fields):
    adapted = adapt_pos_export(source, fields)
    assert len(adapted) == len(source) == 4
    assert adapted["item"].tolist() == ["Latte", "Croissant", "Latte", "Sandwich"]
    assert adapted["units_sold"].tolist() == [2, 1, -1, 1]
    assert adapted["event_id"].is_unique


def test_default_fails_closed_without_accounting_conventions(source, fields):
    result = audit_mapped_pos_export(source, fields)
    assert result.audit.outcome == "review_required"
    assert result.audit.proposed_net_sales is None


def test_confirmed_fixture_reconciles_exact_cents(source, fields):
    audit = confirmed(source, fields).audit
    assert audit.outcome == "matched"
    assert audit.eligible_rows == 2
    assert audit.refund_candidates == 1
    assert audit.cancelled_rows == 1
    assert audit.eligible_sales == Decimal("24.00")
    assert audit.signed_refund_events == Decimal("-10.00")
    assert audit.proposed_net_sales == Decimal("14.00")


def test_independent_total_mismatch_is_not_matched(source, fields):
    audit = confirmed(source, fields, expected_net_sales="13.99").audit
    assert audit.outcome == "mismatch"
    assert audit.difference == Decimal("0.01")


def test_no_claim_without_independent_summary(source, fields):
    audit = confirmed(source, fields, expected_net_sales=None).audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_no_claim_without_confirmed_export_rules(source, fields):
    audit = confirmed(source, fields, verified_conventions=False).audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_no_claim_with_unknown_refund_convention(source, fields):
    audit = confirmed(source, fields, refund_convention="unknown").audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_no_claim_with_unknown_amount_basis(source, fields):
    audit = confirmed(source, fields, source_amount_basis="unknown").audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_duplicate_event_id_blocks_net_sales(source, fields):
    altered = source.copy()
    altered.loc[2, "Event ID"] = altered.loc[0, "Event ID"]
    audit = confirmed(altered, fields).audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_refunded_status_on_positive_original_is_not_deducted(source, fields):
    altered = source.copy()
    altered.loc[0, "Order Status"] = "refunded"
    audit = confirmed(altered, fields).audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_signed_sale_mismatch_blocks_reconciliation(source, fields):
    altered = source.copy()
    altered.loc[0, "Signed Pre-tax Amount"] = 20.00
    audit = confirmed(altered, fields).audit
    assert audit.outcome == "review_required"
    assert audit.proposed_net_sales is None


def test_overlapping_discounts_are_not_silently_stacked(source, fields):
    altered = source.copy()
    altered["Discount Percent"] = [10, 0, 0, 0]
    both = replace(fields, discount_percent="Discount Percent")
    with pytest.raises(ValueError, match="Overlapping"):
        confirmed(altered, both)


def test_missing_source_column_rejected(source, fields):
    with pytest.raises(ValueError, match="not found"):
        adapt_pos_export(source, replace(fields, quantity="Missing Qty"))


def test_duplicate_mapping_rejected(source, fields):
    with pytest.raises(ValueError, match="reuses"):
        adapt_pos_export(source, replace(fields, quantity="Unit Price"))


def test_empty_export_rejected(fields):
    with pytest.raises(ValueError, match="no transaction rows"):
        adapt_pos_export(pd.DataFrame(columns=["Business Date"]), fields)


def test_source_data_is_not_modified(source, fields):
    before = source.copy(deep=True)
    result = confirmed(source, fields)
    pd.testing.assert_frame_equal(source, before)
    assert "price" not in source.columns
    assert "price" in result.canonical.columns


def test_missing_optional_discount_is_allowed_but_not_inferred(source, fields):
    no_discount = source.drop(columns=["Line Discount"]).copy()
    no_discount.loc[0, "Signed Pre-tax Amount"] = 20.00
    audit = confirmed(
        no_discount,
        replace(fields, line_discount=None),
        expected_net_sales="15.00",
    ).audit
    assert audit.outcome == "matched"


def test_nonfinite_price_rejected(source, fields):
    altered = source.copy()
    altered.loc[0, "Unit Price"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        confirmed(altered, fields)
