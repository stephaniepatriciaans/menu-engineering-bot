"""Provider-agnostic POS export validation using explicit field mapping.

The included fixture imitates a plausible restaurant POS line-item export.
It is NOT an official Toast specification, and no accounting conventions are
inferred from a provider name. This adapter never modifies source records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from pos.export_validation import POSAudit, audit_pos_export


@dataclass(frozen=True)
class POSFieldMap:
    """Explicit source-column bindings; never guess accounting semantics."""

    date: str
    item: str
    price: str
    quantity: str
    status: str | None = None
    signed_amount: str | None = None
    event_id: str | None = None
    category: str | None = None
    line_discount: str | None = None
    discount_percent: str | None = None
    per_unit_discount: str | None = None
    order_id: str | None = None
    order_discount: str | None = None
    order_percent: str | None = None


@dataclass(frozen=True)
class POSValidationResult:
    """Raw-preserving validation output with the existing financial audit."""

    canonical: pd.DataFrame
    audit: POSAudit
    source_rows: int


def adapt_pos_export(raw: pd.DataFrame, fields: POSFieldMap) -> pd.DataFrame:
    """Map source fields without dropping rows or silently merging columns."""
    if raw.empty:
        raise ValueError("POS export contains no transaction rows.")
    if not raw.columns.is_unique:
        raise ValueError("POS export has duplicate source column names.")
    if not raw.index.is_unique:
        raise ValueError("POS export requires unique source row indices.")

    bindings = {
        "date": fields.date,
        "item": fields.item,
        "price": fields.price,
        "units_sold": fields.quantity,
        "status": fields.status,
        "signed_amount": fields.signed_amount,
        "event_id": fields.event_id,
        "category": fields.category,
        "line_discount": fields.line_discount,
        "discount_percent": fields.discount_percent,
        "per_unit_discount": fields.per_unit_discount,
        "order_id": fields.order_id,
        "order_discount": fields.order_discount,
        "order_percent": fields.order_percent,
    }
    chosen = {field: source for field, source in bindings.items() if source is not None}
    sources = list(chosen.values())
    if len(sources) != len(set(sources)):
        raise ValueError("POS mapping reuses one source column for multiple fields.")
    missing = sorted(set(sources) - set(raw.columns))
    if missing:
        raise ValueError("Mapped POS source columns not found: " + ", ".join(missing))

    # Reject collisions with existing, unmapped columns (e.g., raw already has
    # a different 'price' field and source 'Unit Price' is mapped to 'price').
    remaining = set(raw.columns) - set(sources)
    collisions = sorted(set(chosen) & remaining)
    if collisions:
        raise ValueError("Canonical column name collision: " + ", ".join(collisions))

    renamed = raw.rename(columns={source: field for field, source in chosen.items()})
    return renamed.copy(deep=True)


def audit_mapped_pos_export(
    raw: pd.DataFrame,
    fields: POSFieldMap,
    *,
    price_basis: Literal["unknown", "listed", "realized"] = "unknown",
    refund_convention: Literal[
        "unknown", "separate_signed_events", "status_only_original"
    ] = "unknown",
    source_amount_basis: Literal["unknown", "pre_tax_sales"] = "unknown",
    expected_net_sales: object | None = None,
    verified_conventions: bool = False,
    stacking: Literal["exclusive", "sequential"] = "exclusive",
) -> POSValidationResult:
    """Use the existing conservative audit, never infer verified net sales.

    A 'matched' result is possible only if the caller separately confirms
    export conventions AND supplies an independent pre-tax sales total.
    This helper does not automatically certify any Toast-style CSV.
    """
    frame = adapt_pos_export(raw, fields)
    discount_bindings = {
        "line_discount_column": "line_discount" if fields.line_discount else None,
        "percent_column": "discount_percent" if fields.discount_percent else None,
        "per_unit_discount_column": "per_unit_discount" if fields.per_unit_discount else None,
        "order_id_column": "order_id" if fields.order_id else None,
        "order_discount_column": "order_discount" if fields.order_discount else None,
        "order_percent_column": "order_percent" if fields.order_percent else None,
    }
    audit = audit_pos_export(
        frame,
        price_basis=price_basis,
        status_column="status" if fields.status else None,
        amount_column="signed_amount" if fields.signed_amount else None,
        event_id_column="event_id" if fields.event_id else None,
        refund_convention=refund_convention,
        source_amount_basis=source_amount_basis,
        expected_net_sales=expected_net_sales,
        verified_conventions=verified_conventions,
        stacking=stacking,
        **discount_bindings,
    )
    return POSValidationResult(canonical=frame, audit=audit, source_rows=len(raw))
