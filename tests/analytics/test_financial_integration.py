"""Financial analytics cannot silently transform an unverified POS export."""

from decimal import Decimal

import pandas as pd
import pytest

from analytics.financial_integration import (
    build_audited_financials,
    financial_report_text,
)
from pos.export_validation import audit_pos_export
from pos.reconciliation import reconcile_pos_sales


def export() -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["s1", "s2", "r1", "c1"],
        "price": [10.00, 5.00, 10.00, 20.00],
        "units_sold": [2, 1, -1, 1],
        "status": ["completed", "completed", "refunded", "cancelled"],
        "signed_amount": [20.00, 5.00, -10.00, 20.00],
    })


def filtered_canonical() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-02"]),
        "item": ["Latte", "Tea", "Cancelled Item"],
        "units_sold": [2, 1, 1],
        "unit_cost": [2.00, 1.00, 1.00],
    }, index=[0, 1, 3])


def matched_inputs():
    source = export()
    audit = audit_pos_export(
        source,
        price_basis="listed",
        status_column="status",
        amount_column="signed_amount",
        event_id_column="event_id",
        refund_convention="separate_signed_events",
        source_amount_basis="pre_tax_sales",
        expected_net_sales="15.00",
        verified_conventions=True,
    )
    rows = reconcile_pos_sales(
        source,
        price_basis="listed",
        status_column="status",
        amount_column="signed_amount",
        verified_conventions=True,
    )
    return audit, rows


def test_audited_totals_and_item_contribution():
    audit, rows = matched_inputs()
    output = build_audited_financials(filtered_canonical(), rows, audit)
    assert audit.outcome == "matched"
    assert output.full_export_net_sales == Decimal("15.00")
    assert output.eligible_sales == Decimal("25.00")
    assert output.eligible_units == 3
    assert output.eligible_rows == 2
    assert output.contribution_profit == Decimal("20.00")
    assert output.by_item.set_index("item").loc["Latte", "revenue"] == Decimal("20.00")
    assert output.has_refund_events


def test_filters_limit_eligible_not_full_export_net():
    audit, rows = matched_inputs()
    subset = filtered_canonical().loc[[1, 3]]
    result = build_audited_financials(subset, rows, audit)
    assert result.eligible_sales == Decimal("5.00")
    assert result.full_export_net_sales == Decimal("15.00")
    assert result.eligible_rows == 1


def test_refund_rows_never_attributed_to_items():
    audit, rows = matched_inputs()
    result = build_audited_financials(filtered_canonical(), rows, audit)
    assert result.by_item["item"].tolist() == ["Latte", "Tea"]
    assert sum(result.by_item["revenue"], Decimal("0.00")) == Decimal("25.00")
    assert result.full_export_net_sales != result.eligible_sales


def test_rejected_without_matched_audit():
    audit, rows = matched_inputs()
    broken = audit_pos_export(
        export(), price_basis="listed", status_column="status",
        amount_column="signed_amount", event_id_column="event_id",
        refund_convention="separate_signed_events", source_amount_basis="pre_tax_sales",
        expected_net_sales="14.00", verified_conventions=True,
    )
    assert broken.outcome == "mismatch"
    with pytest.raises(ValueError, match="matched"):
        build_audited_financials(filtered_canonical(), rows, broken)
    assert audit.outcome == "matched"


def test_review_only_sale_rows_are_rejected():
    audit, rows = matched_inputs()
    rows.loc[0, "accounting_status"] = "review_required"
    with pytest.raises(ValueError, match="Unverified"):
        build_audited_financials(filtered_canonical(), rows, audit)


def test_unrelated_rows_are_rejected():
    audit, rows = matched_inputs()
    other = filtered_canonical().rename(index={0: 100})
    with pytest.raises(ValueError, match="audited POS export"):
        build_audited_financials(other, rows, audit)


def test_missing_cost_yields_no_profit_claim():
    audit, rows = matched_inputs()
    work = filtered_canonical()
    work.loc[0, "unit_cost"] = float("nan")
    result = build_audited_financials(work, rows, audit)
    assert result.contribution_profit is None
    assert pd.isna(result.by_item.set_index("item").loc["Latte", "contribution_profit"])


def test_canonical_source_not_modified():
    audit, rows = matched_inputs()
    canonical = filtered_canonical()
    original = canonical.copy(deep=True)
    result = build_audited_financials(canonical, rows, audit)
    assert result.eligible_sales == Decimal("25.00")
    pd.testing.assert_frame_equal(canonical, original)


def test_export_text_labels_net_separately_from_eligible_sales():
    audit, rows = matched_inputs()
    result = build_audited_financials(filtered_canonical(), rows, audit)
    report = financial_report_text(result, business_name="Demo")
    assert "Full-export audited net sales: 15.00" in report
    assert "Filtered eligible sales: 25.00" in report
    assert "EXCLUDE refunds" in report
    assert "No historical price elasticity" in report


def test_missing_line_amount_rejected():
    audit, rows = matched_inputs()
    rows.loc[0, "eligible_sales_amount"] = float("nan")
    with pytest.raises(ValueError, match="Eligible sales"):
        build_audited_financials(filtered_canonical(), rows, audit)


def test_negative_cost_rejected():
    audit, rows = matched_inputs()
    frame = filtered_canonical()
    frame.loc[0, "unit_cost"] = -1.0
    with pytest.raises(ValueError, match="Unit cost"):
        build_audited_financials(frame, rows, audit)


def test_fractional_cost_input_is_rounded_only_after_multiplication():
    audit, rows = matched_inputs()
    frame = filtered_canonical()
    frame.loc[0, "unit_cost"] = 2.005
    result = build_audited_financials(frame, rows, audit)
    assert result.contribution_profit == Decimal("19.99")


def test_audited_quadrants_use_eligible_sales_margins():
    from analytics.financial_integration import audited_menu_quadrants

    audit, rows = matched_inputs()
    result = build_audited_financials(filtered_canonical(), rows, audit)
    quadrants = audited_menu_quadrants(result)
    assert set(quadrants["item"]) == {"Latte", "Tea"}
    assert set(quadrants["quadrant"]).issubset({"Star", "Plowhorse", "Puzzle", "Dog"})
    assert quadrants["margin_pct"].notna().all()


def test_audited_quadrants_require_costs():
    from analytics.financial_integration import audited_menu_quadrants

    audit, rows = matched_inputs()
    frame = filtered_canonical()
    frame.loc[0, "unit_cost"] = float("nan")
    result = build_audited_financials(frame, rows, audit)
    assert audited_menu_quadrants(result).empty


def test_reconciled_values_must_match_original_audit():
    audit, rows = matched_inputs()
    rows.loc[0, "eligible_sales_amount"] = 99.00
    with pytest.raises(ValueError, match="disagree"):
        build_audited_financials(filtered_canonical(), rows, audit)


def test_reconciled_refund_counts_must_match_original_audit():
    audit, rows = matched_inputs()
    rows.loc[2, "transaction_class"] = "cancelled"
    with pytest.raises(ValueError, match="Refund candidates"):
        build_audited_financials(filtered_canonical(), rows, audit)


def test_missing_time_does_not_create_fake_hourly_revenue():
    audit, rows = matched_inputs()
    result = build_audited_financials(filtered_canonical(), rows, audit)
    assert result.by_hour.empty


def test_hourly_sales_do_not_include_cancelled_transactions():
    audit, rows = matched_inputs()
    frame = filtered_canonical()
    frame["transaction_time"] = ["09:15:00", "10:15", "11:00:00"]
    result = build_audited_financials(frame, rows, audit)
    assert set(result.by_hour["hour"].astype(int)) == {9, 10}
    assert sum(result.by_hour["revenue"], Decimal("0.00")) == Decimal("25.00")


def test_full_export_totals_agree_across_category_and_day_views():
    audit, rows = matched_inputs()
    frame = filtered_canonical()
    frame["category"] = ["Drinks", "Drinks", "Food"]
    result = build_audited_financials(frame, rows, audit)
    assert sum(result.by_category["revenue"], Decimal("0.00")) == result.eligible_sales
    assert sum(result.by_day["revenue"], Decimal("0.00")) == result.eligible_sales
