"""Universal POS sales and discount normalization."""

import numpy as np
import pandas as pd

from pos.transactions import (
    calculate_discounted_sales,
    calculate_percentage_discounted_sales,
    validate_discount_price_basis,
)


def normalize_pos_financials(
    df: pd.DataFrame,
    *,
    price_basis: str = "unknown",
    discount_type: str | None = None,
) -> pd.DataFrame:
    """Normalize POS financial data without guessing price conventions.

    Assumptions:
    - price is a per-unit amount.
    - units_sold is the transaction-row quantity.
    - negative quantities are refund candidates.
    - discount_amount is a line-level monetary discount.
    - discount_percent uses 20 for 20%.
    """
    validate_discount_price_basis(price_basis)

    if discount_type not in {None, "amount", "percent"}:
        raise ValueError(
            "discount_type must be None, 'amount', or 'percent'."
        )

    required = {"price", "units_sold"}

    if discount_type == "amount":
        required.add("discount_amount")
    elif discount_type == "percent":
        required.add("discount_percent")

    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing POS financial fields: "
            + ", ".join(sorted(missing))
        )

    work = df.copy(deep=True)

    for column in required:
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

        if not np.isfinite(
            work[column].to_numpy(dtype=float)
        ).all():
            raise ValueError(
                f"{column} must contain finite numeric values."
            )

    if (work["price"] <= 0).any():
        raise ValueError("Price must be greater than zero.")

    work["is_refund_candidate"] = work["units_sold"] < 0

    # Signed gross amounts retain refund candidates.
    work["source_line_amount"] = (
        work["price"] * work["units_sold"]
    )

    # Do not label unverified figures as realized revenue.
    work["realized_line_amount"] = np.nan
    work["discount_applied"] = np.nan

    # Price convention is unknown: retain source values only.
    if price_basis == "unknown":
        return work

    sales_mask = work["units_sold"] >= 0

    # Already-discounted prices: never subtract discounts again.
    if price_basis == "realized":
        work.loc[
            sales_mask, "realized_line_amount"
        ] = work.loc[sales_mask, "source_line_amount"]

        work.loc[sales_mask, "discount_applied"] = 0.0

        return work

    # Listed prices without mapped discounts.
    if discount_type is None:
        return work

    sales = work.loc[sales_mask].copy()

    if discount_type == "amount":
        normalized = calculate_discounted_sales(sales)
    else:
        normalized = calculate_percentage_discounted_sales(
            sales
        )

    work.loc[
        sales_mask, "realized_line_amount"
    ] = normalized["realized_line_amount"]

    work.loc[
        sales_mask, "discount_applied"
    ] = normalized["discount_amount"]

    return work
