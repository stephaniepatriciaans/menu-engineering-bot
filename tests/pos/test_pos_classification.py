"""Regression tests for universal POS transaction classification."""

import numpy as np
import pandas as pd
import pytest

from pos.classification import classify_pos_transactions


@pytest.fixture
def pos_data():
    """Generate reproducible POS transactions."""
    rng = np.random.default_rng(42)
    n = 100

    quantities = rng.integers(1, 20, size=n)
    amounts = rng.uniform(1.0, 100.0, size=n).round(2)

    return pd.DataFrame({
        "units_sold": quantities,
        "line_total": amounts,
        "status": ["completed"] * n,
    })


def test_positive_transactions_are_sales(pos_data):
    """Positive transactions should remain classified as sales."""
    result = classify_pos_transactions(
        pos_data,
        amount_column="line_total",
        status_column="status",
    )

    assert (result["transaction_class"] == "sale").all()


def test_negative_quantities_are_refund_candidates(pos_data):
    """Negative quantities indicate potential refund transactions."""
    df = pos_data.copy()
    df.loc[df.index[::5], "units_sold"] *= -1

    result = classify_pos_transactions(df)

    expected = df["units_sold"] < 0

    pd.testing.assert_series_equal(
        result["transaction_class"].eq("refund_candidate"),
        expected.rename("transaction_class"),
    )


def test_negative_amounts_are_refund_candidates(pos_data):
    """Negative line amounts indicate potential refund transactions."""
    df = pos_data.copy()
    df.loc[df.index[::4], "line_total"] *= -1

    result = classify_pos_transactions(
        df,
        amount_column="line_total",
    )

    expected = df["line_total"] < 0

    pd.testing.assert_series_equal(
        result["transaction_class"].eq("refund_candidate"),
        expected.rename("transaction_class"),
    )


@pytest.mark.parametrize(
    "refund_status",
    [
        "refunded",
        "refund",
        "returned",
        "return",
        "partial_refund",
        "Partial Refund",
        " REFUNDED ",
    ],
)
def test_refund_statuses_are_detected(refund_status):
    """Common POS refund statuses should be recognized."""
    df = pd.DataFrame({
        "units_sold": [1],
        "status": [refund_status],
    })

    result = classify_pos_transactions(
        df,
        status_column="status",
    )

    assert result.loc[0, "transaction_class"] == "refund_candidate"


@pytest.mark.parametrize(
    "cancel_status",
    ["cancelled", "canceled", "void", "voided", " VOIDED "],
)
def test_cancelled_statuses_are_detected(cancel_status):
    """Cancelled records should not be counted as completed sales."""
    df = pd.DataFrame({
        "units_sold": [1],
        "status": [cancel_status],
    })

    result = classify_pos_transactions(
        df,
        status_column="status",
    )

    assert result.loc[0, "transaction_class"] == "cancelled"


def test_refund_candidate_takes_precedence_over_cancellation():
    """Conflicting signals use the documented precedence rule."""
    df = pd.DataFrame({
        "units_sold": [-1],
        "status": ["cancelled"],
    })

    result = classify_pos_transactions(
        df,
        status_column="status",
    )

    assert result.loc[0, "transaction_class"] == "refund_candidate"


def test_original_dataframe_is_not_modified(pos_data):
    """Classification must not mutate uploaded source data."""
    original = pos_data.copy(deep=True)

    classify_pos_transactions(
        pos_data,
        amount_column="line_total",
        status_column="status",
    )

    pd.testing.assert_frame_equal(pos_data, original)


@pytest.mark.parametrize(
    "invalid_quantity",
    [None, float("nan"), float("inf"), "invalid"],
)
def test_invalid_quantities_are_rejected(invalid_quantity):
    """Invalid transaction quantities must not be silently accepted."""
    df = pd.DataFrame({
        "units_sold": [invalid_quantity],
    })

    with pytest.raises(ValueError, match="finite numeric values"):
        classify_pos_transactions(df)


def test_missing_optional_column_is_rejected(pos_data):
    """Requested classification columns must exist."""
    with pytest.raises(
        ValueError,
        match="Missing POS classification column",
    ):
        classify_pos_transactions(
            pos_data,
            status_column="missing_status",
        )


def test_custom_column_names_are_supported(pos_data):
    """POS exports can use different quantity and amount headers."""
    renamed = pos_data.rename(
        columns={
            "units_sold": "quantity",
            "line_total": "transaction_amount",
            "status": "order_state",
        }
    )

    result = classify_pos_transactions(
        renamed,
        quantity_column="quantity",
        amount_column="transaction_amount",
        status_column="order_state",
    )

    assert (result["transaction_class"] == "sale").all()

def test_non_sale_transactions_require_accounting_review(pos_data):
    """Refund candidates and cancellations require review."""
    df = pos_data.copy()

    df.loc[df.index[::5], "units_sold"] *= -1
    df.loc[df.index[1::5], "status"] = "cancelled"
    df.loc[df.index[2::5], "status"] = "refunded"

    result = classify_pos_transactions(
        df,
        amount_column="line_total",
        status_column="status",
    )

    expected = result["transaction_class"] != "sale"

    pd.testing.assert_series_equal(
        result["requires_accounting_review"],
        expected.rename("requires_accounting_review"),
    )


def test_completed_sales_do_not_require_accounting_review(pos_data):
    """Ordinary sales should not be flagged for accounting review."""
    result = classify_pos_transactions(
        pos_data,
        amount_column="line_total",
        status_column="status",
    )

    assert not result["requires_accounting_review"].any()


def test_missing_status_does_not_imply_refund_or_cancellation():
    """A missing status alone must not imply a refund."""
    df = pd.DataFrame({
        "units_sold": [1, 2, 3],
        "status": [None, "", "completed"],
    })

    result = classify_pos_transactions(
        df,
        status_column="status",
    )

    assert (result["transaction_class"] == "sale").all()
    assert not result["requires_accounting_review"].any()


def test_cancelled_transaction_with_negative_quantity_is_conflict():
    """Cancelled records with refund signals must be flagged."""
    df = pd.DataFrame({
        "units_sold": [-1],
        "line_total": [-5.0],
        "status": ["cancelled"],
    })

    result = classify_pos_transactions(
        df,
        amount_column="line_total",
        status_column="status",
    )

    assert result.loc[0, "has_classification_conflict"]
    assert result.loc[0, "requires_accounting_review"]


def test_positive_quantity_with_negative_amount_is_conflict():
    """Mixed amount and quantity signs require review."""
    df = pd.DataFrame({
        "units_sold": [2],
        "line_total": [-10.0],
        "status": ["completed"],
    })

    result = classify_pos_transactions(
        df,
        amount_column="line_total",
        status_column="status",
    )

    assert result.loc[0, "has_classification_conflict"]
    assert result.loc[0, "transaction_class"] == "refund_candidate"


def test_negative_quantity_with_positive_amount_is_conflict():
    """Opposing quantity and amount signs require review."""
    df = pd.DataFrame({
        "units_sold": [-2],
        "line_total": [10.0],
    })

    result = classify_pos_transactions(
        df,
        amount_column="line_total",
    )

    assert result.loc[0, "has_classification_conflict"]
    assert result.loc[0, "requires_accounting_review"]


def test_consistent_sales_have_no_classification_conflict(pos_data):
    """Ordinary positive transactions must not be flagged."""
    result = classify_pos_transactions(
        pos_data,
        amount_column="line_total",
        status_column="status",
    )

    assert not result["has_classification_conflict"].any()


def test_conflict_detection_does_not_mutate_source(pos_data):
    """Classification must preserve original POS records."""
    df = pos_data.copy(deep=True)
    df.loc[df.index[::5], "line_total"] *= -1

    original = df.copy(deep=True)

    classify_pos_transactions(
        df,
        amount_column="line_total",
        status_column="status",
    )

    pd.testing.assert_frame_equal(df, original)


def test_duplicate_pos_column_names_are_rejected(pos_data):
    """Duplicate source headers must not create ambiguous mappings."""
    df = pos_data.copy()

    df.columns = [
        "units_sold",
        "units_sold",
        "status",
    ]

    with pytest.raises(
        ValueError,
        match="Duplicate POS column names",
    ):
        classify_pos_transactions(df)


def test_reused_classification_columns_are_rejected(pos_data):
    """A source column cannot serve as multiple financial fields."""
    with pytest.raises(
        ValueError,
        match="must be distinct",
    ):
        classify_pos_transactions(
            pos_data,
            quantity_column="units_sold",
            amount_column="units_sold",
        )


def test_valid_custom_pos_columns_are_accepted(pos_data):
    """Distinct POS field names remain universally supported."""
    renamed = pos_data.rename(
        columns={
            "units_sold": "sold_quantity",
            "line_total": "paid_amount",
            "status": "transaction_state",
        }
    )

    result = classify_pos_transactions(
        renamed,
        quantity_column="sold_quantity",
        amount_column="paid_amount",
        status_column="transaction_state",
    )

    assert (result["transaction_class"] == "sale").all()
    assert not result["has_classification_conflict"].any()
