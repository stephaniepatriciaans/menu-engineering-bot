"""Non-destructive POS row review and sales-analysis eligibility screening.

All accounting/settlement audits must continue to use the ORIGINAL source export.
The eligible frame here is only for sales-only analytical calculations; it is
not a net-revenue ledger and review rows must never be automatically deleted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

_CANCELLED = frozenset({"cancelled", "canceled", "void", "voided"})
_REFUND = frozenset({"refund", "refunded", "returned", "return", "partial_refund"})
_REVIEW_COLUMN = "__pos_review_reasons"
_SOURCE_COLUMN = "__pos_source_row"


@dataclass(frozen=True)
class POSQuarantineResult:
    """Read-only partition of source records with an explicit audit trail."""

    analysis_rows: pd.DataFrame
    review_rows: pd.DataFrame
    reason_counts: dict[str, int]
    source_rows: int
    invalid_rows: int
    refund_candidates: int
    cancellation_candidates: int
    invoice_prefix_candidates: int
    uci_unverified_exclusions: int


def inspect_pos_rows(
    raw_df: pd.DataFrame,
    mapping: Mapping[str, str | None],
    *,
    status_column: str | None = None,
    amount_column: str | None = None,
    invoice_column: str | None = None,
    uci_cancellation_prefix: bool = False,
) -> POSQuarantineResult:
    """Partition rows for *sales-only analytics* without editing source records.

    Negative quantity and signed refund rows are flagged for review, never
    treated as verified refund deductions. C-prefixed invoice numbers are
    interpreted only when the caller explicitly enables the UCI convention.
    """
    required = ("date", "item", "price", "units_sold")
    missing = [name for name in required if mapping.get(name) not in raw_df.columns]
    if missing:
        raise ValueError(f"Required POS mappings missing: {', '.join(missing)}")
    if not raw_df.columns.is_unique:
        raise ValueError("Duplicate source column names must be resolved before review.")
    if not raw_df.index.is_unique:
        raise ValueError("Source index must be unique so rows can be audited safely.")
    if raw_df.empty:
        raise ValueError("Cannot review an empty POS export.")
    if uci_cancellation_prefix and (invoice_column is None or invoice_column not in raw_df):
        raise ValueError("Explicit UCI C-prefix handling requires an invoice column.")
    for name, col in (("status", status_column), ("amount", amount_column)):
        if col is not None and col not in raw_df:
            raise ValueError(f"Mapped {name} column is missing: {col}")
    if _REVIEW_COLUMN in raw_df or _SOURCE_COLUMN in raw_df:
        raise ValueError("The export uses reserved review metadata column names.")

    source = raw_df
    item = source[mapping["item"]].astype("string").str.strip()
    blank_item = item.isna() | item.eq("").fillna(True)
    date = pd.to_datetime(source[mapping["date"]], errors="coerce", format="mixed")
    bad_date = date.isna()

    qty = pd.to_numeric(source[mapping["units_sold"]], errors="coerce")
    price = pd.to_numeric(source[mapping["price"]], errors="coerce")
    invalid_qty = qty.isna() | ~np.isfinite(qty)
    invalid_price = price.isna() | ~np.isfinite(price) | price.le(0)
    zero_qty = qty.eq(0)
    negative_qty = qty.lt(0)

    if status_column:
        status = source[status_column].astype("string").str.strip().str.casefold()
        cancelled = status.isin(_CANCELLED)
        refund_status = status.isin(_REFUND)
    else:
        cancelled = pd.Series(False, index=source.index)
        refund_status = pd.Series(False, index=source.index)

    if amount_column:
        amount = pd.to_numeric(source[amount_column], errors="coerce")
        negative_amount = amount.lt(0)
    else:
        negative_amount = pd.Series(False, index=source.index)

    refund = negative_qty | negative_amount | refund_status
    invoice_c = pd.Series(False, index=source.index)
    if invoice_column is not None and invoice_column in source.columns:
        invoice_c = source[invoice_column].astype("string").str.strip().str.upper().str.startswith("C", na=False)

    # Optional unit-cost data is not authoritative. Malformed nonblank costs
    # should not be passed into profitability analytics as valid numeric costs.
    bad_cost = pd.Series(False, index=source.index)
    cost_col = mapping.get("unit_cost")
    if cost_col is not None and cost_col in source.columns:
        cost_raw = source[cost_col]
        parsed = pd.to_numeric(cost_raw, errors="coerce")
        nonblank = cost_raw.notna() & cost_raw.astype("string").str.strip().ne("").fillna(False)
        bad_cost = nonblank & (parsed.isna() | ~np.isfinite(parsed) | parsed.lt(0))

    reasons = {
        "missing_item": blank_item,
        "invalid_date": bad_date,
        "nonpositive_or_invalid_price": invalid_price,
        "invalid_quantity": invalid_qty | zero_qty,
        "invalid_unit_cost": bad_cost,
        "negative_quantity_refund_candidate": negative_qty,
        "negative_amount_refund_candidate": negative_amount,
        "refund_status_review": refund_status,
        "cancelled_status_review": cancelled,
    }
    if uci_cancellation_prefix:
        reasons["uci_c_prefixed_invoice_review"] = invoice_c
    reasons = {key: mask.fillna(False).astype(bool) for key, mask in reasons.items()}

    # Rows with malformed required fields are ineligible, even if refund-like;
    # signed refund/cancel statuses also stay outside sales-only analytics.
    invalid = (blank_item | bad_date | invalid_price | invalid_qty | zero_qty | bad_cost).fillna(False)
    review = (invalid | refund | cancelled | (invoice_c if uci_cancellation_prefix else False)).fillna(False)
    eligible = ~review

    review_frame = source.loc[review].copy()
    review_frame[_SOURCE_COLUMN] = np.flatnonzero(review.to_numpy()) + 2  # Excel/CSV row numbers, header is row 1.
    reason_text = pd.Series("", index=source.index, dtype="string")
    for reason, mask in reasons.items():
        reason_text = reason_text + np.where(mask, reason + ";", "")
    review_frame[_REVIEW_COLUMN] = reason_text.loc[review].str.rstrip(";")

    return POSQuarantineResult(
        analysis_rows=source.loc[eligible].copy(),
        review_rows=review_frame,
        reason_counts={name: int(mask.sum()) for name, mask in reasons.items()},
        source_rows=len(source),
        invalid_rows=int(invalid.sum()),
        refund_candidates=int(refund.sum()),
        cancellation_candidates=int(cancelled.sum()),
        invoice_prefix_candidates=int(invoice_c.sum()),
        uci_unverified_exclusions=int(
            (invoice_c & ~refund & ~cancelled & ~invalid).sum()
        ) if uci_cancellation_prefix else 0,
    )
