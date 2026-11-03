"""Regression checks for source-only financial review indicators."""

import numpy as np
import pandas as pd

from core.financial_review import summarize_financial_review


def test_financial_review_preserves_source_and_counts_signals():
    rng = np.random.default_rng(71)
    n = 60
    quantities = rng.integers(1, 7, n)
    quantities[::8] *= -1
    amounts = (quantities * rng.uniform(2, 10, n)).round(2)
    status = np.full(n, "completed", dtype=object)
    status[1::9] = "cancelled"
    status[2::9] = "refunded"
    df = pd.DataFrame({"units": quantities, "amount": amounts, "status": status})
    before = df.copy(deep=True)
    review = summarize_financial_review(
        df,
        {"units_sold": "units"},
        status_column="status",
        amount_column="amount",
        discount_percent_column="pct",
    )
    assert review.refund_candidates == int(((quantities < 0) | (status == "refunded")).sum())
    assert review.cancelled == int((status == "cancelled").sum())
    assert review.discount_fields_mapped == 1
    assert review.price_basis == "unknown"
    assert review.needs_review == review.refund_candidates + review.cancelled
    pd.testing.assert_frame_equal(df, before)


def test_missing_classification_mapping_is_not_treated_as_zero():
    df = pd.DataFrame({"quantity": [1, 2]})
    review = summarize_financial_review(df, {}, price_basis="listed")
    assert review.refund_candidates is None
    assert review.classification_note


def test_negative_quantity_detection_works_without_status():
    df = pd.DataFrame({"quantity": [3, -1, 2]})
    review = summarize_financial_review(df, {"units_sold": "quantity"})
    assert review.refund_candidates == 1
    assert review.cancelled == 0
    assert review.needs_review == 1
