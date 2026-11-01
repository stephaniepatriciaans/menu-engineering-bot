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
