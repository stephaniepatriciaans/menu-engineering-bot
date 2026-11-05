"""Generated-data checks for conservative, cent-accurate POS reconciliation."""

import numpy as np
import pandas as pd
import pytest

from pos.reconciliation import reconcile_pos_sales, summarize_reconciled_sales


def make_orders(seed=17, orders=24, lines=4):
    rng = np.random.default_rng(seed)
    count = orders * lines
    return pd.DataFrame({
        "price": rng.integers(200, 3000, count) / 100,
        "units_sold": rng.integers(1, 5, count),
        "order": np.repeat(np.arange(orders), lines),
    })


def test_per_unit_discount_is_multiplied_by_quantity_and_preserves_data():
    df = make_orders()
    df["per_unit"] = 0.35
    before = df.copy(deep=True)
    reconciled = reconcile_pos_sales(
        df, price_basis="listed", per_unit_discount_column="per_unit",
        verified_conventions=True,
    )
    expected = df["price"] * df["units_sold"] - 0.35 * df["units_sold"]
    np.testing.assert_allclose(reconciled["eligible_sales_amount"], expected)
    assert summarize_reconciled_sales(reconciled)["conventions_verified"]
    pd.testing.assert_frame_equal(df, before)


def test_repeated_order_discount_total_allocated_only_once_per_order():
    df = make_orders()
    df["order_discount"] = 1.01
    result = reconcile_pos_sales(
        df, price_basis="listed", order_id_column="order",
        order_discount_column="order_discount",
    )
    per_order = result.groupby("order")["order_discount_allocated"].sum()
    np.testing.assert_allclose(per_order, 1.01)
    assert round(result["eligible_sales_amount"].sum(), 2) == round(
        (df["price"] * df["units_sold"]).sum() - df["order"].nunique() * 1.01, 2
    )


def test_one_order_discount_on_single_line_is_allocated():
    df = make_orders(orders=3, lines=3)
    df["coupon"] = 0.0
    df.loc[df.groupby("order").head(1).index, "coupon"] = 1.03
    result = reconcile_pos_sales(
        df, price_basis="listed", order_id_column="order",
        order_discount_column="coupon",
    )
    np.testing.assert_allclose(result.groupby("order")["order_discount_allocated"].sum(), 1.03)


def test_stacking_needs_explicit_rule_and_sequential_is_calculated():
    df = pd.DataFrame({
        "price": [10.0], "units_sold": [2], "percentage": [10],
        "line": [1.0], "per_unit": [0.5],
    })
    args = {
        "price_basis": "listed", "percent_column": "percentage",
        "line_discount_column": "line", "per_unit_discount_column": "per_unit",
    }
    with pytest.raises(ValueError, match="overlap|Overlapping"):
        reconcile_pos_sales(df, **args)
    got = reconcile_pos_sales(df, stacking="sequential", **args)
    assert got.at[0, "eligible_sales_amount"] == 16.0


def test_refund_candidates_are_not_deducted_or_classed_as_confirmed_refunds():
    df = pd.DataFrame({
        "price": [10.0, 10.0, 10.0, 10.0],
        "units_sold": [2, 2, -1, 2],
        "status": ["completed", "refunded", "returned", "cancelled"],
        "signed": [20.0, 20.0, -10.0, 20.0],
    })
    result = reconcile_pos_sales(
        df, price_basis="listed", status_column="status", amount_column="signed",
        verified_conventions=True,
    )
    summary = summarize_reconciled_sales(result)
    assert summary["eligible_sales_revenue"] == 20.0
    assert summary["refund_candidates"] == 2
    assert summary["cancelled_rows"] == 1
    assert summary["net_revenue_verified"] is False
    assert result.loc[[1, 2, 3], "eligible_sales_amount"].isna().all()


def test_unknown_price_basis_cannot_claim_realized_sales():
    result = reconcile_pos_sales(make_orders(), price_basis="unknown", verified_conventions=True)
    assert result["eligible_sales_amount"].isna().all()
    assert summarize_reconciled_sales(result)["eligible_sales_revenue"] is None


def test_realized_basis_does_not_double_subtract_discounts():
    df = make_orders()
    df["per_unit"] = 0.5
    result = reconcile_pos_sales(df, price_basis="realized", per_unit_discount_column="per_unit")
    np.testing.assert_allclose(result["eligible_sales_amount"], df["price"] * df["units_sold"])


def test_conflicting_order_discount_values_fail_closed():
    df = make_orders(orders=1, lines=3)
    df["coupon"] = [1.0, 2.0, 0]
    with pytest.raises(ValueError, match="Conflicting"):
        reconcile_pos_sales(df, price_basis="listed", order_id_column="order", order_discount_column="coupon")


def test_excessive_order_discount_fails_closed():
    df = make_orders(orders=1, lines=2)
    df["coupon"] = 9999.99
    with pytest.raises(ValueError, match="cannot exceed"):
        reconcile_pos_sales(df, price_basis="listed", order_id_column="order", order_discount_column="coupon")


def test_missing_order_id_fails_closed():
    df = make_orders(orders=1, lines=2)
    df.loc[0, "order"] = np.nan
    df["coupon"] = 0.1
    with pytest.raises(ValueError, match="nonmissing order IDs"):
        reconcile_pos_sales(df, price_basis="listed", order_id_column="order", order_discount_column="coupon")


def test_no_duplicate_source_names_or_duplicate_row_indices():
    df = make_orders(orders=1, lines=2)
    df.index = [0, 0]
    with pytest.raises(ValueError, match="Duplicate row indices"):
        reconcile_pos_sales(df)


def test_overlapping_mapping_is_rejected():
    with pytest.raises(ValueError, match="distinct"):
        reconcile_pos_sales(make_orders(), price_basis="listed", per_unit_discount_column="price")


def test_negative_and_invalid_discounts_rejected():
    df = make_orders(orders=1, lines=2)
    df["pct"] = [-1, 50]
    with pytest.raises(ValueError, match="Discounts must"):
        reconcile_pos_sales(df, price_basis="listed", percent_column="pct")


def test_zero_value_order_cannot_have_coupon():
    df = pd.DataFrame({"price": [1.0], "units_sold": [1], "order": ["a"], "disc": [1.0], "coupon": [0.01]})
    with pytest.raises(ValueError, match="zero-value"):
        reconcile_pos_sales(df, price_basis="listed", line_discount_column="disc", order_id_column="order", order_discount_column="coupon")


def test_order_percentage_discount_allocated_exactly():
    df = make_orders(orders=6, lines=3)
    df["pct"] = 17.0
    result = reconcile_pos_sales(
        df, price_basis="listed", order_id_column="order",
        order_percent_column="pct",
    )
    gross = (df["price"] * df["units_sold"]).groupby(df["order"]).sum()
    expected = gross.map(lambda amount: round(float(amount) * 0.17 + 0.000001, 2))
    actual = result.groupby("order")["order_discount_allocated"].sum()
    np.testing.assert_allclose(actual, expected, atol=0.01)


def test_overlapping_order_percentage_and_coupon_must_be_explicit():
    df = make_orders(orders=1, lines=2)
    df["pct"] = 10.0
    df["coupon"] = 1.0
    options = {
        "price_basis": "listed", "order_id_column": "order",
        "order_percent_column": "pct", "order_discount_column": "coupon",
    }
    with pytest.raises(ValueError, match="Overlapping order"):
        reconcile_pos_sales(df, **options)
    result = reconcile_pos_sales(df, stacking="sequential", **options)
    assert round(result["order_discount_allocated"].sum(), 2) > 1


def test_refund_evidence_is_explainable_and_status_only_is_not_a_deduction():
    df = pd.DataFrame({
        "price": [5, 5, 5], "units_sold": [2, -1, 2],
        "status": ["refunded", "completed", "cancelled"],
    })
    result = reconcile_pos_sales(df, status_column="status", price_basis="listed")
    assert result["accounting_evidence"].tolist() == [
        "refund_status", "negative_quantity", "cancelled_status",
    ]
    assert result["eligible_sales_amount"].isna().all()
