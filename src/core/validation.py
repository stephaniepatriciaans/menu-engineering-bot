"""Validation and capability detection for canonical menu-engineering data."""

from __future__ import annotations

import pandas as pd

from config import CANONICAL_FIELDS, CORE_FIELDS


def validate_sales_df(df: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Validate/clean a canonical dataframe while keeping unit cost optional."""
    errors: list[str] = []
    warnings: list[str] = []

    if df is None or df.empty:
        return None, ["The dataset is empty."], warnings

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    missing_core = [col for col in CORE_FIELDS if col not in df.columns]
    if missing_core:
        return None, [f"Missing required canonical fields: {', '.join(missing_core)}"], warnings

    if "category" not in df.columns:
        df["category"] = "Uncategorized"
        warnings.append("Category was not available, so all rows were labeled 'Uncategorized'.")
    
    if "unit_cost" not in df.columns:
        df["unit_cost"] = pd.NA

    # Transaction time is optional.
    if "transaction_time" not in df.columns:
        df["transaction_time"] = pd.NA

    df = df[CANONICAL_FIELDS].copy()

    df["item"] = df["item"].astype("string").str.strip()
    blank_items = df["item"].isna() | df["item"].eq("")
    if blank_items.any():
        errors.append(f"{int(blank_items.sum())} rows have missing item names.")

    df["category"] = df["category"].astype("string").str.strip()
    blank_categories = df["category"].isna() | df["category"].eq("")
    if blank_categories.any():
        df.loc[blank_categories, "category"] = "Uncategorized"
        warnings.append(f"{int(blank_categories.sum())} blank categories were set to 'Uncategorized'.")

    
    # Parse dates, including combined date-and-time values.
    original_dates = df["date"].copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    bad_dates = df["date"].isna()

    if bad_dates.any():
        errors.append(
            f"{int(bad_dates.sum())} rows have invalid dates."
        )
    else:
        # Detect explicitly supplied times in combined timestamps.
        # Date-only values must not create artificial times.
        has_embedded_time = (
            original_dates.astype("string")
            .str.contains(
                r"(?:T|\s)\d{1,2}:\d{2}",
                regex=True,
                na=False,
            )
        )

        missing_time = (
            df["transaction_time"].isna()
            | df["transaction_time"]
                .astype("string")
                .str.strip()
                .isin(["", "nan", "None"])
        ).fillna(True)

        fill_time = has_embedded_time & missing_time

        df.loc[fill_time, "transaction_time"] = (
            df.loc[fill_time, "date"]
            .dt.strftime("%H:%M:%S")
        )

        # Keep dates normalized for existing daily analyses.
        df["date"] = df["date"].dt.normalize()


    # Validate prices and quantities, including infinity.
    for col in ["price", "units_sold"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

        bad = (
            df[col].isna()
            | df[col].isin([float("inf"), float("-inf")])
        )

        if bad.any():
            errors.append(
                f"{int(bad.sum())} rows have invalid values in `{col}`."
            )

    # Unit cost is optional, but infinity is invalid.
    df["unit_cost"] = pd.to_numeric(
        df["unit_cost"],
        errors="coerce",
    )

    invalid_cost = df["unit_cost"].isin(
        [float("inf"), float("-inf")]
    )

    if invalid_cost.any():
        errors.append(
            f"{int(invalid_cost.sum())} rows have non-finite unit costs."
        )

    if errors:
        return None, errors, warnings


    if (df["price"] <= 0).any():
        errors.append("Price must be greater than 0.")
    if (df["units_sold"] < 0).any():
        errors.append("Units sold cannot be negative.")

    cost_present = df["unit_cost"].notna()
    if cost_present.any() and (df.loc[cost_present, "unit_cost"] < 0).any():
        errors.append("Unit cost cannot be negative.")
    if cost_present.any() and (df.loc[cost_present, "unit_cost"] > df.loc[cost_present, "price"]).any():
        warnings.append(
            "Some unit costs exceed selling price. This can be valid for loss leaders, but it creates negative margins."
        )
    if cost_present.any() and not cost_present.all():
        warnings.append(
            "Unit cost is only available for part of the dataset. Full profit analysis is disabled until every sales row has cost."
        )
    if not cost_present.any():
        warnings.append(
            "Unit cost is unavailable. Revenue, popularity, trends, and price-variation analysis remain available."
        )

    today = pd.Timestamp.today().normalize()
    if (df["date"] > today).any():
        warnings.append("Some dates are in the future. Please confirm the date mapping is correct.")
    if (df["date"] < today - pd.DateOffset(years=10)).any():
        warnings.append("Some dates are more than 10 years old. Please confirm this is intentional.")

    if df.duplicated(keep=False).any():
        warnings.append(
            "Some standardized sales rows have identical values. "
            "These may represent separate, legitimate purchases. "
            "Review the original transaction IDs before "
            "deciding whether any records are duplicates. "
            "No rows have been removed."
        )

    if errors:
        return None, errors, warnings
    return df, errors, warnings



def audit_source_transactions(
    raw_df: pd.DataFrame,
) -> list[str]:
    """
    Audit the original POS dataset for possible duplicates.

    Preserve all rows. Repeated transaction IDs and identical
    records are flagged for review, never automatically deleted.
    """
    messages: list[str] = []

    if raw_df is None or raw_df.empty:
        return messages

    # Check identical rows in the original, unmodified CSV
    exact_repeat_rows = int(
        raw_df.duplicated(keep=False).sum()
    )

    if exact_repeat_rows:
        messages.append(
            f"Source CSV: {exact_repeat_rows:,} rows belong "
            "to groups of identical full-source rows. "
            "Review these records before removing anything."
        )

    # Look for a transaction identifier
    id_column = next(
        (
            col for col in raw_df.columns
            if str(col).strip().casefold() == "transaction_id"
        ),
        None,
    )

    if id_column is not None:
        ids = raw_df[id_column].astype("string").str.strip()

        valid_ids = ids.notna() & ids.ne("")

        missing_ids = int((~valid_ids).sum())

        repeated_id_rows = int(
            ids.loc[valid_ids].duplicated(
                keep=False
            ).sum()
        )

        if missing_ids:
            messages.append(
                f"Source CSV: {missing_ids:,} rows "
                "have no transaction_id."
            )

        if repeated_id_rows:
            messages.append(
                f"Source CSV: {repeated_id_rows:,} rows "
                "share transaction_id values with another row. "
                "This may be normal for multi-item orders; "
                "inspect full records before treating them "
                "as duplicates."
            )

        elif not missing_ids:
            messages.append(
                "Source CSV: transaction_id is present "
                "and unique for every row."
            )

    else:
        messages.append(
            "Source CSV has no transaction_id column. "
            "Identical values cannot reliably identify "
            "duplicate purchases."
        )

    return messages


def determine_capabilities(df: pd.DataFrame) -> dict[str, bool]:
    """Report analyses that are safe to run from the available canonical fields."""
    if df is None or df.empty:
        return {
            "revenue_analysis": False,
            "popularity_analysis": False,
            "sales_trend_analysis": False,
            "price_variation_analysis": False,
            "historical_elasticity_estimation": False,
            "profit_analysis": False,
            "menu_engineering_quadrants": False,
            "price_optimization": False,
        }

    has_cost = "unit_cost" in df.columns and df["unit_cost"].notna().all()
    variation = df.groupby("item")["price"].nunique(dropna=True) if "price" in df else pd.Series(dtype=float)
    has_price_variation = bool((variation >= 2).any())

    return {
        "revenue_analysis": True,
        "popularity_analysis": True,
        "sales_trend_analysis": True,
        "price_variation_analysis": True,
        "historical_elasticity_estimation": has_price_variation,
        "profit_analysis": bool(has_cost),
        "menu_engineering_quadrants": bool(has_cost),
        "price_optimization": bool(has_cost),
    }
