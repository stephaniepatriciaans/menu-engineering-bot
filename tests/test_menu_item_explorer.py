"""Regression tests for the Menu Item Explorer dashboard"""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import menu_item_explorer


BASE_COLUMNS = [
    "item",
    "category",
    "price",
    "avg_daily_units",
    "total_units_sold",
    "total_revenue",
]

COST_COLUMNS = [
    "unit_cost",
    "contribution_margin_amount",
    "contribution_margin_%",
    "total_profit",
    "quadrant",
]

ELASTICITY_COLUMNS = [
    "elasticity",
    "elasticity_source",
    "elasticity_confidence",
]


def make_sample_summary():
    """Create sample data containing all supported columns."""

    return pd.DataFrame({
        "item": ["Latte", "Mocha", "Tea"],
        "category": ["Coffee", "Coffee", "Tea"],
        "price": [5.0, 6.0, 3.0],
        "avg_daily_units": [10.0, 20.0, 30.0],
        "total_units_sold": [100, 200, 300],
        "total_revenue": [500.0, 1200.0, 900.0],
        "unit_cost": [2.0, 2.5, 1.0],
        "contribution_margin_amount": [3.0, 3.5, 2.0],
        "contribution_margin_%": [60.0, 58.33, 66.67],
        "total_profit": [300.0, 700.0, 600.0],
        "quadrant": ["Puzzle", "Star", "Plowhorse"],
        "elasticity": [-1.2, -0.8, -1.5],
        "elasticity_source": [
            "estimated",
            "category_prior",
            "default_prior",
        ],
        "elasticity_confidence": [
            "high",
            "low",
            "low",
        ],
    })


def setup_mocks(monkeypatch, selected_sort):
    """Mock Streamlit controls and dashboard helpers."""

    container_mock = Mock(return_value=nullcontext())
    header_mock = Mock()
    dataframe_mock = Mock()
    caption_mock = Mock()

    selectbox_mock = Mock(return_value=selected_sort)

    sort_mock = Mock(
        side_effect=lambda summary, sort: summary.copy()
    )

    # Return a copy so we can inspect which columns were selected.
    format_mock = Mock(
        side_effect=lambda df, currency, has_cost: df.copy()
    )

    monkeypatch.setattr(
        menu_item_explorer.st,
        "container",
        container_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer.st,
        "selectbox",
        selectbox_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer.st,
        "dataframe",
        dataframe_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer.st,
        "caption",
        caption_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer,
        "render_chart_header",
        header_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer,
        "sort_menu_items",
        sort_mock,
    )

    monkeypatch.setattr(
        menu_item_explorer,
        "display_item_table",
        format_mock,
    )

    # Use a controlled sorting configuration.
    monkeypatch.setattr(
        menu_item_explorer,
        "SORTING_OPTIONS",
        {
            "Revenue": "total_revenue",
            "Units Sold": "total_units_sold",
        },
    )

    return {
        "container": container_mock,
        "header": header_mock,
        "selectbox": selectbox_mock,
        "sort": sort_mock,
        "format": format_mock,
        "dataframe": dataframe_mock,
        "caption": caption_mock,
    }


def test_menu_item_explorer_with_costs(monkeypatch):
    """Verify all columns display when profit analysis is available."""

    summary = make_sample_summary()
    original = summary.copy(deep=True)

    mocks = setup_mocks(
        monkeypatch,
        selected_sort="Revenue",
    )

    capabilities = {
        "profit_analysis": True,
    }

    menu_item_explorer.render_menu_item_explorer(
        summary,
        capabilities,
        "USD",
    )

    # Verify heading and description.
    mocks["header"].assert_called_once_with(
        "Menu Item Explorer",
        "Explore menu items by revenue, sales volume, or name. "
        "Category filters are applied automatically.",
    )

    # Verify sorting widget.
    mocks["selectbox"].assert_called_once_with(
        "Sort menu items by",
        options=["Revenue", "Units Sold"],
        index=0,
        key="menu_item_sort",
    )

    # Verify the original summary reaches the sorting function.
    mocks["sort"].assert_called_once_with(
        summary,
        "Revenue",
    )

    # Verify the table formatting function receives all columns.
    mocks["format"].assert_called_once()

    format_call = mocks["format"].call_args

    formatted_input = format_call.args[0]

    expected_columns = (
        BASE_COLUMNS
        + COST_COLUMNS
        + ELASTICITY_COLUMNS
    )

    assert list(formatted_input.columns) == expected_columns

    assert format_call.args[1] == "USD"
    assert format_call.args[2] is True

    # Verify table rendering.
    mocks["dataframe"].assert_called_once()

    assert mocks["dataframe"].call_args.kwargs == {
        "width": "stretch",
        "hide_index": True,
    }

    # Verify caption.
    mocks["caption"].assert_called_once_with(
        "Displaying 3 menu items. Sorted by: Revenue."
    )

    # Outer and inner containers.
    assert mocks["container"].call_count == 2

    # No mutation of the input data.
    assert_frame_equal(summary, original)


def test_menu_item_explorer_without_costs(monkeypatch):
    """Verify profit columns are excluded when costs are unavailable."""

    summary = make_sample_summary()
    original = summary.copy(deep=True)

    # Mimic data without cost-related fields.
    summary = summary[
        BASE_COLUMNS + ELASTICITY_COLUMNS
    ].copy()

    original = summary.copy(deep=True)

    mocks = setup_mocks(
        monkeypatch,
        selected_sort="Units Sold",
    )

    capabilities = {
        "profit_analysis": False,
    }

    menu_item_explorer.render_menu_item_explorer(
        summary,
        capabilities,
        "USD",
    )

    # Verify selected sorting option reaches the sorting helper.
    mocks["sort"].assert_called_once_with(
        summary,
        "Units Sold",
    )

    # Verify no cost-related columns are requested.
    mocks["format"].assert_called_once()

    format_call = mocks["format"].call_args

    formatted_input = format_call.args[0]

    expected_columns = (
        BASE_COLUMNS
        + ELASTICITY_COLUMNS
    )

    assert list(formatted_input.columns) == expected_columns

    for column in COST_COLUMNS:
        assert column not in formatted_input.columns

    assert format_call.args[1] == "USD"
    assert format_call.args[2] is False

    mocks["dataframe"].assert_called_once()

    mocks["caption"].assert_called_once_with(
        "Displaying 3 menu items. Sorted by: Units Sold."
    )

    assert mocks["container"].call_count == 2

    # The original input must remain unchanged
    assert_frame_equal(summary, original)
