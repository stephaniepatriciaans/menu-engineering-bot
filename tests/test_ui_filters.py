"""Regression tests for Streamlit sales date filtering."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui import filters


def setup_mocks(monkeypatch, selected_range):
    """Mock Streamlit widgets without running the dashboard."""

    widgets = {
        "date_input": Mock(return_value=selected_range),
        "warning": Mock(),
        "error": Mock(),
        "info": Mock(),
        "caption": Mock(),
        "stop": Mock(side_effect=RuntimeError("Streamlit stopped")),
    }

    for name, widget_mock in widgets.items():
        monkeypatch.setattr(
            filters.st,
            name,
            widget_mock,
        )

    return widgets


def make_sales_data():
    """Create a small, deterministic transaction dataset."""

    return pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
        ],
        "item": ["Latte", "Tea", "Cookie"],
        "price": [5.0, 4.0, 3.0],
        "units_sold": [2, 3, 4],
    })


def test_valid_date_range_filters_transactions(monkeypatch):
    """Return only transactions inside the inclusive date range."""

    selected_range = (
        date(2026, 1, 1),
        date(2026, 1, 2),
    )

    widgets = setup_mocks(monkeypatch, selected_range)

    sales = make_sales_data()
    original = sales.copy(deep=True)

    result, start_date, end_date = filters.render_date_filter(sales)

    assert start_date == selected_range[0]
    assert end_date == selected_range[1]

    assert result["item"].tolist() == ["Latte", "Tea"]
    assert len(result) == 2

    widgets["date_input"].assert_called_once()
    widgets["stop"].assert_not_called()

    # Verify filtering does not mutate the original input.
    assert_frame_equal(sales, original)


def test_invalid_dates_are_excluded_with_warning(monkeypatch):
    """Exclude invalid dates without inventing replacements."""

    selected_range = (
        date(2026, 1, 1),
        date(2026, 1, 3),
    )

    widgets = setup_mocks(monkeypatch, selected_range)

    sales = make_sales_data()
    sales.loc[1, "date"] = "not-a-date"

    original = sales.copy(deep=True)

    result, _, _ = filters.render_date_filter(sales)

    assert result["item"].tolist() == ["Latte", "Cookie"]

    warning_messages = [
        str(call.args[0])
        for call in widgets["warning"].call_args_list
    ]

    assert any(
        "invalid dates" in message
        for message in warning_messages
    )

    assert_frame_equal(sales, original)


def test_incomplete_date_range_stops_processing(monkeypatch):
    """A partially selected date range must not be processed."""

    widgets = setup_mocks(
        monkeypatch,
        selected_range=(date(2026, 1, 1),),
    )

    with pytest.raises(RuntimeError, match="Streamlit stopped"):
        filters.render_date_filter(make_sales_data())

    widgets["stop"].assert_called_once()

    info_messages = [
        str(call.args[0])
        for call in widgets["info"].call_args_list
    ]

    assert any(
        "Please select both" in message
        for message in info_messages
    )


def test_empty_date_range_stops_processing(monkeypatch):
    """Stop when the selected range contains no transactions."""

    widgets = setup_mocks(
        monkeypatch,
        selected_range=(
            date(2027, 1, 1),
            date(2027, 1, 2),
        ),
    )

    with pytest.raises(RuntimeError, match="Streamlit stopped"):
        filters.render_date_filter(make_sales_data())

    widgets["stop"].assert_called_once()

    warning_messages = [
        str(call.args[0])
        for call in widgets["warning"].call_args_list
    ]

    assert any(
        "No sales records exist" in message
        for message in warning_messages
    )


# ============================================================
# Category filtering regression tests
# ============================================================


def make_category_sales_data():
    """Build synthetic transactions across multiple categories."""

    return pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
        ],
        "item": [
            "Latte",
            "Espresso",
            "Chocolate Cake",
            "Turkey Sandwich",
        ],
        "category": [
            "Coffee",
            "Coffee",
            "Bakery",
            "Sandwich",
        ],
        "price": [5.0, 3.0, 6.0, 9.0],
        "units_sold": [2, 3, 1, 2],
    })


def setup_category_mocks(monkeypatch, selections=None):
    """Mock category widgets with controllable user selections."""

    selections = selections or {}

    def mock_multiselect(label, options, default, **kwargs):
        if label in selections:
            return selections[label]

        # By default, select all available categories.
        return list(default)

    widgets = {
        "header": Mock(),
        "multiselect": Mock(side_effect=mock_multiselect),
        "warning": Mock(),
        "caption": Mock(),
        "stop": Mock(
            side_effect=RuntimeError("Streamlit stopped")
        ),
    }

    for name, widget_mock in widgets.items():
        monkeypatch.setattr(
            filters.st,
            name,
            widget_mock,
        )

    return widgets


def test_category_filter_keeps_all_items_by_default(monkeypatch):
    """Default selections should preserve every valid transaction."""

    widgets = setup_category_mocks(monkeypatch)

    sales = make_category_sales_data()
    original = sales.copy(deep=True)

    result = filters.render_category_filter(sales)

    assert len(result) == len(sales)
    assert set(result["item"]) == set(sales["item"])

    # The original DataFrame must not gain a category_group column.
    assert "category_group" not in sales.columns

    assert_frame_equal(sales, original)

    widgets["stop"].assert_not_called()


def test_category_filter_limits_detailed_categories(monkeypatch):
    """Detailed selection should filter records correctly."""

    widgets = setup_category_mocks(
        monkeypatch,
        selections={
            "Filter by detailed category (optional)": ["Coffee"],
        },
    )

    sales = make_category_sales_data()

    result = filters.render_category_filter(sales)

    assert set(result["category"]) == {"Coffee"}
    assert set(result["item"]) == {"Latte", "Espresso"}
    assert len(result) == 2

    widgets["stop"].assert_not_called()


def test_category_filter_stops_on_empty_selection(monkeypatch):
    """An empty broad-category selection should stop processing."""

    widgets = setup_category_mocks(
        monkeypatch,
        selections={
            "Select food categories": [],
        },
    )

    with pytest.raises(RuntimeError, match="Streamlit stopped"):
        filters.render_category_filter(
            make_category_sales_data()
        )

    widgets["stop"].assert_called_once()

    warning_messages = [
        str(call.args[0])
        for call in widgets["warning"].call_args_list
    ]

    assert any(
        "No menu items match" in message
        for message in warning_messages
    )


def test_category_filter_uses_available_data_not_fixed_list(
    monkeypatch,
):
    """Category options should come from the supplied dataset."""

    widgets = setup_category_mocks(monkeypatch)

    sales = make_category_sales_data()

    filters.render_category_filter(sales)

    calls = widgets["multiselect"].call_args_list

    broad_call = next(
        call
        for call in calls
        if call.args[0] == "Select food categories"
    )

    detailed_call = next(
        call
        for call in calls
        if call.args[0] == "Filter by detailed category (optional)"
    )

    # All options must be based on categories that exist.
    assert set(detailed_call.kwargs["options"]) == set(
        sales["category"].unique()
    )

    assert set(broad_call.kwargs["default"]) == set(
        broad_call.kwargs["options"]
    )

    assert set(detailed_call.kwargs["default"]) == set(
        detailed_call.kwargs["options"]
    )
