"""Classify POS transaction records without altering source data."""

import numpy as np
import pandas as pd

REFUND_STATUSES = {
    "refunded",
    "refund",
    "returned",
    "return",
    "partial_refund",
}

CANCELLED_STATUSES = {
    "cancelled",
    "canceled",
    "void",
    "voided",
}


def classify_pos_transactions(
    df: pd.DataFrame,
    *,
    quantity_column: str = "units_sold",
    amount_column: str | None = None,
    status_column: str | None = None,
) -> pd.DataFrame:
    """Classify sales, refund candidates, and cancelled transactions.

    Negative quantities or negative line amounts are treated
    as refund candidates.

    Explicit refund statuses take precedence over cancellation
    statuses. Statuses are normalized case-insensitively.

    The original dataframe is not modified.
    """
    
    # Reject duplicate source column names before processing.
    if not df.columns.is_unique:
        raise ValueError(
            "Duplicate POS column names are not supported "
            "for transaction classification."
        )

    # Prevent one source column from being reused for
    # multiple classification fields.
    selected_columns = [
        column
        for column in (
            quantity_column,
            amount_column,
            status_column,
        )
        if column is not None
    ]

    if len(selected_columns) != len(set(selected_columns)):
        raise ValueError(
            "POS classification columns must be distinct."
        )

    # Validate the required quantity column.
    if quantity_column not in df.columns:
        raise ValueError(
            f"Missing quantity column: {quantity_column}"
        )

    for optional_column in (amount_column, status_column):
        if (
            optional_column is not None
            and optional_column not in df.columns
        ):
            raise ValueError(
                f"Missing POS classification column: {optional_column}"
            )

    work = df.copy(deep=True)

    quantities = pd.to_numeric(
        work[quantity_column],
        errors="coerce",
    )

    if not np.isfinite(quantities.to_numpy(dtype=float)).all():
        raise ValueError(
            "Transaction quantities must be finite numeric values."
        )

    refund_mask = quantities < 0
    
    negative_quantity_mask = quantities < 0

    negative_amount_mask = pd.Series(
        False,
        index=work.index,
    )

    if amount_column is not None:
        amounts = pd.to_numeric(
            work[amount_column],
            errors="coerce",
        )

        if not np.isfinite(amounts.to_numpy(dtype=float)).all():
            raise ValueError(
                "Transaction amounts must be finite numeric values."
            )

        negative_amount_mask = amounts < 0

        refund_mask = refund_mask | negative_amount_mask

    cancellation_mask = pd.Series(
        False,
        index=work.index,
    )
    
    refund_status_mask = pd.Series(
        False,
        index=work.index,
    )

    if status_column is not None:
        statuses = (
            work[status_column]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"[\s-]+", "_", regex=True)
        )

        refund_status_mask = statuses.isin(
            REFUND_STATUSES
        )

        refund_mask = refund_mask | refund_status_mask

        cancellation_mask = statuses.isin(
            CANCELLED_STATUSES
        )

    work["transaction_class"] = "sale"

    work.loc[
        cancellation_mask,
        "transaction_class",
    ] = "cancelled"

    work.loc[
        refund_mask,
        "transaction_class",
    ] = "refund_candidate"

    # These classifications describe evidence, not confirmed
    # financial adjustments. A refunded status may belong
    # to the original sale rather than a refund event.
    work["requires_accounting_review"] = (
        work["transaction_class"] != "sale"
    )
    
    # Detect contradictory transaction evidence.
    #
    # A cancellation combined with negative financial
    # signals requires review rather than automatic
    # treatment as a normal refund.
    cancellation_refund_conflict = (
        cancellation_mask
        & (
            negative_quantity_mask
            | negative_amount_mask
            | refund_status_mask
        )
    )

    # A positive quantity combined with a negative amount
    # may reflect a refund convention or inconsistent data.
    quantity_amount_conflict = (
        quantities > 0
    ) & negative_amount_mask

    # A negative quantity combined with a positive amount
    # may reflect a return convention or inconsistent data.
    if amount_column is not None:
        amounts = pd.to_numeric(
            work[amount_column],
            errors="coerce",
        )

        amount_quantity_conflict = (
            negative_quantity_mask & (amounts > 0)
        )
    else:
        amount_quantity_conflict = pd.Series(
            False,
            index=work.index,
        )

    work["has_classification_conflict"] = (
        cancellation_refund_conflict
        | quantity_amount_conflict
        | amount_quantity_conflict
    )

    work["requires_accounting_review"] = (
        (work["transaction_class"] != "sale")
        | work["has_classification_conflict"]
    )


    # Explain each candidate without asserting that a refund was processed.
    work["refund_signal_negative_quantity"] = negative_quantity_mask
    work["refund_signal_negative_amount"] = negative_amount_mask
    work["refund_signal_status"] = refund_status_mask
    work["cancellation_signal_status"] = cancellation_mask
    work["accounting_evidence"] = [
        ", ".join(
            label for flag, label in (
                (nq, "negative_quantity"),
                (na, "negative_amount"),
                (rs, "refund_status"),
                (cs, "cancelled_status"),
            ) if flag
        ) or "no_refund_or_cancellation_signal"
        for nq, na, rs, cs in zip(
            negative_quantity_mask, negative_amount_mask,
            refund_status_mask, cancellation_mask, strict=True,
        )
    ]


    return work
