"""Regression tests for dashboard calculations."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from dashboard_utils import (
    add_transaction_datetime,
    aggregate_sales_by_period,
    analyze_day_of_week,
    analyze_hourly_revenue,
    analyze_peak_hours,
    compare_weekday_weekend,
    filter_by_date_range,
    sort_menu_items,
)


@pytest.fixture
def menu_summary():
    return pd.DataFrame({
        "item": ["Latte", "Croissant", "Tea"],
        "total_revenue": [150.0, 80.0, 120.0],
        "total_units_sold": [30, 40, 20],
    })


def test_highest_revenue(menu_summary):
    result = sort_menu_items(menu_summary, "Highest revenue")
    assert result["item"].tolist() == [
        "Latte", "Tea", "Croissant"
    ]


def test_lowest_revenue(menu_summary):
    result = sort_menu_items(menu_summary, "Lowest revenue")
    assert result["item"].tolist() == [
        "Croissant", "Tea", "Latte"
    ]


def test_best_selling(menu_summary):
    result = sort_menu_items(menu_summary, "Best-selling (units)")
    assert result["item"].tolist() == [
        "Croissant", "Latte", "Tea"
    ]


def test_lowest_selling(menu_summary):
    result = sort_menu_items(menu_summary, "Lowest-selling (units)")
    assert result["item"].tolist() == [
        "Tea", "Latte", "Croissant"
    ]


def test_alphabetical(menu_summary):
    result = sort_menu_items(menu_summary, "Alphabetical (A-Z)")
    assert result["item"].tolist() == [
        "Croissant", "Latte", "Tea"
    ]


def test_invalid_sort_option(menu_summary):
    with pytest.raises(ValueError):
        sort_menu_items(menu_summary, "Invalid option")


def test_sort_does_not_modify_original(menu_summary):
    original = menu_summary.copy(deep=True)

    sort_menu_items(menu_summary, "Highest revenue")

    pd.testing.assert_frame_equal(menu_summary, original)



@pytest.fixture
def dated_sales():
    return pd.DataFrame({
        "date": [
            "2023-03-01",
            "2023-03-15",
            "2023-03-31",
            "2023-04-01",
        ],
        "item": ["Latte", "Tea", "Cake", "Croissant"],
        "price": [4.0, 3.0, 5.0, 4.0],
        "units_sold": [2, 3, 1, 2],
    })


def test_date_range_inclusive(dated_sales):
    result = filter_by_date_range(
        dated_sales,
        "2023-03-01",
        "2023-03-31",
    )

    assert len(result) == 3
    assert result["item"].tolist() == [
        "Latte", "Tea", "Cake"
    ]


def test_single_day_filter(dated_sales):
    result = filter_by_date_range(
        dated_sales,
        "2023-03-15",
        "2023-03-15",
    )

    assert result["item"].tolist() == ["Tea"]


def test_date_range_no_matches(dated_sales):
    result = filter_by_date_range(
        dated_sales,
        "2023-05-01",
        "2023-05-31",
    )

    assert result.empty


def test_invalid_date_range(dated_sales):
    with pytest.raises(ValueError):
        filter_by_date_range(
            dated_sales,
            "2023-04-01",
            "2023-03-01",
        )


def test_date_filter_preserves_original(dated_sales):
    original = dated_sales.copy(deep=True)

    filter_by_date_range(
        dated_sales,
        "2023-03-01",
        "2023-03-31",
    )

    pd.testing.assert_frame_equal(
        dated_sales,
        original,
    )


def test_end_date_includes_timestamps():
    sales = pd.DataFrame({
        "date": [
            "2023-03-31 23:59:59",
            "2023-04-01 00:00:00",
        ]
    })

    result = filter_by_date_range(
        sales,
        "2023-03-01",
        "2023-03-31",
    )

    assert len(result) == 1


@pytest.fixture
def period_sales():
    return pd.DataFrame({
        "date": [
            "2023-01-01",
            "2023-01-02",
            "2023-01-08",
            "2023-02-01",
            "2024-01-01",
        ],
        "price": [10.0, 20.0, 5.0, 30.0, 40.0],
        "units_sold": [2, 1, 3, 1, 1],
    })


def test_daily_aggregation(period_sales):
    result = aggregate_sales_by_period(period_sales, "Daily")

    assert len(result) == 5
    assert result["revenue"].sum() == 125.0


def test_weekly_aggregation(period_sales):
    result = aggregate_sales_by_period(period_sales, "Weekly")

    assert result["period"].dt.strftime("%Y-%m-%d").tolist() == [
        "2022-12-26",
        "2023-01-02",
        "2023-01-30",
        "2024-01-01",
    ]

    assert result["revenue"].tolist() == [
        20.0, 35.0, 30.0, 40.0
    ]


def test_monthly_aggregation(period_sales):
    result = aggregate_sales_by_period(period_sales, "Monthly")

    assert len(result) == 3
    assert result["revenue"].tolist() == [
        55.0, 30.0, 40.0
    ]


def test_yearly_aggregation(period_sales):
    result = aggregate_sales_by_period(period_sales, "Yearly")

    assert result["revenue"].tolist() == [
        85.0, 40.0
    ]


def test_total_units_preserved(period_sales):
    result = aggregate_sales_by_period(period_sales, "Monthly")

    assert (
        result["units_sold"].sum()
        == period_sales["units_sold"].sum()
    )


def test_invalid_time_grouping(period_sales):
    with pytest.raises(ValueError):
        aggregate_sales_by_period(
            period_sales,
            "Hourly",
        )


def test_period_aggregation_preserves_original(period_sales):
    original = period_sales.copy(deep=True)

    aggregate_sales_by_period(
        period_sales,
        "Monthly",
    )

    pd.testing.assert_frame_equal(
        period_sales,
        original,
    )


@pytest.fixture
def weekday_weekend_sales():
    return pd.DataFrame({
        "date": [
            "2023-03-03",  # Friday
            "2023-03-04",  # Saturday
            "2023-03-05",  # Sunday
            "2023-03-06",  # Monday
        ],
        "price": [10.0, 20.0, 15.0, 10.0],
        "units_sold": [2, 3, 2, 4],
    })


def test_weekday_weekend_classification(weekday_weekend_sales):
    result = compare_weekday_weekend(weekday_weekend_sales)

    assert result["day_type"].astype(str).tolist() == [
        "Weekday", "Weekend"
    ]


def test_weekday_weekend_revenue(weekday_weekend_sales):
    result = compare_weekday_weekend(weekday_weekend_sales)

    assert result["total_revenue"].tolist() == [
        60.0, 90.0
    ]


def test_weekday_weekend_units(weekday_weekend_sales):
    result = compare_weekday_weekend(weekday_weekend_sales)

    assert result["total_units"].tolist() == [
        6, 5
    ]


def test_weekday_weekend_average_revenue(weekday_weekend_sales):
    result = compare_weekday_weekend(weekday_weekend_sales)

    assert result["avg_daily_revenue"].tolist() == [
        30.0, 45.0
    ]


def test_weekday_weekend_days_count(weekday_weekend_sales):
    result = compare_weekday_weekend(weekday_weekend_sales)

    assert result["days_with_sales"].tolist() == [
        2, 2
    ]


def test_weekday_weekend_preserves_original(weekday_weekend_sales):
    original = weekday_weekend_sales.copy(deep=True)

    compare_weekday_weekend(weekday_weekend_sales)

    pd.testing.assert_frame_equal(
        weekday_weekend_sales,
        original,
    )


@pytest.fixture
def day_of_week_sales():
    return pd.DataFrame({
        "date": [
            "2023-03-06",  # Monday
            "2023-03-06",  # Monday, another transaction
            "2023-03-07",  # Tuesday
            "2023-03-12",  # Sunday
            "2023-03-13",  # Next Monday
        ],
        "price": [10.0, 5.0, 20.0, 15.0, 30.0],
        "units_sold": [2, 2, 1, 2, 1],
    })


def test_day_of_week_order(day_of_week_sales):
    result = analyze_day_of_week(day_of_week_sales)

    assert result["day_name"].tolist() == [
        "Monday", "Tuesday", "Sunday"
    ]


def test_day_of_week_revenue(day_of_week_sales):
    result = analyze_day_of_week(day_of_week_sales)

    assert result["total_revenue"].tolist() == [
        60.0, 20.0, 30.0
    ]


def test_day_of_week_units(day_of_week_sales):
    result = analyze_day_of_week(day_of_week_sales)

    assert result["total_units"].tolist() == [
        5, 1, 2
    ]


def test_day_of_week_daily_average(day_of_week_sales):
    result = analyze_day_of_week(day_of_week_sales)

    monday = result[result["day_name"] == "Monday"].iloc[0]

    assert monday["days_with_sales"] == 2
    assert monday["avg_daily_revenue"] == 30.0


def test_day_of_week_total_preserved(day_of_week_sales):
    result = analyze_day_of_week(day_of_week_sales)

    assert result["total_revenue"].sum() == 110.0
    assert result["total_units"].sum() == 8


def test_day_of_week_preserves_original(day_of_week_sales):
    original = day_of_week_sales.copy(deep=True)

    analyze_day_of_week(day_of_week_sales)

    pd.testing.assert_frame_equal(
        day_of_week_sales, original
    )


def test_add_transaction_datetime():
    sales = pd.DataFrame({
        "date": ["2023-03-06", "2023-03-07"],
        "transaction_time": ["14:35:20", "09:15:00"],
    })

    result = add_transaction_datetime(sales)

    assert result["transaction_datetime"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    ).tolist() == [
        "2023-03-06 14:35:20",
        "2023-03-07 09:15:00",
    ]


def test_transaction_datetime_midnight():
    sales = pd.DataFrame({
        "date": ["2023-03-06"],
        "transaction_time": ["00:00:00"],
    })

    result = add_transaction_datetime(sales)

    assert result["transaction_datetime"].iloc[0] == pd.Timestamp(
        "2023-03-06 00:00:00"
    )


def test_transaction_datetime_missing_time():
    sales = pd.DataFrame({
        "date": ["2023-03-06"],
        "transaction_time": [pd.NA],
    })

    result = add_transaction_datetime(sales)

    assert pd.isna(result["transaction_datetime"].iloc[0])


def test_transaction_datetime_invalid_time():
    sales = pd.DataFrame({
        "date": ["2023-03-06"],
        "transaction_time": ["25:30:00"],
    })

    result = add_transaction_datetime(sales)

    assert pd.isna(result["transaction_datetime"].iloc[0])


def test_transaction_datetime_preserves_original():
    sales = pd.DataFrame({
        "date": ["2023-03-06"],
        "transaction_time": ["14:35:20"],
    })

    original = sales.copy(deep=True)

    add_transaction_datetime(sales)

    pd.testing.assert_frame_equal(sales, original)


def test_peak_hours_aggregation():
    sales = pd.DataFrame({
        "transaction_datetime": pd.to_datetime([
            "2023-03-06 09:15:00",
            "2023-03-06 09:45:00",
            "2023-03-06 14:30:00",
        ]),
        "price": [5.0, 4.0, 10.0],
        "units_sold": [2, 1, 3],
    })

    result = analyze_peak_hours(sales)

    assert result["hour"].tolist() == [9, 14]
    assert result["total_revenue"].tolist() == [14.0, 30.0]
    assert result["total_units"].tolist() == [3, 3]
    assert result["sales_rows"].tolist() == [2, 1]


def test_peak_hours_excludes_missing_times():
    sales = pd.DataFrame({
        "transaction_datetime": [
            pd.Timestamp("2023-03-06 09:00:00"),
            pd.NaT,
        ],
        "price": [5.0, 10.0],
        "units_sold": [2, 1],
    })

    result = analyze_peak_hours(sales)

    assert result["total_revenue"].sum() == 10.0
    assert result["sales_rows"].sum() == 1


def test_peak_hours_requires_datetime():
    sales = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
    })

    with pytest.raises(ValueError):
        analyze_peak_hours(sales)


def test_peak_hours_preserves_original():
    sales = pd.DataFrame({
        "transaction_datetime": pd.to_datetime(
            ["2023-03-06 09:15:00"]
        ),
        "price": [5.0],
        "units_sold": [2],
    })

    original = sales.copy(deep=True)

    analyze_peak_hours(sales)

    pd.testing.assert_frame_equal(sales, original)


def test_hourly_revenue_totals_and_averages():
    sales = pd.DataFrame({
        "transaction_datetime": pd.to_datetime([
            "2023-03-06 09:00:00",
            "2023-03-06 09:30:00",
            "2023-03-07 09:15:00",
            "2023-03-07 10:00:00",
        ]),
        "price": [5.0, 10.0, 20.0, 4.0],
        "units_sold": [2, 1, 1, 3],
    })

    result = analyze_hourly_revenue(sales)

    assert result["hour"].tolist() == [9, 10]
    assert result["total_revenue"].tolist() == [40.0, 12.0]
    assert result["days_with_sales"].tolist() == [2, 1]
    assert result["avg_daily_revenue"].tolist() == [20.0, 12.0]


def test_hourly_revenue_excludes_missing_timestamps():
    sales = pd.DataFrame({
        "transaction_datetime": [
            pd.Timestamp("2023-03-06 09:00:00"),
            pd.NaT,
        ],
        "price": [5.0, 10.0],
        "units_sold": [2, 1],
    })

    result = analyze_hourly_revenue(sales)

    assert result["total_revenue"].sum() == 10.0


def test_hourly_revenue_preserves_original():
    sales = pd.DataFrame({
        "transaction_datetime": pd.to_datetime([
            "2023-03-06 09:00:00",
        ]),
        "price": [5.0],
        "units_sold": [2],
    })

    original = sales.copy(deep=True)

    analyze_hourly_revenue(sales)

    pd.testing.assert_frame_equal(sales, original)
