
"""Regression tests for Hourly Analysis dashboard"""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import hourly_analysis


@pytest.fixture
def mock_hourly_ui(monkeypatch):
    """Mock Streamlit controls and charts."""

    monkeypatch.setattr(
        hourly_analysis.st,
        "container",
        Mock(return_value=nullcontext()),
    )
    monkeypatch.setattr(
        hourly_analysis.st,
        "expander",
        Mock(return_value=nullcontext()),
    )

    widgets = {
        "metric": Mock(),
        "info": Mock(),
        "dataframe": Mock(),
        "plotly_chart": Mock(),
        "selectbox": Mock(return_value="Revenue"),
    }

    for name, mock in widgets.items():
        monkeypatch.setattr(hourly_analysis.st, name, mock)

    chart = Mock()
    bar_mock = Mock(return_value=chart)
    line_mock = Mock(return_value=chart)

    monkeypatch.setattr(hourly_analysis.px, "bar", bar_mock)
    monkeypatch.setattr(hourly_analysis.px, "line", line_mock)
    monkeypatch.setattr(
        hourly_analysis,
        "style_chart",
        Mock(return_value=chart),
    )
    monkeypatch.setattr(
        hourly_analysis,
        "render_chart_header",
        Mock(),
    )

    widgets["bar"] = bar_mock
    widgets["line"] = line_mock

    return widgets


def test_hourly_analysis_with_valid_timestamps(
    monkeypatch,
    mock_hourly_ui,
):
    """Verify peak-hour and average-revenue results."""

    df = pd.DataFrame({
        "transaction_datetime": pd.to_datetime([
            "2026-01-01 09:00",
            "2026-01-01 12:00",
        ]),
    })

    peak_summary = pd.DataFrame({
        "hour": [9, 12],
        "total_revenue": [100.0, 250.0],
        "total_units": [10, 20],
        "sales_rows": [2, 4],
    })

    revenue_summary = pd.DataFrame({
        "hour": [9, 12],
        "total_revenue": [300.0, 500.0],
        "days_with_sales": [3, 2],
        "avg_daily_revenue": [100.0, 250.0],
    })

    peak_mock = Mock(return_value=peak_summary)
    revenue_mock = Mock(return_value=revenue_summary)

    monkeypatch.setattr(
        hourly_analysis,
        "analyze_peak_hours",
        peak_mock,
    )
    monkeypatch.setattr(
        hourly_analysis,
        "analyze_hourly_revenue",
        revenue_mock,
    )

    hourly_analysis.render_hourly_analysis(df, "USD")

    peak_mock.assert_called_once_with(df)
    revenue_mock.assert_called_once_with(df)

    select_call = mock_hourly_ui["selectbox"].call_args
    assert select_call.kwargs["key"] == "peak_hour_metric"

    bar_call = mock_hourly_ui["bar"].call_args
    assert bar_call.kwargs["y"] == "total_revenue"

    line_call = mock_hourly_ui["line"].call_args
    assert line_call.kwargs["y"] == "avg_daily_revenue"

    metric_calls = mock_hourly_ui["metric"].call_args_list

    assert metric_calls[0].args == (
        "Peak Hour by Revenue",
        "12:00",
    )
    assert metric_calls[1].args == (
        "Highest Average Revenue Hour",
        "12:00",
    )

    assert mock_hourly_ui["plotly_chart"].call_count == 2
    assert mock_hourly_ui["dataframe"].call_count == 2
    mock_hourly_ui["info"].assert_not_called()


def test_hourly_analysis_without_timestamps(
    monkeypatch,
    mock_hourly_ui,
):
    """Missing timestamps should show informative messages."""

    df = pd.DataFrame({
        "transaction_datetime": [pd.NaT, pd.NaT],
    })

    peak_mock = Mock()
    revenue_mock = Mock()

    monkeypatch.setattr(
        hourly_analysis,
        "analyze_peak_hours",
        peak_mock,
    )
    monkeypatch.setattr(
        hourly_analysis,
        "analyze_hourly_revenue",
        revenue_mock,
    )

    hourly_analysis.render_hourly_analysis(df, "USD")

    peak_mock.assert_not_called()
    revenue_mock.assert_not_called()

    assert mock_hourly_ui["info"].call_count == 2
    mock_hourly_ui["plotly_chart"].assert_not_called()
    mock_hourly_ui["metric"].assert_not_called()