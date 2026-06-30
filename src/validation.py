from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["date", "item", "category", "price", "unit_cost", "units_sold"]
NUMERIC_COLUMNS = ["price", "unit_cost", "units_sold"]


def validate_sales_df(df: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """
    Validate and clean uploaded sales data.

    Returns:
        cleaned_df: validated dataframe, or None if errors exist
        errors: blocking issues that should stop the app
        warnings: non-blocking issues to show the user
    """
    errors: list[str] = []
    warnings: list[str] = []

    if df is None or df.empty:
        return None, ["The uploaded file is empty."], warnings

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return None, errors, warnings

    df = df[REQUIRED_COLUMNS].copy()

    # Clean text columns
    df["item"] = df["item"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()

    blank_items = df["item"].eq("") | df["item"].str.lower().eq("nan")
    blank_categories = df["category"].eq("") | df["category"].str.lower().eq("nan")

    if blank_items.any():
        errors.append(f"{blank_items.sum()} rows have missing item names.")

    if blank_categories.any():
        errors.append(f"{blank_categories.sum()} rows have missing categories.")

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna()

    if bad_dates.any():
        errors.append(f"{bad_dates.sum()} rows have invalid dates.")

    # Numeric validation
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        bad_numeric = df[col].isna()

        if bad_numeric.any():
            errors.append(f"{bad_numeric.sum()} rows have invalid values in `{col}`.")

    if errors:
        return None, errors, warnings

    # Business-rule validation
    if (df["price"] <= 0).any():
        errors.append("Price must be greater than 0.")

    if (df["unit_cost"] < 0).any():
        errors.append("Unit cost cannot be negative.")

    if (df["units_sold"] < 0).any():
        errors.append("Units sold cannot be negative.")

    if (df["unit_cost"] > df["price"]).any():
        warnings.append(
            "Some rows have unit_cost greater than price. This may be valid for loss leaders, "
            "but it will produce negative margins."
        )

    today = pd.Timestamp.today().normalize()

    if (df["date"] > today).any():
        warnings.append("Some dates are in the future. Please confirm the date column is correct.")

    if (df["date"] < today - pd.DateOffset(years=10)).any():
        warnings.append("Some dates are more than 10 years old. Please confirm this is intentional.")

    duplicate_rows = df.duplicated(subset=["date", "item", "category", "price", "unit_cost"], keep=False)

    if duplicate_rows.any():
        warnings.append(
            "Some rows look duplicated. The app will still run, but duplicate sales rows may overstate demand."
        )

    if errors:
        return None, errors, warnings

    return df, errors, warnings