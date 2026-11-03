"""Non-authoritative, source-based POS review indicators.

These checks never change transactions or certify net revenue.
"""

from __future__ import annotations

from typing import NamedTuple

import pandas as pd

from pos.classification import classify_pos_transactions


class FinancialReview(NamedTuple):
    refund_candidates: int | None
    cancelled: int | None
    conflicts: int | None
    needs_review: int | None
    discount_fields_mapped: int
    price_basis: str
    classification_note: str | None


def summarize_financial_review(
    raw_df: pd.DataFrame,
    mapping: dict[str, str | None],
    *,
    status_column: str | None = None,
    amount_column: str | None = None,
    discount_column: str | None = None,
    discount_percent_column: str | None = None,
    price_basis: str = "unknown",
) -> FinancialReview:
    """Summarize preliminary signals; no revenue adjustments are implied.

    An absent status/amount mapping cannot establish that a refund
    or cancellation did not occur. Negative quantities are still checked.
    """
    discounts = sum(
        column is not None
        for column in (discount_column, discount_percent_column)
    )
    quantity_column = mapping.get("units_sold")
    if quantity_column is None or quantity_column not in raw_df.columns:
        return FinancialReview(
            None, None, None, None, discounts, price_basis,
            "Quantity mapping is unavailable; transaction checks could not run.",
        )

    try:
        classified = classify_pos_transactions(
            raw_df,
            quantity_column=quantity_column,
            status_column=status_column,
            amount_column=amount_column,
        )
    except ValueError as exc:
        return FinancialReview(
            None, None, None, None, discounts, price_basis,
            f"Transaction checks could not run: {exc}",
        )

    counts = classified["transaction_class"].value_counts()
    return FinancialReview(
        int(counts.get("refund_candidate", 0)),
        int(counts.get("cancelled", 0)),
        int(classified["has_classification_conflict"].sum()),
        int(classified["requires_accounting_review"].sum()),
        discounts,
        price_basis,
        None,
    )
