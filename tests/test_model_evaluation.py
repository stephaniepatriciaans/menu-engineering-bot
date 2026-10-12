"""Tests for chronological model evaluation"""

import sys
from pathlib import Path

import pandas as pd
import pytest
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_evaluation import (
    chronological_split,
    calculate_forecast_metrics,
    predict_historical_average,
    evaluate_historical_average,
    predict_elasticity_demand,
    compare_demand_forecasts,
    evaluate_all_items,
    summarize_model_coverage,
    build_model_evaluation_report,
    export_model_evaluation_report,
)

from config import (
    MIN_ELASTICITY_OBSERVATIONS,
    MIN_ELASTICITY_PRICE_POINTS,
    MIN_RELATIVE_PRICE_RANGE,
)


def sufficient_training_prices() -> list[float]:
    """Create prices that meet the configured evidence thresholds."""
    n = max(
        12,
        MIN_ELASTICITY_OBSERVATIONS,
        MIN_ELASTICITY_PRICE_POINTS,
    )

    relative_range = max(
        1.0,
        MIN_RELATIVE_PRICE_RANGE * 2,
    )

    return [
        4.0 * (1.0 + relative_range * i / (n - 1))
        for i in range(n)
    ]


def test_chronological_split_prevents_future_leakage():
    """Training dates must always precede testing dates."""

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-05",
            "2026-01-01",
            "2026-01-03",
            "2026-01-02",
            "2026-01-04",
        ]),
        "item": ["Latte"] * 5,
        "units_sold": [10, 20, 15, 12, 9],
    })

    train, test = chronological_split(
        df,
        train_fraction=0.6,
    )

    assert len(train) == 3
    assert len(test) == 2

    assert train["date"].max() < test["date"].min()

    assert set(train["date"]).isdisjoint(
        set(test["date"])
    )


def test_chronological_split_keeps_same_date_together():
    """Transactions from the same date must not cross splits."""

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-02",
            "2026-01-03",
            "2026-01-03",
        ]),
        "item": [
            "Latte", "Tea",
            "Latte", "Tea",
            "Latte", "Tea",
        ],
        "units_sold": [10, 5, 12, 6, 9, 4],
    })

    train, test = chronological_split(
        df,
        train_fraction=0.67,
    )

    assert len(train) == 4
    assert len(test) == 2

    assert train["date"].max() < test["date"].min()

    assert set(train["date"]).isdisjoint(
        set(test["date"])
    )


def test_chronological_split_rejects_one_date():
    """At least two distinct dates are required."""

    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01"],
        "item": ["Latte", "Tea"],
        "units_sold": [10, 5],
    })

    with pytest.raises(
        ValueError,
        match="At least two distinct dates",
    ):
        chronological_split(df)


def test_forecast_metrics_known_values():
    """Metrics should match independently calculated results."""
    actual = [10.0, 20.0, 30.0]
    predicted = [12.0, 18.0, 33.0]

    metrics = calculate_forecast_metrics(actual, predicted)

    # Absolute errors: 2, 2, 3.
    assert metrics["mae"] == pytest.approx(7 / 3)

    # Squared errors: 4, 4, 9.
    assert metrics["rmse"] == pytest.approx((17 / 3) ** 0.5)

    # WAPE: (2 + 2 + 3) / (10 + 20 + 30) * 100.
    assert metrics["wape"] == pytest.approx(7 / 60 * 100)


def test_forecast_metrics_zero_actual_demand():
    """WAPE should be unavailable when total demand is zero."""
    metrics = calculate_forecast_metrics(
        [0.0, 0.0],
        [2.0, 3.0],
    )

    assert metrics["mae"] == pytest.approx(2.5)
    assert metrics["rmse"] == pytest.approx((13 / 2) ** 0.5)
    assert metrics["wape"] is None


def test_forecast_metrics_rejects_invalid_predictions():
    """Invalid forecasts must not generate misleading scores."""
    with pytest.raises(ValueError):
        calculate_forecast_metrics(
            [10.0, 20.0],
            [float("inf"), 18.0],
        )

    with pytest.raises(ValueError):
        calculate_forecast_metrics(
            [10.0, 20.0],
            [12.0],
        )

    with pytest.raises(ValueError):
        calculate_forecast_metrics(
            [10.0, 20.0],
            [-1.0, 18.0],
        )


def test_historical_average_baseline_known_values():
    """The baseline predicts the training mean."""

    predictions = predict_historical_average(
        train_units=[10.0, 12.0, 14.0],
        n_predictions=2,
    )

    assert predictions.tolist() == pytest.approx(
        [12.0, 12.0]
    )


def test_historical_average_baseline_does_not_use_test_values():
    """Changing future sales must not change baseline predictions."""

    training = [10.0, 20.0, 30.0]

    first_predictions = predict_historical_average(
        training,
        n_predictions=3,
    )

    # These are hypothetical future actual values.
    # Neither should be provided to the baseline.
    future_a = [5.0, 10.0, 15.0]
    future_b = [100.0, 200.0, 300.0]

    assert future_a != future_b

    second_predictions = predict_historical_average(
        training,
        n_predictions=3,
    )

    assert first_predictions.tolist() == pytest.approx(
        second_predictions.tolist()
    )

    assert first_predictions.tolist() == pytest.approx(
        [20.0, 20.0, 20.0]
    )


def test_historical_average_baseline_rejects_invalid_inputs():
    """Invalid training demand and prediction counts are rejected."""

    with pytest.raises(ValueError):
        predict_historical_average([], 2)

    with pytest.raises(ValueError):
        predict_historical_average(
            [10.0, float("inf")],
            2,
        )

    with pytest.raises(ValueError):
        predict_historical_average(
            [10.0, -2.0],
            2,
        )

    with pytest.raises(ValueError):
        predict_historical_average(
            [10.0, 20.0],
            0,
        )


def test_evaluate_historical_average_on_future_dates():
    """Baseline metrics must use later dates as test observations."""

    df = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
        ],
        "item": ["Latte"] * 5,
        "units_sold": [4.0, 6.0, 12.0, 14.0, 20.0],
    })

    result = evaluate_historical_average(
        df,
        train_fraction=0.5,
    )

    # Daily demand = 10, 12, 14, 20.
    # Train = 10, 12. Mean = 11.
    # Test = 14, 20.
    assert result["train_days"] == 2
    assert result["test_days"] == 2
    assert result["predictions"] == pytest.approx(
        [11.0, 11.0]
    )
    assert result["actual"] == pytest.approx(
        [14.0, 20.0]
    )

    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["mae"] == pytest.approx(6.0)
    assert metrics["rmse"] == pytest.approx(
        (45.0) ** 0.5
    )
    assert metrics["wape"] == pytest.approx(
        12.0 / 34.0 * 100
    )


def test_evaluate_historical_average_rejects_multiple_items():
    """The initial evaluator must not mix demand from different items."""

    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "item": ["Latte", "Tea"],
        "units_sold": [10.0, 20.0],
    })

    with pytest.raises(
        ValueError,
        match="Evaluate one item at a time",
    ):
        evaluate_historical_average(df)



def test_elasticity_forecast_known_relationship():
    """Recover demand generated from a known log-log model."""

    prices = sufficient_training_prices()

    units = [
        100.0 * (price / 5.0) ** -1.5
        for price in prices
    ]

    predictions = predict_elasticity_demand(
        train_prices=prices,
        train_units=units,
        future_prices=[5.0, 10.0],
    )

    assert predictions.tolist() == pytest.approx([
        100.0,
        100.0 * (10.0 / 5.0) ** -1.5,
    ])


def test_elasticity_forecast_uses_only_training_data():
    """Predictions depend only on training data and supplied prices."""

    train_prices = sufficient_training_prices()

    train_units = [
        100.0 * (price / 5.0) ** -1.2
        for price in train_prices
    ]

    future_prices = [5.5, 6.5]

    first = predict_elasticity_demand(
        train_prices,
        train_units,
        future_prices,
    )

    second = predict_elasticity_demand(
        train_prices,
        train_units,
        future_prices,
    )

    assert first.tolist() == pytest.approx(
        second.tolist()
    )

    assert (first > 0).all()



def test_elasticity_forecast_rejects_invalid_training_data():
    """Insufficient variation and invalid observations are rejected."""

    with pytest.raises(ValueError):
        predict_elasticity_demand(
            [5.0, 5.0, 5.0],
            [10.0, 12.0, 14.0],
            [6.0],
        )

    with pytest.raises(ValueError):
        predict_elasticity_demand(
            [4.0, 5.0],
            [10.0, 0.0],
            [6.0],
        )

    with pytest.raises(ValueError):
        predict_elasticity_demand(
            [4.0, float("inf")],
            [10.0, 12.0],
            [6.0],
        )

    with pytest.raises(ValueError):
        predict_elasticity_demand(
            [4.0, 5.0],
            [10.0, 12.0],
            [-1.0],
        )



def test_compare_forecasts_known_elasticity_relationship():
    """Compare both models on the same future sales dates."""

    train_prices = sufficient_training_prices()
    n_train = len(train_prices)

    test_prices = [5.5, 6.5]
    prices = train_prices + test_prices

    units = [
        100.0 * (price / 5.0) ** -1.5
        for price in prices
    ]

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=len(prices),
        ),
        "item": ["Latte"] * len(prices),
        "price": prices,
        "units_sold": units,
    })

    result = compare_demand_forecasts(
        df,
        train_fraction=(n_train + 0.5) / len(prices),
    )

    assert result["train_days"] == n_train
    assert result["test_days"] == 2

    assert result["actual"] == pytest.approx(
        units[n_train:]
    )

    assert result["elasticity_predictions"] == (
        pytest.approx(units[n_train:])
    )

    baseline_metrics = result["baseline_metrics"]
    elasticity_metrics = result["elasticity_metrics"]

    assert isinstance(baseline_metrics, dict)
    assert isinstance(elasticity_metrics, dict)

    assert elasticity_metrics["mae"] == pytest.approx(
        0.0,
        abs=1e-8,
    )

    assert elasticity_metrics["rmse"] == pytest.approx(
        0.0,
        abs=1e-8,
    )

    assert baseline_metrics["mae"] > (
        elasticity_metrics["mae"]
    )

    assert result["elasticity_lower_mae"] is True
    assert result["price_extrapolation"] is False


def test_compare_forecasts_rejects_multiple_daily_prices():
    """Different prices on one date require more careful modeling."""

    df = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
        ],
        "item": ["Latte"] * 4,
        "price": [5.0, 6.0, 5.0, 6.0],
        "units_sold": [10.0, 8.0, 12.0, 9.0],
    })

    with pytest.raises(
        ValueError,
        match="Multiple prices on the same date",
    ):
        compare_demand_forecasts(df)



def test_compare_forecasts_flags_price_extrapolation():
    """Flag test prices beyond the training price range."""

    train_prices = sufficient_training_prices()
    n_train = len(train_prices)

    future_price = max(train_prices) * 1.5
    prices = train_prices + [future_price]

    units = [
        100.0 * (price / 5.0) ** -1.2
        for price in prices
    ]

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=len(prices),
        ),
        "item": ["Latte"] * len(prices),
        "price": prices,
        "units_sold": units,
    })

    result = compare_demand_forecasts(
        df,
        train_fraction=(n_train + 0.5) / len(prices),
    )

    assert result["train_days"] == n_train
    assert result["test_days"] == 1

    assert result["test_prices"] == pytest.approx(
        [future_price]
    )

    assert result["price_extrapolation"] is True

    baseline_predictions = result["baseline_predictions"]
    elasticity_predictions = result["elasticity_predictions"]

    assert isinstance(baseline_predictions, list)
    assert isinstance(elasticity_predictions, list)

    assert len(baseline_predictions) == 1
    assert len(elasticity_predictions) == 1


def test_elasticity_forecast_rejects_zero_training_demand():
    """Zero demand cannot be used directly in a log-log model."""

    with pytest.raises(
        ValueError,
        match="Prices and training demand must be positive",
    ):
        predict_elasticity_demand(
            train_prices=[4.0, 5.0, 6.0],
            train_units=[10.0, 0.0, 8.0],
            future_prices=[5.5],
        )


def test_comparison_rejects_zero_training_demand():
    """Do not silently discard zero-sales dates."""

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=5,
        ),
        "item": ["Latte"] * 5,
        "price": [4.0, 5.0, 6.0, 7.0, 5.5],
        "units_sold": [10.0, 0.0, 8.0, 7.0, 9.0],
    })

    with pytest.raises(
        ValueError,
        match="Prices and training demand must be positive",
    ):
        compare_demand_forecasts(
            df,
            train_fraction=0.8,
        )



def test_elasticity_forecast_requires_sufficient_observations():
    """Two points should not justify a historical demand model."""

    with pytest.raises(
        ValueError,
        match="Insufficient historical evidence",
    ):
        predict_elasticity_demand(
            train_prices=[4.0, 5.0],
            train_units=[120.0, 100.0],
            future_prices=[5.5],
        )


def test_comparison_rejects_insufficient_training_evidence():
    """A small dataset must not produce misleading model metrics."""

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=5,
        ),
        "item": ["Latte"] * 5,
        "price": [4.0, 5.0, 6.0, 7.0, 5.5],
        "units_sold": [120.0, 100.0, 85.0, 75.0, 90.0],
    })

    with pytest.raises(
        ValueError,
        match="Insufficient historical evidence",
    ):
        compare_demand_forecasts(
            df,
            train_fraction=0.8,
        )


def test_compare_forecasts_with_noisy_demand():
    """Both models should produce valid metrics with noisy sales."""

    train_prices = sufficient_training_prices()
    n_train = len(train_prices)

    test_prices = [5.5, 6.5, 7.0]
    prices = train_prices + test_prices

    # Deterministic sales variation, not a perfect price-demand curve.
    noise = [1.08, 0.94, 1.03, 0.97, 1.05]

    units = [
        100.0
        * (price / 5.0) ** -1.3
        * noise[i % len(noise)]
        for i, price in enumerate(prices)
    ]

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=len(prices),
        ),
        "item": ["Latte"] * len(prices),
        "price": prices,
        "units_sold": units,
    })

    result = compare_demand_forecasts(
        df,
        train_fraction=(n_train + 0.5) / len(prices),
    )

    assert result["train_days"] == n_train
    assert result["test_days"] == len(test_prices)

    baseline_metrics = result["baseline_metrics"]
    elasticity_metrics = result["elasticity_metrics"]

    assert isinstance(baseline_metrics, dict)
    assert isinstance(elasticity_metrics, dict)

    for metrics in (baseline_metrics, elasticity_metrics):
        assert metrics["mae"] is not None
        assert metrics["rmse"] is not None
        assert metrics["wape"] is not None

        assert metrics["mae"] >= 0
        assert metrics["rmse"] >= 0
        assert metrics["wape"] >= 0

    assert result["price_extrapolation"] is False


def test_evaluate_all_items_reports_eligible_and_ineligible_items():
    """Unsupported products must not block evaluation of other items."""

    prices = sufficient_training_prices() + [5.5, 6.5]
    n = len(prices)

    latte = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=n),
        "item": ["Latte"] * n,
        "price": prices,
        "units_sold": [
            100.0 * (price / 5.0) ** -1.5
            for price in prices
        ],
    })

    tea = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=n),
        "item": ["Tea"] * n,
        "price": [3.0] * n,
        "units_sold": [12.0] * n,
    })

    combined = pd.concat(
        [latte, tea],
        ignore_index=True,
    )

    train_fraction = (
        len(prices) - 1.5
    ) / len(prices)

    results = evaluate_all_items(
        combined,
        train_fraction=train_fraction,
    )

    by_item = results.set_index("item").to_dict(
        orient="index"
    )

    assert by_item["Latte"]["status"] == "evaluated"
    assert by_item["Tea"]["status"] == "insufficient_evidence"

    assert by_item["Latte"]["elasticity_mae"] == (
        pytest.approx(0.0, abs=1e-8)
    )

    assert pd.isna(by_item["Tea"]["elasticity_mae"])
    assert "distinct training prices" in str(
        by_item["Tea"]["reason"]
    )


def test_evaluate_all_items_empty_dataset():
    """Empty uploads should return a stable report schema."""

    results = evaluate_all_items(pd.DataFrame())

    assert results.empty
    assert "item" in results.columns
    assert "status" in results.columns
    assert "elasticity_mae" in results.columns


def test_model_coverage_summary_known_values():
    """Coverage and win rates must use correct denominators."""

    results = pd.DataFrame({
        "item": ["Latte", "Tea", "Mocha", "Juice"],
        "status": [
            "evaluated",
            "evaluated",
            "evaluated",
            "insufficient_evidence",
        ],
        "elasticity_lower_mae": [
            True,
            False,
            True,
            None,
        ],
    })

    coverage = summarize_model_coverage(results)

    assert coverage["total_items"] == 4
    assert coverage["evaluated_items"] == 3
    assert coverage["insufficient_evidence_items"] == 1

    assert coverage["evaluation_coverage_pct"] == pytest.approx(
        75.0
    )

    assert coverage["elasticity_better_items"] == 2
    assert coverage["elasticity_better_pct"] == pytest.approx(
        66.7
    )


def test_model_coverage_summary_no_evaluable_items():
    """Do not invent accuracy percentages when evaluation is unavailable."""

    results = pd.DataFrame({
        "item": ["Latte", "Tea"],
        "status": [
            "insufficient_evidence",
            "insufficient_evidence",
        ],
        "elasticity_lower_mae": [None, None],
    })

    coverage = summarize_model_coverage(results)

    assert coverage["total_items"] == 2
    assert coverage["evaluated_items"] == 0
    assert coverage["insufficient_evidence_items"] == 2

    assert coverage["evaluation_coverage_pct"] == pytest.approx(
        0.0
    )

    assert coverage["elasticity_better_items"] == 0
    assert coverage["elasticity_better_pct"] is None


def test_model_evaluation_report_contains_methodology():
    """Evaluation reports must clearly describe their limitations."""

    prices = sufficient_training_prices() + [5.5, 6.5]
    n = len(prices)

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=n,
        ),
        "item": ["Latte"] * n,
        "price": prices,
        "units_sold": [
            100.0 * (price / 5.0) ** -1.5
            for price in prices
        ],
    })

    report = build_model_evaluation_report(
        df,
        train_fraction=(n - 1.5) / n,
    )

    methodology = report["methodology"]
    coverage = report["coverage"]
    items = report["items"]

    assert isinstance(methodology, dict)
    assert isinstance(coverage, dict)
    assert isinstance(items, list)

    assert methodology["split_method"] == "chronological"
    assert methodology["causal_interpretation"] is False

    assert methodology["missing_dates"] == (
        "not_assumed_zero_sales"
    )

    assert coverage["total_items"] == 1
    assert coverage["evaluated_items"] == 1
    assert report["evaluated_items"] == 1

    assert len(items) == 1
    assert items[0]["status"] == "evaluated"


def test_model_evaluation_report_handles_no_supported_items():
    """A report should remain useful even without forecast metrics."""

    df = pd.DataFrame({
        "date": pd.date_range(
            "2026-01-01",
            periods=5,
        ),
        "item": ["Tea"] * 5,
        "price": [3.0] * 5,
        "units_sold": [10.0, 12.0, 9.0, 11.0, 8.0],
    })

    report = build_model_evaluation_report(df)

    coverage = report["coverage"]
    items = report["items"]

    assert isinstance(coverage, dict)
    assert isinstance(items, list)

    assert coverage["evaluated_items"] == 0
    assert coverage["elasticity_better_pct"] is None

    assert len(items) == 1
    assert items[0]["status"] == "insufficient_evidence"


def test_export_model_evaluation_report(tmp_path: Path):
    """Report exports should preserve methodology and item metrics."""

    report: dict[str, object] = {
        "methodology": {
            "split_method": "chronological",
            "causal_interpretation": False,
        },
        "coverage": {
            "total_items": 2,
            "evaluated_items": 1,
            "evaluation_coverage_pct": 50.0,
        },
        "evaluated_items": 1,
        "items": [
            {
                "item": "Latte",
                "status": "evaluated",
                "baseline_mae": 4.0,
                "elasticity_mae": 2.0,
            },
            {
                "item": "Tea",
                "status": "insufficient_evidence",
                "baseline_mae": None,
                "elasticity_mae": None,
            },
        ],
    }

    json_path, csv_path = export_model_evaluation_report(
        report,
        tmp_path,
    )

    assert json_path.exists()
    assert csv_path.exists()

    saved_json = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_json["coverage"]["total_items"] == 2
    assert saved_json["coverage"]["evaluated_items"] == 1
    assert saved_json["methodology"]["causal_interpretation"] is False

    saved_csv = pd.read_csv(csv_path)

    assert len(saved_csv) == 2

    by_item = saved_csv.set_index("item").to_dict(
        orient="index"
    )

    assert by_item["Latte"]["elasticity_mae"] == pytest.approx(
        2.0
    )
    assert by_item["Tea"]["status"] == "insufficient_evidence"


def test_export_model_evaluation_report_rejects_missing_sections(
    tmp_path: Path,
):
    """Malformed reports should not create misleading output files."""

    report: dict[str, object] = {
        "methodology": {"split_method": "chronological"},
        "coverage": {"total_items": 1},
        # Missing 'items'
    }

    with pytest.raises(
        ValueError,
        match="Report item results are missing or invalid",
    ):
        export_model_evaluation_report(report, tmp_path)

    assert not (
        tmp_path / "model_evaluation_report.json"
    ).exists()

    assert not (
        tmp_path / "model_evaluation_items.csv"
    ).exists()
