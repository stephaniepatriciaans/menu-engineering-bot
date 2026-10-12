"""Regression tests for the Day Analysis dashboard"""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import day_analysis


@pytest.fixture
def sample_sales():
    """Minimal sales data passed into the dashboard"""
    return pd.DataFrame({
        "item": ["Latte", "Mocha"],
        "revenue": [100.0, 150.0],
        "units_sold": [20, 30],
    })


@pytest.fixture
def weekday_summary():
    """Known weekday and weekend results"""
    return pd.DataFrame({
        "day_type": ["Weekday", "Weekend"],
        "total_revenue": [500.0, 300.0],
        "total_units": [100, 50],
        "avg_daily_revenue": [100.0, 150.0],
        "days_with_sales": [5, 2],
    })


@pytest.fixture
def day_summary():
    """Known daily results with clear highest and lowest days results"""
    return pd.DataFrame({
        "day_name": ["Monday", "Tuesday", "Wednesday"],
        "total_revenue": [200.0, 600.0, 100.0],
        "total_units": [20, 60, 10],
        "days_with_sales": [2, 3, 1],
        "avg_daily_revenue": [100.0, 200.0, 50.0],
        "avg_daily_units": [10.0, 20.0, 10.0],
    })


@pytest.fixture
def mock_day_ui(monkeypatch):
    """Mock Streamlit and Plotly while preserving UI call behavior"""

    # Streamlit containers and expanders
    monkeypatch.setattr(
        day_analysis.st,
        "container",
        Mock(return_value=nullcontext()),
    )

    monkeypatch.setattr(
        day_analysis.st,
        "expander",
        Mock(return_value=nullcontext()),
    )

    # Streamlit columns are used as context managers
    columns_mock = Mock(
        side_effect=lambda *args, **kwargs: [
            nullcontext(),
            nullcontext(),
        ]
    )

    monkeypatch.setattr(
        day_analysis.st,
        "columns",
        columns_mock,
    )

    # Streamlit output functions
    metric_mock = Mock()
    info_mock = Mock()
    dataframe_mock = Mock()
    plot_mock = Mock()

    monkeypatch.setattr(
        day_analysis.st,
        "metric",
        metric_mock,
    )

    monkeypatch.setattr(
        day_analysis.st,
        "info",
        info_mock,
    )

    monkeypatch.setattr(
        day_analysis.st,
        "dataframe",
        dataframe_mock,
    )

    monkeypatch.setattr(
        day_analysis.st,
        "plotly_chart",
        plot_mock,
    )

    monkeypatch.setattr(
        day_analysis.st,
        "markdown",
        Mock(),
    )

    monkeypatch.setattr(
        day_analysis.st,
        "caption",
        Mock(),
    )

    # Mock charts but preserve the call arguments
    chart = Mock()

    bar_mock = Mock(return_value=chart)

    monkeypatch.setattr(
        day_analysis.px,
        "bar",
        bar_mock,
    )

    monkeypatch.setattr(
        day_analysis,
        "style_chart",
        Mock(return_value=chart),
    )

    monkeypatch.setattr(
        day_analysis,
        "render_chart_header",
        Mock(),
    )

    selectbox_mock = Mock(
        return_value="Average Daily Revenue"
    )

    monkeypatch.setattr(
        day_analysis.st,
        "selectbox",
        selectbox_mock,
    )

    return {
        "metric": metric_mock,
        "info": info_mock,
        "dataframe": dataframe_mock,
        "plot": plot_mock,
        "bar": bar_mock,
        "selectbox": selectbox_mock,
    }


def test_day_analysis_metrics_and_charts(
    monkeypatch,
    sample_sales,
    weekday_summary,
    day_summary,
    mock_day_ui,
):
    """Verify correct metrics, chart inputs, and widget keys."""

    original_sales = sample_sales.copy(deep=True)

    weekday_mock = Mock(return_value=weekday_summary)
    daily_mock = Mock(return_value=day_summary)

    monkeypatch.setattr(
        day_analysis,
        "compare_weekday_weekend",
        weekday_mock,
    )

    monkeypatch.setattr(
        day_analysis,
        "analyze_day_of_week",
        daily_mock,
    )

    # Run the dashboard section
    day_analysis.render_day_analysis(
        sample_sales,
        "USD",
    )

    # Existing analysis functions must receive original data
    weekday_mock.assert_called_once_with(sample_sales)
    daily_mock.assert_called_once_with(sample_sales)

    # Preserve the Streamlit widget key
    selectbox_call = mock_day_ui["selectbox"].call_args

    assert selectbox_call.kwargs["key"] == (
        "day_of_week_metric"
    )

    assert selectbox_call.args[0] == "Compare days by"

    # Both charts must render
    assert mock_day_ui["bar"].call_count == 2
    assert mock_day_ui["plot"].call_count == 2

    # Weekday/weekend chart uses average daily revenue
    first_chart = mock_day_ui["bar"].call_args_list[0]

    assert first_chart.kwargs["x"] == "day_type"
    assert first_chart.kwargs["y"] == (
        "avg_daily_revenue"
    )

    # Monday-Sunday chart uses selected metric
    second_chart = mock_day_ui["bar"].call_args_list[1]

    assert second_chart.kwargs["x"] == "day_name"
    assert second_chart.kwargs["y"] == (
        "avg_daily_revenue"
    )

    # Check highest and lowest day selections
    metric_calls = mock_day_ui["metric"].call_args_list

    highest = [
        call for call in metric_calls
        if call.args[0] == "Highest Avg. Revenue Day"
    ]

    lowest = [
        call for call in metric_calls
        if call.args[0] == "Lowest Avg. Revenue Day"
    ]

    assert len(highest) == 1
    assert len(lowest) == 1

    assert highest[0].args[1] == "Tuesday"
    assert lowest[0].args[1] == "Wednesday"

    # Check displayed average revenue values
    assert highest[0].args[2] == "USD200.00/day"
    assert lowest[0].args[2] == "USD50.00/day"

    # Both expandable data tables must render
    assert mock_day_ui["dataframe"].call_count == 2

    # Source data must remain unchanged
    assert_frame_equal(sample_sales, original_sales)


def test_day_analysis_missing_weekend(
    monkeypatch,
    sample_sales,
    day_summary,
    mock_day_ui,
):
    """Verify missing weekend data does not break the dashboard."""

    weekday_only = pd.DataFrame({
        "day_type": ["Weekday"],
        "total_revenue": [500.0],
        "total_units": [100],
        "avg_daily_revenue": [100.0],
        "days_with_sales": [5],
    })

    monkeypatch.setattr(
        day_analysis,
        "compare_weekday_weekend",
        Mock(return_value=weekday_only),
    )

    monkeypatch.setattr(
        day_analysis,
        "analyze_day_of_week",
        Mock(return_value=day_summary),
    )

    # Test a different metric selection
    mock_day_ui["selectbox"].return_value = (
        "Total Units Sold"
    )

    day_analysis.render_day_analysis(
        sample_sales,
        "USD",
    )

    # The missing weekend should show an info message
    mock_day_ui["info"].assert_called_once_with(
        "No sales recorded for this day type."
    )

    # Weekday values should still display
    metric_calls = mock_day_ui["metric"].call_args_list

    total_revenue = [
        call for call in metric_calls
        if call.args[0] == "Total Revenue"
    ]

    assert len(total_revenue) == 1
    assert total_revenue[0].args[1] == "$500.00"

    # Charts should continue rendering
    assert mock_day_ui["plot"].call_count == 2

    # Chart should use units sold when selected
    second_chart = mock_day_ui["bar"].call_args_list[1]

    assert second_chart.kwargs["y"] == (
        "total_units"
    )

    # Both tables should still render
    assert mock_day_ui["dataframe"].call_count == 2
