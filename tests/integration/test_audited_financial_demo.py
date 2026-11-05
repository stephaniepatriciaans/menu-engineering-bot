"""End-to-end independent settlement audit using a portable demo CSV."""

from decimal import Decimal
from pathlib import Path

import pandas as pd

from analytics.financial_integration import build_audited_financials
from pos.export_validation import audit_pos_export
from pos.reconciliation import reconcile_pos_sales

DEMO = (
    Path(__file__).resolve().parents[2]
    / "data" / "synthetic" / "part4_audited_demo.csv"
)


def test_audited_demo_matches_and_keeps_refunds_unattributed():
    data = pd.read_csv(DEMO)
    result = audit_pos_export(
        data, price_basis="listed", amount_column="signed_amount",
        status_column="status", event_id_column="event_id",
        refund_convention="separate_signed_events",
        source_amount_basis="pre_tax_sales", expected_net_sales="15.00",
        verified_conventions=True,
    )
    assert result.outcome == "matched"
    rows = reconcile_pos_sales(
        data, price_basis="listed", amount_column="signed_amount",
        status_column="status", verified_conventions=True,
    )
    canonical = data.loc[[0, 1, 3], [
        "date", "item", "category", "units_sold", "unit_cost"
    ]].copy()
    view = build_audited_financials(canonical, rows, result)
    assert view.full_export_net_sales == Decimal("15.00")
    assert view.eligible_sales == Decimal("25.00")
    assert view.contribution_profit == Decimal("20.00")
    assert view.by_item["item"].tolist() == ["Latte", "Tea"]
