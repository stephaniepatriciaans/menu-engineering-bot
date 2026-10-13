"""Reusable, testable dashboard calculations."""

from __future__ import annotations

import pandas as pd

SORTING_OPTIONS = {
    "Highest revenue": ("total_revenue", False),
    "Lowest revenue": ("total_revenue", True),
    "Best-selling (units)": ("total_units_sold", False),
    "Lowest-selling (units)": ("total_units_sold", True),
    "Alphabetical (A-Z)": ("item", True),
    "Alphabetical (Z-A)": ("item", False),
}


def _datetime_index(values: pd.Series) -> pd.DatetimeIndex:
    """Parse dates positionally, without relying on pandas Series.dt typing."""
    return pd.DatetimeIndex(pd.to_datetime(values, errors="coerce"))


def sort_menu_items(
    summary: pd.DataFrame,
    sort_option: str = "Highest revenue",
) -> pd.DataFrame:
    """Sort menu items without modifying the original dataframe."""
    if sort_option not in SORTING_OPTIONS:
        raise ValueError(f"Unsupported sorting option: {sort_option}")

    column, ascending = SORTING_OPTIONS[sort_option]
    return summary.sort_values(
        by=column, ascending=ascending, kind="stable"
    ).copy()


def filter_by_date_range(
    df: pd.DataFrame,
    start_date,
    end_date,
) -> pd.DataFrame:
    """Filter transactions by an inclusive date range."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start > end:
        raise ValueError("Start date cannot be after end date.")

    result = df.copy()
    dates = _datetime_index(result["date"]).normalize()
    mask = (dates >= start.normalize()) & (dates <= end.normalize())
    return result.iloc[mask].copy()


def aggregate_sales_by_period(df: pd.DataFrame, grouping: str) -> pd.DataFrame:
    """Aggregate revenue and units sold by reporting period."""
    frequencies = {
        "Daily": None,
        "Weekly": "W-SUN",
        "Monthly": "M",
        "Yearly": "Y",
    }
    if grouping not in frequencies:
        raise ValueError(f"Unsupported grouping: {grouping}")

    result = df[["date", "price", "units_sold"]].copy()
    result["date"] = _datetime_index(result["date"]).to_numpy()
    result = result.dropna(subset=["date"])
    result["revenue"] = result["price"] * result["units_sold"]

    dates = _datetime_index(result["date"])
    if grouping == "Daily":
        result["period"] = dates.normalize().to_numpy()
    else:
        frequency = frequencies[grouping]
        assert frequency is not None
        result["period"] = dates.to_period(frequency).start_time.to_numpy()

    return (
        result.groupby("period", as_index=False)
        .agg(revenue=("revenue", "sum"), units_sold=("units_sold", "sum"))
        .sort_values("period")
        .reset_index(drop=True)
    )


def compare_weekday_weekend(df: pd.DataFrame) -> pd.DataFrame:
    """Compare weekday and weekend sales performance."""
    result = df[["date", "price", "units_sold"]].copy()
    result["date"] = _datetime_index(result["date"]).normalize().to_numpy()
    result = result.dropna(subset=["date"])

    day_numbers = _datetime_index(result["date"]).dayofweek
    result["day_type"] = [
        "Weekend" if day >= 5 else "Weekday" for day in day_numbers
    ]
    result["revenue"] = result["price"] * result["units_sold"]

    # Aggregate by calendar date before calculating daily averages.
    daily = (
        result.groupby(["date", "day_type"], as_index=False)
        .agg(revenue=("revenue", "sum"), units_sold=("units_sold", "sum"))
    )
    comparison = (
        daily.groupby("day_type", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            total_units=("units_sold", "sum"),
            days_with_sales=("date", "nunique"),
            avg_daily_revenue=("revenue", "mean"),
            avg_daily_units=("units_sold", "mean"),
        )
    )
    comparison["day_type"] = pd.Categorical(
        comparison["day_type"],
        categories=["Weekday", "Weekend"],
        ordered=True,
    )
    return comparison.sort_values("day_type").reset_index(drop=True)


def analyze_day_of_week(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze sales by day of week, Monday through Sunday."""
    result = df[["date", "price", "units_sold"]].copy()
    result["date"] = _datetime_index(result["date"]).normalize().to_numpy()
    result = result.dropna(subset=["date"])
    result["day_number"] = _datetime_index(result["date"]).dayofweek
    result["revenue"] = result["price"] * result["units_sold"]

    daily = (
        result.groupby(["date", "day_number"], as_index=False)
        .agg(revenue=("revenue", "sum"), units_sold=("units_sold", "sum"))
    )
    summary = (
        daily.groupby("day_number", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            total_units=("units_sold", "sum"),
            days_with_sales=("date", "nunique"),
            avg_daily_revenue=("revenue", "mean"),
            avg_daily_units=("units_sold", "mean"),
        )
    )
    day_names = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    summary["day_name"] = summary["day_number"].map(
        dict(enumerate(day_names))
    )
    return summary.sort_values("day_number").reset_index(drop=True)


def add_transaction_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Create transaction timestamps without inventing missing times."""
    result = df.copy()
    result["transaction_datetime"] = pd.NaT
    if "transaction_time" not in result.columns:
        return result

    dates = _datetime_index(result["date"])
    times = result["transaction_time"].astype("string").str.strip()
    valid_times = times.str.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", na=False
    )
    date_strings = pd.Series(dates.strftime("%Y-%m-%d"), index=result.index)
    combined = date_strings + " " + times
    result.loc[valid_times, "transaction_datetime"] = pd.to_datetime(
        combined.loc[valid_times], errors="coerce", format="mixed"
    )
    return result


def analyze_peak_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize sales performance by hour of day."""
    if "transaction_datetime" not in df.columns:
        raise ValueError(
            "Missing transaction_datetime column. "
            "Run add_transaction_datetime() first."
        )

    result = df.copy()
    result["transaction_datetime"] = _datetime_index(
        result["transaction_datetime"]
    ).to_numpy()
    result = result.dropna(subset=["transaction_datetime"])
    result["hour"] = _datetime_index(result["transaction_datetime"]).hour
    result["revenue"] = result["price"] * result["units_sold"]

    return (
        result.groupby("hour", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            total_units=("units_sold", "sum"),
            sales_rows=("hour", "size"),
        )
        .sort_values("hour")
        .reset_index(drop=True)
    )


def analyze_hourly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate total and average daily revenue by hour."""
    if "transaction_datetime" not in df.columns:
        raise ValueError(
            "Missing transaction_datetime column. "
            "Run add_transaction_datetime() first."
        )

    result = df.copy()
    result["transaction_datetime"] = _datetime_index(
        result["transaction_datetime"]
    ).to_numpy()
    result = result.dropna(subset=["transaction_datetime"])
    dates = _datetime_index(result["transaction_datetime"])
    result["date"] = dates.normalize().to_numpy()
    result["hour"] = dates.hour
    result["revenue"] = result["price"] * result["units_sold"]

    daily_hourly = (
        result.groupby(["date", "hour"], as_index=False)
        .agg(revenue=("revenue", "sum"))
    )
    hourly_summary = (
        daily_hourly.groupby("hour", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            days_with_sales=("date", "nunique"),
            avg_daily_revenue=("revenue", "mean"),
        )
    )
    return hourly_summary.sort_values("hour").reset_index(drop=True)