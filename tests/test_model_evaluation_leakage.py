"""Regression tests for chronological forecast evaluation."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_evaluation import (
    chronological_split,
    evaluate_historical_average,
)


def make_sales_data():
    """Create deterministic daily sales observations."""
    return pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=20,
            freq="D",
        ),
        "item": ["Latte"] * 20,
        "price": [5.0] * 20,
        "units_sold": [
            10.0 + (day % 5)
            for day in range(20)
        ],
    })


@pytest.mark.parametrize(
    "train_fraction",
    [0.60, 0.70, 0.80],
)
def test_training_dates_precede_test_dates(train_fraction):
    """No calendar date may appear in both splits."""
    df = make_sales_data()

    train, test = chronological_split(
        df,
        train_fraction=train_fraction,
    )

    assert not train.empty
    assert not test.empty

    assert train["date"].max() < test["date"].min()

    assert set(train["date"]).isdisjoint(
        set(test["date"])
    )


def test_row_order_does_not_change_split():
    """Shuffling input rows must not change date membership."""
    df = make_sales_data()
    shuffled = df.sample(frac=1, random_state=42)

    train_a, test_a = chronological_split(df)
    train_b, test_b = chronological_split(shuffled)

    assert set(train_a["date"]) == set(train_b["date"])
    assert set(test_a["date"]) == set(test_b["date"])


def test_future_sales_do_not_change_baseline_predictions():
    """Held-out demand must not influence baseline fitting."""
    original = make_sales_data()

    first = evaluate_historical_average(
        original,
        train_fraction=0.70,
    )

    modified = original.copy()

    # Change only the last six days (the test period).
    modified.loc[
        modified["date"] >= pd.Timestamp("2026-01-15"),
        "units_sold",
    ] = 999.0

    second = evaluate_historical_average(
        modified,
        train_fraction=0.70,
    )

    first_predictions = np.asarray(
        first["predictions"],
        dtype=float,
    )
    second_predictions = np.asarray(
        second["predictions"],
        dtype=float,
    )

    np.testing.assert_allclose(
        first_predictions,
        second_predictions,
    )

    # Actual test values should change.
    assert first["actual"] != second["actual"]


def test_missing_dates_are_not_imputed_as_zero():
    """Evaluation must use recorded dates only."""
    df = make_sales_data()

    df = df.loc[
        ~df["date"].isin([
            pd.Timestamp("2026-01-05"),
            pd.Timestamp("2026-01-10"),
        ])
    ].copy()

    result = evaluate_historical_average(
        df,
        train_fraction=0.70,
    )

    
    train_days = result["train_days"]
    test_days = result["test_days"]

    assert isinstance(train_days, int)
    assert isinstance(test_days, int)

    assert train_days + test_days == 18



def test_invalid_dates_are_rejected():
    """Invalid dates must not enter chronological splitting."""
    df = make_sales_data()

    # Convert dates to object dtype so we can simulate
    # a malformed date from a CSV or POS export.
    df["date"] = df["date"].astype(object)
    df.loc[0, "date"] = "not-a-date"

    with pytest.raises(
        ValueError,
        match="missing or invalid dates",
    ):
        chronological_split(df)


def test_same_day_records_remain_in_one_split():
    """Multiple transactions on one date cannot cross the cutoff."""
    df = make_sales_data()

    duplicate = df.iloc[[10]].copy()
    combined = pd.concat(
        [df, duplicate],
        ignore_index=True,
    )

    train, test = chronological_split(
        combined,
        train_fraction=0.70,
    )

    # No calendar date appears in both splits.
    assert set(train["date"]).isdisjoint(
        set(test["date"])
    )

    # Every original and duplicate row is preserved.
    assert len(train) + len(test) == len(combined)

    # Both transactions from January 11 must stay together.
    target_date = pd.Timestamp("2026-01-11")

    train_count = (train["date"] == target_date).sum()
    test_count = (test["date"] == target_date).sum()

    assert (train_count, test_count) in {
        (2, 0),
        (0, 2),
    }


def test_future_sales_do_not_change_elasticity_predictions():
    """Changing test demand must not affect fitted forecasts."""
    from model_evaluation import compare_demand_forecasts

    prices = (
        [5.0, 5.5, 6.0, 6.5, 7.0] * 6
    )

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=len(prices),
        ),
        "item": ["Latte"] * len(prices),
        "price": prices,
        "units_sold": [
            100.0 * (price / 5.0) ** -1.5
            for price in prices
        ],
    })

    original = compare_demand_forecasts(
        df,
        train_fraction=0.70,
    )

    modified = df.copy()

    # Modify only dates in the chronological holdout.
    _train, test = chronological_split(
        df,
        train_fraction=0.70,
    )

    modified.loc[
        modified["date"].isin(test["date"]),
        "units_sold",
    ] = 999.0

    updated = compare_demand_forecasts(
        modified,
        train_fraction=0.70,
    )

    np.testing.assert_allclose(
        np.asarray(
            original["elasticity_predictions"],
            dtype=float,
        ),
        np.asarray(
            updated["elasticity_predictions"],
            dtype=float,
        ),
    )

    np.testing.assert_allclose(
        np.asarray(
            original["baseline_predictions"],
            dtype=float,
        ),
        np.asarray(
            updated["baseline_predictions"],
            dtype=float,
        ),
    )

    assert original["actual"] != updated["actual"]


def test_holdout_dates_align_with_actual_and_predictions():
    """Holdout dates, actual demand, and predictions must align."""
    df = make_sales_data()

    result = evaluate_historical_average(
        df,
        train_fraction=0.70,
    )

    dates = result["test_dates"]
    actual = result["actual"]
    predictions = result["predictions"]

    assert isinstance(dates, list)
    assert isinstance(actual, list)
    assert isinstance(predictions, list)

    # All three sequences must have matching lengths.
    assert len(dates) == len(actual) == len(predictions)

    # Dates must be chronological and belong to the holdout.
    parsed_dates = pd.to_datetime(dates)

    assert parsed_dates.is_monotonic_increasing
    assert len(dates) == 6

    # Verify alignment against the original recorded sales.
    expected = (
        df.set_index("date")
        .loc[parsed_dates, "units_sold"]
        .to_numpy(dtype=float)
    )

    np.testing.assert_allclose(
        np.asarray(actual, dtype=float),
        expected,
    )

    # Predictions must be based on training demand.
    expected_mean = df.iloc[:14]["units_sold"].mean()

    np.testing.assert_allclose(
        np.asarray(predictions, dtype=float),
        np.full(6, expected_mean),
    )
