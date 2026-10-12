"""Regression tests for the Popular Items dashboard."""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import popular_items


def test_popular_items_chart(monkeypatch):
    """Verify chart inputs, styling, and rendering."""

    summary = pd.DataFrame({
        "item": ["Latte", "Mocha", "Tea"],
        "total_units_sold": [100, 60, 30],
    })

    original = summary.copy(deep=True)

    monkeypatch.setattr(
        popular_items.st,
        "container",
        Mock(return_value=nullcontext()),
    )

    header_mock = Mock()
    monkeypatch.setattr(
        popular_items,
        "render_chart_header",
        header_mock,
    )

    chart = Mock()
    bar_mock = Mock(return_value=chart)

    monkeypatch.setattr(
        popular_items.px,
        "bar",
        bar_mock,
    )

    style_mock = Mock(return_value=chart)
    monkeypatch.setattr(
        popular_items,
        "style_chart",
        style_mock,
    )

    plot_mock = Mock()
    monkeypatch.setattr(
        popular_items.st,
        "plotly_chart",
        plot_mock,
    )

    popular_items.render_popular_items(summary)

    header_mock.assert_called_once_with(
        "Top Selling Menu Items",
        "Discover which menu items sell the most units.",
    )

    bar_mock.assert_called_once()

    chart_data = bar_mock.call_args.args[0]

    assert list(chart_data["item"]) == [
        "Latte",
        "Mocha",
        "Tea",
    ]

    assert bar_mock.call_args.kwargs["x"] == (
        "total_units_sold"
    )
    assert bar_mock.call_args.kwargs["y"] == "item"
    assert bar_mock.call_args.kwargs["orientation"] == "h"

    style_mock.assert_called_once_with(
        chart,
        title="Top Items by Units Sold",
    )

    plot_mock.assert_called_once_with(
        chart,
        width="stretch",
        config={"displayModeBar": False},
    )

    pd.testing.assert_frame_equal(summary, original)


def test_popular_items_limit(monkeypatch):
    """Only the top 15 items should appear in the chart."""

    summary = pd.DataFrame({
        "item": [f"Item {i}" for i in range(20)],
        "total_units_sold": list(range(20)),
    })

    monkeypatch.setattr(
        popular_items.st,
        "container",
        Mock(return_value=nullcontext()),
    )
    monkeypatch.setattr(
        popular_items,
        "render_chart_header",
        Mock(),
    )
    monkeypatch.setattr(
        popular_items,
        "style_chart",
        lambda chart, title: chart,
    )
    monkeypatch.setattr(
        popular_items.st,
        "plotly_chart",
        Mock(),
    )

    bar_mock = Mock(return_value=Mock())

    monkeypatch.setattr(
        popular_items.px,
        "bar",
        bar_mock,
    )

    popular_items.render_popular_items(summary)

    chart_data = bar_mock.call_args.args[0]

    assert len(chart_data) == 15
    assert chart_data["total_units_sold"].min() == 5
    assert chart_data["total_units_sold"].max() == 19
