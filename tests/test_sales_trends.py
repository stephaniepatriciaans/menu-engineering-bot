"""Regression tests for the Sales Trends dashboard section."""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import sales_trends


def test_sales_trends_preserves_controls_and_data(monkeypatch):
    grouped = pd.DataFrame({
        "period": pd.to_datetime([
            "2026-01-01",
            "2026-02-01",
        ]),
        "revenue": [100.0, 150.0],
        "units_sold": [20, 30],
    })

    aggregate_mock = Mock(return_value=grouped)
    monkeypatch.setattr(
        sales_trends,
        "aggregate_sales_by_period",
        aggregate_mock,
    )

    container_mock = Mock(return_value=nullcontext())
    monkeypatch.setattr(
        sales_trends.st,
        "container",
        container_mock,
    )

    monkeypatch.setattr(
        sales_trends.st,
        "expander",
        Mock(return_value=nullcontext()),
    )

    col1 = Mock()
    col2 = Mock()
    col1.__enter__ = Mock(return_value=col1)
    col1.__exit__ = Mock(return_value=False)
    col2.__enter__ = Mock(return_value=col2)
    col2.__exit__ = Mock(return_value=False)

    monkeypatch.setattr(
        sales_trends.st,
        "columns",
        Mock(return_value=(col1, col2)),
    )

    radio_mock = Mock(return_value="Monthly")
    select_mock = Mock(return_value="Revenue")

    monkeypatch.setattr(
        sales_trends.st,
        "radio",
        radio_mock,
    )
    monkeypatch.setattr(
        sales_trends.st,
        "selectbox",
        select_mock,
    )

    chart_mock = Mock()
    line_mock = Mock(return_value=chart_mock)

    monkeypatch.setattr(
        sales_trends.px,
        "line",
        line_mock,
    )

    monkeypatch.setattr(
        sales_trends,
        "style_chart",
        Mock(return_value=chart_mock),
    )

    monkeypatch.setattr(
        sales_trends,
        "render_chart_header",
        Mock(),
    )

    plot_mock = Mock()
    table_mock = Mock()

    monkeypatch.setattr(
        sales_trends.st,
        "plotly_chart",
        plot_mock,
    )
    monkeypatch.setattr(
        sales_trends.st,
        "dataframe",
        table_mock,
    )

    sales_trends.render_sales_trends(grouped, "USD")

    aggregate_mock.assert_called_once_with(
        grouped,
        "Monthly",
    )

    assert radio_mock.call_args.kwargs["key"] == (
        "sales_time_grouping"
    )

    assert select_mock.call_args.kwargs["key"] == (
        "sales_trend_metric"
    )

    assert line_mock.call_args.kwargs["y"] == "revenue"

    plot_mock.assert_called_once()
    table_mock.assert_called_once()

    displayed = table_mock.call_args.args[0]

    assert displayed.loc[0, "period"] == "2026-01-01"
    assert displayed.loc[0, "revenue"] == "$100.00"
