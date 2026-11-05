"""Non-destructive row classification tests for POS uploads."""

import pandas as pd
import pytest

from data_pipeline.pos_quarantine import inspect_pos_rows

MAPPING = {
    "date": "date",
    "item": "item",
    "price": "price",
    "units_sold": "qty",
    "unit_cost": "cost",
}


def source_fixture() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2026-01-01"] * 8,
        "item": ["Tea", None, "Coffee", "Muffin", "Tea", "Coffee", "Tea", "Tea"],
        "price": [5, 3, 0, 5, 5, 5, 5, 5],
        "qty": [2, 1, 1, -2, 1, 1, 1, 1],
        "cost": [1, 1, 1, 1, 1, 1, 1, 1],
        "status": ["completed"] * 6 + ["cancelled", "refunded"],
        "InvoiceNo": ["A1", "A2", "A3", "C4", "A5", "C6", "A7", "A8"],
    })


def test_raw_frame_unchanged_and_review_reasons_retained():
    df = source_fixture()
    saved = df.copy(deep=True)
    result = inspect_pos_rows(df, MAPPING, status_column="status", invoice_column="InvoiceNo")
    pd.testing.assert_frame_equal(df, saved)
    assert result.source_rows == 8
    assert result.invalid_rows == 2
    assert result.refund_candidates == 2
    assert result.cancellation_candidates == 1
    assert set(result.analysis_rows.index) == {0, 4, 5}
    assert result.reason_counts["missing_item"] == 1
    assert result.reason_counts["nonpositive_or_invalid_price"] == 1
    assert "__pos_review_reasons" in result.review_rows
    assert result.review_rows.loc[1, "__pos_source_row"] == 3


def test_uci_invoice_prefix_opt_in_only():
    df = source_fixture()
    without = inspect_pos_rows(df, MAPPING, invoice_column="InvoiceNo")
    enabled = inspect_pos_rows(
        df, MAPPING, invoice_column="InvoiceNo", uci_cancellation_prefix=True,
    )
    assert without.invoice_prefix_candidates == 2
    assert 5 in without.analysis_rows.index
    assert 5 not in enabled.analysis_rows.index
    assert enabled.uci_unverified_exclusions == 1
    assert "uci_c_prefixed_invoice_review" in enabled.review_rows.loc[5, "__pos_review_reasons"]


def test_negative_quantity_is_not_auto_deducted():
    df = source_fixture()
    result = inspect_pos_rows(df, MAPPING)
    assert result.refund_candidates == 1
    assert 3 in result.review_rows.index
    assert df.loc[3, "qty"] == -2
    assert 3 not in result.analysis_rows.index


def test_invalid_dates_prices_quantities_and_costs_are_flagged():
    df = source_fixture().iloc[[0, 4, 5]].copy()
    df.loc[4, "date"] = "not a date"
    df.loc[5, "qty"] = 0
    df.loc[0, "cost"] = -1
    result = inspect_pos_rows(df, MAPPING)
    assert result.invalid_rows == 3
    assert result.analysis_rows.empty
    assert result.reason_counts["invalid_unit_cost"] == 1
    assert result.reason_counts["invalid_date"] == 1
    assert result.reason_counts["invalid_quantity"] == 1


def test_negative_amount_with_positive_quantity_requires_review():
    df = source_fixture().iloc[[0]].copy()
    df["signed_amount"] = [-10]
    result = inspect_pos_rows(df, MAPPING, amount_column="signed_amount")
    assert result.refund_candidates == 1
    assert result.analysis_rows.empty
    assert "negative_amount_refund_candidate" in result.review_rows.iloc[0]["__pos_review_reasons"]


def test_missing_mappings_cannot_be_silently_substituted():
    with pytest.raises(ValueError, match="Required POS mappings missing"):
        inspect_pos_rows(source_fixture(), {"date": "date"})


def test_source_index_must_be_unique():
    df = source_fixture()
    df.index = [0] * len(df)
    with pytest.raises(ValueError, match="index must be unique"):
        inspect_pos_rows(df, MAPPING)


def test_large_generated_export_preserves_reconciliation_counts():
    n = 25_000
    df = pd.DataFrame({
        "date": ["2026-01-01"] * n,
        "item": ["Item"] * n,
        "price": [5] * n,
        "qty": [1] * n,
    })
    df.loc[::31, "qty"] = -1
    df.loc[::43, "item"] = None
    result = inspect_pos_rows(df, {k: v for k, v in MAPPING.items() if k != "unit_cost"})
    assert len(result.analysis_rows) + len(result.review_rows) == n
    assert result.refund_candidates == len(df.loc[::31])
    assert result.reason_counts["missing_item"] == len(df.loc[::43])
    expected_review = (df["qty"] < 0) | df["item"].isna()
    assert len(result.review_rows) == int(expected_review.sum())


def test_identical_valid_sales_are_not_deduplicated():
    data = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01"],
        "item": ["Tea", "Tea"],
        "price": [5.0, 5.0],
        "qty": [1, 1],
    })
    mapping = {k: v for k, v in MAPPING.items() if k != "unit_cost"}
    result = inspect_pos_rows(data, mapping)
    assert len(result.analysis_rows) == 2
    assert result.review_rows.empty


def test_invalid_nonblank_cost_does_not_change_original_values():
    data = source_fixture().iloc[[0]].copy()
    data["cost"] = data["cost"].astype(object)
    data.loc[0, "cost"] = "not a cost"
    original = data.copy(deep=True)
    result = inspect_pos_rows(data, MAPPING)
    assert result.invalid_rows == 1
    assert result.reason_counts["invalid_unit_cost"] == 1
    pd.testing.assert_frame_equal(data, original)
