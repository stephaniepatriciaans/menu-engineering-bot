"""Chronological evaluation utilities for menu demand models"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    MIN_ELASTICITY_OBSERVATIONS,
    MIN_ELASTICITY_PRICE_POINTS,
    MIN_RELATIVE_PRICE_RANGE,
)


def chronological_split(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split observations by date without leaking future dates.

    All rows from the same calendar date stay in the same split.
    """
    if not 0 < train_fraction < 1:
        raise ValueError(
            "train_fraction must be strictly between 0 and 1."
        )

    if df.empty:
        raise ValueError("Cannot split an empty dataset.")

    if "date" not in df.columns:
        raise ValueError("Dataset must contain a date column.")

    work = df.copy()
    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    if work["date"].isna().any():
        raise ValueError(
            "Dataset contains missing or invalid dates."
        )

    work["date"] = work["date"].dt.normalize()

    dates = sorted(work["date"].unique())

    if len(dates) < 2:
        raise ValueError(
            "At least two distinct dates are required."
        )

    train_count = max(
        1,
        min(
            len(dates) - 1,
            int(len(dates) * train_fraction),
        ),
    )

    cutoff = dates[train_count - 1]

    train = work.loc[
        work["date"] <= cutoff
    ].copy()

    test = work.loc[
        work["date"] > cutoff
    ].copy()

    return train, test


def calculate_forecast_metrics(
    actual: Sequence[float] | np.ndarray,
    predicted: Sequence[float] | np.ndarray,
) -> dict[str, float | None]:
    """Calculate MAE, RMSE, and WAPE for demand forecasts.

    WAPE is unavailable when total actual demand is zero.
    Invalid or non-finite predictions are rejected.
    """
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)

    if actual_arr.ndim != 1 or predicted_arr.ndim != 1:
        raise ValueError("Forecast inputs must be one-dimensional.")

    if len(actual_arr) == 0:
        raise ValueError("Forecast inputs cannot be empty.")

    if len(actual_arr) != len(predicted_arr):
        raise ValueError(
            "Actual and predicted arrays must have equal length."
        )

    if not (
        np.isfinite(actual_arr).all()
        and np.isfinite(predicted_arr).all()
    ):
        raise ValueError(
            "Forecast inputs must contain only finite numbers."
        )

    if (actual_arr < 0).any() or (predicted_arr < 0).any():
        raise ValueError(
            "Demand quantities cannot be negative."
        )

    errors = actual_arr - predicted_arr

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    total_actual = float(np.sum(np.abs(actual_arr)))

    wape = (
        float(np.sum(np.abs(errors)) / total_actual * 100)
        if total_actual > 0
        else None
    )

    return {
        "mae": mae,
        "rmse": rmse,
        "wape": wape,
    }


def predict_historical_average(
    train_units: Sequence[float] | np.ndarray,
    n_predictions: int,
) -> np.ndarray:
    """Predict constant demand using the training-period average.

    The baseline never accesses test-set demand.
    """
    train = np.asarray(train_units, dtype=float)

    if train.ndim != 1 or len(train) == 0:
        raise ValueError(
            "Training demand must be a non-empty 1D array."
        )

    if not np.isfinite(train).all():
        raise ValueError(
            "Training demand must contain only finite values."
        )

    if (train < 0).any():
        raise ValueError(
            "Training demand cannot be negative."
        )

    if n_predictions < 1:
        raise ValueError(
            "n_predictions must be at least 1."
        )

    mean_demand = float(np.mean(train))

    return np.full(
        n_predictions,
        mean_demand,
        dtype=float,
    )


def evaluate_historical_average(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> dict[str, object]:
    """Evaluate historical-average demand on later recorded dates.

    Expects one item with one row per recorded sales date.
    This does not infer zero sales for absent dates.
    """
    required = {"date", "item", "units_sold"}

    if not required.issubset(df.columns):
        raise ValueError(
            "Dataset must contain date, item, and units_sold."
        )

    items = df["item"].dropna().unique()

    if len(items) != 1 or df["item"].isna().any():
        raise ValueError(
            "Evaluate one item at a time."
        )

    work = df.copy()
    work["units_sold"] = pd.to_numeric(
        work["units_sold"],
        errors="coerce",
    )

    quantities = work["units_sold"].to_numpy(dtype=float)

    if not np.isfinite(quantities).all():
        raise ValueError("Demand contains non-finite values.")

    if (quantities < 0).any():
        raise ValueError("Demand cannot be negative.")

    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    if work["date"].isna().any():
        raise ValueError("Invalid dates.")

    work["date"] = work["date"].dt.normalize()

    # Aggregate multiple transactions for the same item/date.
    daily = (
        work.groupby(
            ["item", "date"],
            as_index=False,
        )
        .agg(
            units_sold=("units_sold", "sum")
        )
    )

    train, test = chronological_split(
        daily,
        train_fraction=train_fraction,
    )

    predictions = predict_historical_average(
        train["units_sold"].to_numpy(dtype=float),
        len(test),
    )

    metrics = calculate_forecast_metrics(
        test["units_sold"].to_numpy(dtype=float),
        predictions,
    )

    return {
        "item": str(items[0]),
        "train_days": len(train),
        "test_days": len(test),
        "train_end": str(train["date"].max().date()),
        "test_start": str(test["date"].min().date()),
        "predictions": predictions.tolist(),
        "actual": test["units_sold"].tolist(),
        "metrics": metrics,
    }


def predict_elasticity_demand(
    train_prices: Sequence[float] | np.ndarray,
    train_units: Sequence[float] | np.ndarray,
    future_prices: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Fit a log-log demand model using training data only.

    Predictions are conditional on supplied prices.
    This is an exploratory association model, not causal
    evidence that changing prices will change demand.
    """
    prices = np.asarray(train_prices, dtype=float)
    units = np.asarray(train_units, dtype=float)
    future = np.asarray(future_prices, dtype=float)

    if any(
        arr.ndim != 1
        for arr in (prices, units, future)
    ):
        raise ValueError("Inputs must be one-dimensional.")

    if (
        len(prices) < 2
        or len(prices) != len(units)
        or len(future) == 0
    ):
        raise ValueError(
            "At least two matching training observations "
            "and one future price are required."
        )

    if not all(
        np.isfinite(arr).all()
        for arr in (prices, units, future)
    ):
        raise ValueError("Inputs must contain finite values.")

    if (
        (prices <= 0).any()
        or (units <= 0).any()
        or (future <= 0).any()
    ):
        raise ValueError(
            "Prices and training demand must be positive."
        )

    if len(np.unique(prices)) < 2:
        raise ValueError(
            "At least two distinct training prices are required."
        )
    
    price_points = len(np.unique(prices))
    relative_price_range = (
        float(np.max(prices)) - float(np.min(prices))
    ) / float(np.min(prices))

    sufficient_evidence = (
        len(prices) >= MIN_ELASTICITY_OBSERVATIONS
        and price_points >= MIN_ELASTICITY_PRICE_POINTS
        and relative_price_range >= MIN_RELATIVE_PRICE_RANGE
    )

    if not sufficient_evidence:
        raise ValueError(
            "Insufficient historical evidence for elasticity "
            "forecasting. More observations, distinct prices, "
            "or price variation are required."
        )

    log_prices = np.log(prices)
    log_units = np.log(units)

    slope, intercept = np.polyfit(
        log_prices,
        log_units,
        1,
    )

    with np.errstate(over="raise", invalid="raise"):
        try:
            predictions = np.exp(
                intercept + slope * np.log(future)
            )
        except FloatingPointError as exc:
            raise ValueError(
                "Forecast produced non-finite values."
            ) from exc

    if not np.isfinite(predictions).all():
        raise ValueError(
            "Forecast produced non-finite values."
        )

    return np.asarray(predictions, dtype=float)


def compare_demand_forecasts(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> dict[str, object]:
    """Compare baseline and elasticity forecasts on future dates.

    Evaluates one item at a time, with one selling price per date.
    Absent dates are not assumed to represent zero sales.

    Test-period prices are known inputs, but test-period sales
    quantities are never used when fitting either model.
    """
    required = {"date", "item", "price", "units_sold"}

    if not required.issubset(df.columns):
        raise ValueError(
            "Dataset must contain date, item, price, and units_sold."
        )

    if df.empty:
        raise ValueError("Cannot evaluate an empty dataset.")

    items = df["item"].dropna().unique()

    if len(items) != 1 or df["item"].isna().any():
        raise ValueError("Evaluate one item at a time.")

    work = df.copy()

    work["date"] = pd.to_datetime(
        work["date"],
        errors="coerce",
    )

    if work["date"].isna().any():
        raise ValueError("Invalid dates.")

    work["date"] = work["date"].dt.normalize()

    for column in ["price", "units_sold"]:
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        )

        values = work[column].to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                f"{column} must contain finite values."
            )

    if (work["price"] <= 0).any():
        raise ValueError("Prices must be positive.")

    if (work["units_sold"] < 0).any():
        raise ValueError("Demand cannot be negative.")

    # Avoid treating different prices on the same date as
    # one arbitrary daily price.
    price_counts = work.groupby("date")["price"].nunique()

    if (price_counts > 1).any():
        raise ValueError(
            "Multiple prices on the same date are not "
            "supported by this evaluation."
        )

    # Sum transactions at the same daily selling price.
    daily = (
        work.groupby("date", as_index=False)
        .agg(
            price=("price", "first"),
            units_sold=("units_sold", "sum"),
        )
    )

    train, test = chronological_split(
        daily,
        train_fraction=train_fraction,
    )

    train_prices = train["price"].to_numpy(dtype=float)
    train_units = train["units_sold"].to_numpy(dtype=float)
    test_prices = test["price"].to_numpy(dtype=float)
    test_units = test["units_sold"].to_numpy(dtype=float)

    baseline_predictions = predict_historical_average(
        train_units,
        n_predictions=len(test),
    )

    elasticity_predictions = predict_elasticity_demand(
        train_prices,
        train_units,
        test_prices,
    )

    baseline_metrics = calculate_forecast_metrics(
        test_units,
        baseline_predictions,
    )

    elasticity_metrics = calculate_forecast_metrics(
        test_units,
        elasticity_predictions,
    )

    train_min_price = float(np.min(train_prices))
    train_max_price = float(np.max(train_prices))

    extrapolation = bool(
        (test_prices < train_min_price).any()
        or (test_prices > train_max_price).any()
    )

    baseline_mae = baseline_metrics["mae"]
    elasticity_mae = elasticity_metrics["mae"]

    assert baseline_mae is not None
    assert elasticity_mae is not None

    return {
        "item": str(items[0]),
        "train_days": len(train),
        "test_days": len(test),
        "train_end": str(train["date"].max().date()),
        "test_start": str(test["date"].min().date()),
        "actual": test_units.tolist(),
        "test_prices": test_prices.tolist(),
        "baseline_predictions": baseline_predictions.tolist(),
        "elasticity_predictions": elasticity_predictions.tolist(),
        "baseline_metrics": baseline_metrics,
        "elasticity_metrics": elasticity_metrics,
        "elasticity_lower_mae": bool(
            elasticity_mae < baseline_mae
        ),
        "price_extrapolation": extrapolation,
    }
    

def evaluate_all_items(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> pd.DataFrame:
    """Evaluate each item separately and report unsupported items.

    No aggregate model accuracy is claimed when an item cannot be
    evaluated reliably.
    """
    columns = [
        "item",
        "status",
        "reason",
        "train_days",
        "test_days",
        "baseline_mae",
        "elasticity_mae",
        "baseline_rmse",
        "elasticity_rmse",
        "baseline_wape",
        "elasticity_wape",
        "elasticity_lower_mae",
        "price_extrapolation",
    ]

    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    if "item" not in df.columns:
        raise ValueError("Dataset must contain an item column.")

    records: list[dict[str, object]] = []

    for item, item_df in df.groupby("item", sort=False):
        try:
            result = compare_demand_forecasts(
                item_df,
                train_fraction=train_fraction,
            )

            baseline = result["baseline_metrics"]
            elasticity = result["elasticity_metrics"]

            assert isinstance(baseline, dict)
            assert isinstance(elasticity, dict)

            records.append({
                "item": str(item),
                "status": "evaluated",
                "reason": "",
                "train_days": result["train_days"],
                "test_days": result["test_days"],
                "baseline_mae": baseline["mae"],
                "elasticity_mae": elasticity["mae"],
                "baseline_rmse": baseline["rmse"],
                "elasticity_rmse": elasticity["rmse"],
                "baseline_wape": baseline["wape"],
                "elasticity_wape": elasticity["wape"],
                "elasticity_lower_mae": result["elasticity_lower_mae"],
                "price_extrapolation": result["price_extrapolation"],
            })

        except ValueError as exc:
            records.append({
                "item": str(item),
                "status": "insufficient_evidence",
                "reason": str(exc),
                "train_days": None,
                "test_days": None,
                "baseline_mae": None,
                "elasticity_mae": None,
                "baseline_rmse": None,
                "elasticity_rmse": None,
                "baseline_wape": None,
                "elasticity_wape": None,
                "elasticity_lower_mae": None,
                "price_extrapolation": None,
            })

    return pd.DataFrame(records, columns=columns)



def summarize_model_coverage(
    evaluation_df: pd.DataFrame,
) -> dict[str, int | float | None]:
    """Summarize evaluation coverage without overstating accuracy.

    Only evaluated items count toward model comparisons.
    A zero evaluated-item count produces unavailable rates.
    """
    if evaluation_df is None or evaluation_df.empty:
        return {
            "total_items": 0,
            "evaluated_items": 0,
            "insufficient_evidence_items": 0,
            "evaluation_coverage_pct": None,
            "elasticity_better_items": 0,
            "elasticity_better_pct": None,
        }

    required = {
        "item",
        "status",
        "elasticity_lower_mae",
    }

    if not required.issubset(evaluation_df.columns):
        raise ValueError(
            "Evaluation results are missing required columns."
        )

    total = len(evaluation_df)

    evaluated = evaluation_df[
        evaluation_df["status"] == "evaluated"
    ]

    n_evaluated = len(evaluated)
    n_insufficient = int(
        (evaluation_df["status"] == "insufficient_evidence").sum()
    )

    n_better = int(
        evaluated["elasticity_lower_mae"]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    coverage_pct = (
        round(n_evaluated / total * 100, 1)
        if total > 0
        else None
    )

    better_pct = (
        round(n_better / n_evaluated * 100, 1)
        if n_evaluated > 0
        else None
    )

    return {
        "total_items": total,
        "evaluated_items": n_evaluated,
        "insufficient_evidence_items": n_insufficient,
        "evaluation_coverage_pct": coverage_pct,
        "elasticity_better_items": n_better,
        "elasticity_better_pct": better_pct,
    }


def build_model_evaluation_report(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> dict[str, object]:
    """Build a reproducible model evaluation report.

    Report metrics only for eligible items.
    Do not claim accuracy for items without sufficient evidence.
    """
    item_results = evaluate_all_items(
        df,
        train_fraction=train_fraction,
    )

    coverage = summarize_model_coverage(item_results)

    evaluated = item_results.loc[
        item_results["status"] == "evaluated"
    ]

    return {
        "methodology": {
            "split_method": "chronological",
            "train_fraction": train_fraction,
            "baseline": "historical_average",
            "candidate": "log_log_elasticity",
            "metrics": ["MAE", "RMSE", "WAPE"],
            "target": "daily_item_units_on_recorded_dates",
            "future_prices": "observed_test_period_prices",
            "missing_dates": "not_assumed_zero_sales",
            "causal_interpretation": False,
        },
        "coverage": coverage,
        "items": item_results.to_dict(orient="records"),
        "evaluated_items": len(evaluated),
    }


def export_model_evaluation_report(
    report: dict[str, object],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Export methodology/coverage as JSON and item results as CSV.

    The report contains aggregate item-level metrics, not original
    transaction records. Output paths are controlled by the caller.
    """
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "model_evaluation_report.json"
    csv_path = destination / "model_evaluation_items.csv"

    methodology = report.get("methodology")
    coverage = report.get("coverage")
    items = report.get("items")

    # Missing sections preserve the existing error messages.
    if methodology is None:
        raise ValueError(
            "Report methodology is missing or invalid."
        )

    if coverage is None:
        raise ValueError(
            "Report coverage is missing or invalid."
        )

    if items is None:
        raise ValueError(
            "Report item results are missing or invalid."
        )

    # Incorrect types raise TypeError, as recommended by Ruff.
    if not isinstance(methodology, dict):
        raise TypeError(
            "Report methodology must be a dictionary."
        )

    if not isinstance(coverage, dict):
        raise TypeError(
            "Report coverage must be a dictionary."
        )

    if not isinstance(items, list):
        raise TypeError(
            "Report item results must be a list."
        )


    # Validate the report before writing either output.
    json_content = json.dumps(
        {
            "methodology": methodology,
            "coverage": coverage,
            "evaluated_items": report.get("evaluated_items"),
        },
        indent=2,
        allow_nan=False,
    )

    items_df = pd.DataFrame(items)
    csv_content = items_df.to_csv(index=False)

    json_path.write_text(json_content, encoding="utf-8")
    csv_path.write_text(csv_content, encoding="utf-8")

    return json_path, csv_path
