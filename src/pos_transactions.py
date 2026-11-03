"""Explicit accounting for POS sales and refund candidates."""

from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_pos_transactions(df: pd.DataFrame) -> dict[str, float | int]:
    """Summarize positive sales and negative-quantity refund candidates.

    Assumes prices are positive per-unit amounts.
    Does not modify the original DataFrame.
    """
    required = {"price", "units_sold"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing POS transaction fields: "
            + ", ".join(sorted(missing))
        )

    work = df[["price", "units_sold"]].copy()

    for column in ("price", "units_sold"):
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

    if (
        work.isna().any().any()
        or not np.isfinite(work.to_numpy(dtype=float)).all()
    ):
        raise ValueError(
            "POS prices and quantities must be finite numbers."
        )

    if (work["price"] <= 0).any():
        raise ValueError(
            "POS unit prices must be greater than zero."
        )

    sales = work.loc[work["units_sold"] > 0]
    refund_candidates = work.loc[work["units_sold"] < 0]

    gross_units = float(sales["units_sold"].sum())
    refund_units = float(-refund_candidates["units_sold"].sum())

    gross_revenue = float(
        (sales["price"] * sales["units_sold"]).sum()
    )

    refund_value = float(
        -(
            refund_candidates["price"]
            * refund_candidates["units_sold"]
        ).sum()
    )

    return {
        "sale_rows": len(sales),
        "refund_candidate_rows": len(refund_candidates),
        "gross_units": gross_units,
        "refund_units": refund_units,
        "net_units": gross_units - refund_units,
        "gross_revenue": gross_revenue,
        "refund_value": refund_value,
        "net_revenue": gross_revenue - refund_value,
    }


def split_pos_transactions(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate nonnegative sales from negative-quantity candidates.

    Preserve every source row and its original values.
    This function does not validate cancellation statuses or
    confirm whether negative quantities are true refunds.
    """
    if df is None or df.empty:
        raise ValueError(
            "Cannot split an empty POS dataset."
        )

    if "units_sold" not in df.columns:
        raise ValueError(
            "Missing POS transaction field: units_sold."
        )

    quantities = pd.to_numeric(
        df["units_sold"],
        errors="coerce",
    )

    if not np.isfinite(
        quantities.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "POS quantities must be finite numbers."
        )

    sales_df = df.loc[quantities >= 0].copy()
    refund_candidates_df = df.loc[quantities < 0].copy()

    return sales_df, refund_candidates_df


def calculate_discounted_sales(
    df: pd.DataFrame,
    discount_column: str = "discount_amount",
) -> pd.DataFrame:
    """Calculate gross and realized sales for line-level discounts.

    Assumptions:
    - price is the listed unit price before discounts.
    - units_sold is a nonnegative quantity.
    - discount_amount is the total discount for the entire row,
      not a per-unit or percentage discount.
    - Tax, tips, and service charges are excluded.
    """
    required = {"price", "units_sold", discount_column}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing discount calculation fields: "
            + ", ".join(sorted(missing))
        )

    work = df.copy()

    for column in ["price", "units_sold", discount_column]:
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

    if (work["units_sold"] < 0).any():
        raise ValueError(
            "Discount calculation requires nonnegative quantities."
        )

    if (work[discount_column] < 0).any():
        raise ValueError(
            "Discount amounts cannot be negative."
        )

    gross = work["price"] * work["units_sold"]

    if (work[discount_column] > gross).any():
        raise ValueError(
            "Discount cannot exceed gross line sales."
        )

    work["gross_line_amount"] = gross
    work["realized_line_amount"] = gross - work[discount_column]

    work["effective_unit_price"] = np.where(
        work["units_sold"] > 0,
        work["realized_line_amount"]
        / work["units_sold"].replace(0, np.nan),
        np.nan,
    )

    return work


def calculate_percentage_discounted_sales(
    df: pd.DataFrame,
    percentage_column: str = "discount_percent",
) -> pd.DataFrame:
    """Calculate realized sales from percentage discounts.

    A value of 20 means 20%, not 0.20.
    Percentages apply to the gross line amount.
    """
    required = {"price", "units_sold", percentage_column}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            "Missing percentage discount fields: "
            + ", ".join(sorted(missing))
        )

    work = df.copy(deep=True)

    for column in ["price", "units_sold", percentage_column]:
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

    if (work["units_sold"] < 0).any():
        raise ValueError(
            "Percentage discounts require nonnegative quantities."
        )

    if (
        (work[percentage_column] < 0)
        | (work[percentage_column] > 100)
    ).any():
        raise ValueError(
            "Discount percentages must be between 0 and 100."
        )

    work["gross_line_amount"] = (
        work["price"] * work["units_sold"]
    )

    work["discount_amount"] = (
        work["gross_line_amount"]
        * work[percentage_column]
        / 100.0
    )

    work["realized_line_amount"] = (
        work["gross_line_amount"]
        - work["discount_amount"]
    )

    work["effective_unit_price"] = (
        work["realized_line_amount"]
        .div(work["units_sold"].replace(0, np.nan))
    )

    return work


def validate_discount_price_basis(
    price_basis: str,
) -> str:
    """Validate how source prices relate to discounts.

    listed:
        Prices are before discounts.
    realized:
        Prices already include discounts.
    unknown:
        The source price convention is unconfirmed.
    """
    allowed = {"listed", "realized", "unknown"}

    if price_basis not in allowed:
        raise ValueError(
            "Price basis must be 'listed', 'realized', or 'unknown'."
        )

    return price_basis
