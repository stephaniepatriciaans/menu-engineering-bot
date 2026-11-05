"""Independent POS export audit; never infer a provider's refund conventions.

This module does not change the dashboard's revenue or verify accounting by
itself. A matching POS summary is required for a positive audit result.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

import pandas as pd

from pos.reconciliation import reconcile_pos_sales

RefundConvention = Literal["unknown", "separate_signed_events", "status_only_original"]
_CENT = Decimal("0.01")


def _amount(value: object, label: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite monetary amount") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label} must be a finite monetary amount")
    return parsed.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class POSAudit:
    eligible_sales: Decimal | None
    signed_refund_events: Decimal | None
    proposed_net_sales: Decimal | None
    expected_net_sales: Decimal | None
    difference: Decimal | None
    outcome: Literal["matched", "mismatch", "review_required"]
    findings: tuple[str, ...]
    eligible_rows: int
    refund_candidates: int
    cancelled_rows: int

    def as_dict(self) -> dict[str, object]:
        """Convert to JSON-compatible values without binary floating point."""
        return {
            "eligible_sales": str(self.eligible_sales) if self.eligible_sales is not None else None,
            "signed_refund_events": (
                str(self.signed_refund_events) if self.signed_refund_events is not None else None
            ),
            "proposed_net_sales": (
                str(self.proposed_net_sales) if self.proposed_net_sales is not None else None
            ),
            "expected_net_sales": (
                str(self.expected_net_sales) if self.expected_net_sales is not None else None
            ),
            "difference": str(self.difference) if self.difference is not None else None,
            "outcome": self.outcome,
            "findings": list(self.findings),
            "eligible_rows": self.eligible_rows,
            "refund_candidates": self.refund_candidates,
            "cancelled_rows": self.cancelled_rows,
        }


def audit_pos_export(
    df: pd.DataFrame,
    *,
    price_basis: str = "unknown",
    amount_column: str | None = None,
    status_column: str | None = None,
    event_id_column: str | None = None,
    refund_convention: RefundConvention = "unknown",
    source_amount_basis: Literal["unknown", "pre_tax_sales"] = "unknown",
    expected_net_sales: object | None = None,
    verified_conventions: bool = False,
    **discount_columns: object,
) -> POSAudit:
    """Audit *pre-tax item-sales* totals against an independent POS summary.

    Requirements for a matched result:
      - the user explicitly confirms the export's column and refund rules;
      - source signed amounts exclude taxes, tips, fees and tender movements;
      - each signed refund is a distinct negative event with a unique event ID;
      - no ambiguous refund-status originals or cancellation/refund conflicts;
      - the computed total agrees to the cent with the supplied POS summary.

    A `matched` audit is scoped only to THIS export and comparison. It does not
    prove future POS files have the same conventions. We do not edit the input.
    """
    if refund_convention not in ("unknown", "separate_signed_events", "status_only_original"):
        raise ValueError("Unrecognized refund convention")
    if source_amount_basis not in ("unknown", "pre_tax_sales"):
        raise ValueError("Unrecognized source amount basis")
    if event_id_column is not None and event_id_column not in df.columns:
        raise ValueError(f"Missing event ID column: {event_id_column}")
    if expected_net_sales is not None:
        expected = _amount(expected_net_sales, "expected_net_sales")
    else:
        expected = None

    reconciled = reconcile_pos_sales(
        df,
        price_basis=price_basis,
        status_column=status_column,
        amount_column=amount_column,
        verified_conventions=False,
        **discount_columns,
    )
    eligible = reconciled[reconciled["eligible_sale"]]
    refund = reconciled[reconciled["transaction_class"].eq("refund_candidate")]
    cancelled = reconciled[reconciled["transaction_class"].eq("cancelled")]
    findings: list[str] = []
    sales: Decimal | None = None
    if price_basis == "unknown":
        findings.append("Unit price basis is unknown; eligible sales cannot be reconciled.")
    elif eligible["eligible_sales_amount"].isna().any():
        findings.append("Some eligible sales lack calculable amounts.")
    else:
        sales = sum(
            (_amount(value, "eligible_sales_amount") for value in eligible["eligible_sales_amount"]),
            Decimal("0.00"),
        )

    signed_refunds: Decimal | None = None
    net: Decimal | None = None
    if not verified_conventions:
        findings.append("Export accounting conventions have not been explicitly confirmed.")
    if source_amount_basis != "pre_tax_sales":
        findings.append("Signed amounts may include taxes, tips, fees, or tender movements.")
    if refund_convention != "separate_signed_events":
        findings.append("Refund format is not confirmed as separate signed events.")
    if amount_column is None:
        findings.append("A signed transaction-amount column is required.")
    if event_id_column is None:
        findings.append("Unique transaction-event IDs are required to prevent duplicate refund deductions.")
    elif df[event_id_column].isna().any() or df[event_id_column].duplicated().any():
        findings.append("Transaction-event IDs are missing or duplicated.")

    # Reconciliation uses the listed/realized unit price plus mapped discounts.
    # Independently exported signed sale amounts must match the same pre-tax,
    # post-discount basis or the mapping is not verified.
    if sales is not None and amount_column is not None:
        signed_sales = sum(
            (_amount(value, "signed_sale") for value in eligible[amount_column]),
            Decimal("0.00"),
        )
        if signed_sales != sales:
            findings.append(
                "POS signed sale amounts do not match calculated eligible sales; "
                "check discounts, taxes, tips, and unit-price basis."
            )

    if len(refund) and amount_column is not None:
        refund_amounts = [_amount(value, "signed_refund") for value in refund[amount_column]]
        if any(value >= 0 for value in refund_amounts):
            findings.append("Refund candidates include original/positive events; do not deduct these.")
        else:
            signed_refunds = sum(refund_amounts, Decimal("0.00"))
    elif amount_column is not None:
        signed_refunds = Decimal("0.00")

    if reconciled["has_classification_conflict"].any():
        findings.append("Conflicting quantity/amount/status evidence requires review.")
    if expected is None:
        findings.append("No independent POS net-sales summary was supplied.")

    # Do not claim net revenue if ANY precondition is unresolved.
    if not findings and sales is not None and signed_refunds is not None:
        net = sales + signed_refunds

    difference = net - expected if net is not None and expected is not None else None
    outcome: Literal["matched", "mismatch", "review_required"] = "review_required"
    if difference is not None:
        outcome = "matched" if difference == 0 else "mismatch"
        if outcome == "mismatch":
            findings.append("POS summary differs from computed pre-tax net sales.")

    return POSAudit(
        eligible_sales=sales,
        signed_refund_events=signed_refunds,
        proposed_net_sales=net,
        expected_net_sales=expected,
        difference=difference,
        outcome=outcome,
        findings=tuple(findings),
        eligible_rows=len(eligible),
        refund_candidates=len(refund),
        cancelled_rows=len(cancelled),
    )
