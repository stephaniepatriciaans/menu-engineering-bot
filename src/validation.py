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

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna()
    if bad_dates.any():
        errors.append(f"{int(bad_dates.sum())} rows have invalid dates.")
    else:
        # Transaction timestamps are normalized to calendar date so daily sales
        # velocity and elasticity aggregation are not distorted by time-of-day.
        df["date"] = df["date"].dt.normalize()

    for col in ["price", "units_sold"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        bad = df[col].isna()
        if bad.any():
            errors.append(f"{int(bad.sum())} rows have invalid values in `{col}`.")

    df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce")

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
            "Some rows are exact duplicates. The app will still run, but duplicate sales rows may overstate demand."
        )

    if errors:
        return None, errors, warnings
    return df, errors, warnings


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
