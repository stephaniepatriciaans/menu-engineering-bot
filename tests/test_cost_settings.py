"""Regression tests for optional cost settings."""

import io
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui import cost_settings


@pytest.fixture
def sample_sales():
    """Sales dataset with incomplete unit costs."""
    return pd.DataFrame({
        "item": ["Latte", "Mocha"],
        "price": [5.50, 6.00],
        "units_sold": [10, 8],
        "unit_cost": [2.00, float("nan")],
    })


@pytest.fixture
def mock_ui(monkeypatch):
    """Replace Streamlit widgets with controllable mocks."""
    names = [
        "expander",
        "write",
        "radio",
        "file_uploader",
        "columns",
        "slider",
        "warning",
        "error",
        "success",
    ]

    widgets = {}

    for name in names:
        widget = Mock()
        monkeypatch.setattr(cost_settings.st, name, widget)
        widgets[name] = widget

    widgets["expander"].return_value = nullcontext()

    return widgets


def test_complete_cost_data(mock_ui, sample_sales):
    """Provided costs must remain unchanged."""
    sales = sample_sales.fillna({"unit_cost": 2.50})
    original = sales.copy(deep=True)

    result, basis, assumed = (
        cost_settings.render_cost_settings(sales)
    )

    assert_frame_equal(result, original)
    assert basis == "provided_cost_column"
    assert assumed is False

    mock_ui["success"].assert_called_once()
    mock_ui["radio"].assert_not_called()


def test_continue_without_cost(mock_ui, sample_sales):
    """Missing costs must not be silently estimated."""
    mock_ui["radio"].return_value = (
        "Continue without unit cost"
    )

    original = sample_sales.copy(deep=True)

    result, basis, assumed = (
        cost_settings.render_cost_settings(sample_sales)
    )

    assert_frame_equal(result, original)
    assert basis == "unavailable"
    assert assumed is False
    assert pd.isna(result.loc[1, "unit_cost"])


def test_separate_cost_csv(
    monkeypatch,
    mock_ui,
    sample_sales,
):
    """Uploaded costs must use the existing merge function."""
    mock_ui["radio"].return_value = (
        "Upload a separate menu-cost CSV"
    )

    upload = io.BytesIO(
        b"item_name,cost\nMocha,2.50\n"
    )
    mock_ui["file_uploader"].return_value = upload

    cost_df = pd.DataFrame({
        "item_name": ["Mocha"],
        "cost": [2.50],
    })

    read_mock = Mock(return_value=cost_df)
    detect_mock = Mock(return_value={
        "item": "item_name",
        "unit_cost": "cost",
    })

    merged = sample_sales.copy(deep=True)
    merged.loc[1, "unit_cost"] = 2.50

    merge_mock = Mock(return_value=(
        merged,
        ["Cost reference successfully matched."],
    ))

    monkeypatch.setattr(
        cost_settings,
        "read_delimited_csv",
        read_mock,
    )
    monkeypatch.setattr(
        cost_settings,
        "detect_column_mapping",
        detect_mock,
    )
    monkeypatch.setattr(
        cost_settings,
        "merge_cost_reference",
        merge_mock,
    )

    item_column = Mock()
    cost_column = Mock()

    item_column.selectbox.return_value = "item_name"
    cost_column.selectbox.return_value = "cost"

    mock_ui["columns"].return_value = (
        item_column,
        cost_column,
    )

    result, basis, assumed = (
        cost_settings.render_cost_settings(sample_sales)
    )

    assert_frame_equal(result, merged)
    assert basis == "separate_menu_cost_csv"
    assert assumed is False

    read_mock.assert_called_once_with(upload)
    detect_mock.assert_called_once()

    merge_mock.assert_called_once_with(
        sample_sales,
        cost_df,
        "item_name",
        "cost",
    )

    assert mock_ui["warning"].called
    mock_ui["error"].assert_not_called()


def test_estimated_cost_scenario(
    monkeypatch,
    mock_ui,
    sample_sales,
):
    """A 30% scenario must pass 0.30 to the estimator."""
    mock_ui["radio"].return_value = (
        "Scenario analysis using estimated cost percentage"
    )
    mock_ui["slider"].return_value = 30

    estimated = sample_sales.copy(deep=True)
    estimated["unit_cost"] = [
        1.65,
        1.80,
    ]

    estimate_mock = Mock(return_value=estimated)

    monkeypatch.setattr(
        cost_settings,
        "apply_estimated_cost_percentage",
        estimate_mock,
    )

    result, basis, assumed = (
        cost_settings.render_cost_settings(sample_sales)
    )

    assert_frame_equal(result, estimated)
    assert basis == "assumption_30_percent_of_price"
    assert assumed is True

    estimate_mock.assert_called_once_with(
        sample_sales,
        0.30,
    )

    mock_ui["warning"].assert_called_once()


def test_invalid_cost_csv(
    monkeypatch,
    mock_ui,
    sample_sales,
):
    """Invalid uploads must show an error without crashing."""
    mock_ui["radio"].return_value = (
        "Upload a separate menu-cost CSV"
    )

    mock_ui["file_uploader"].return_value = (
        io.BytesIO(b"invalid file")
    )

    read_mock = Mock(
        side_effect=ValueError("Invalid CSV")
    )

    monkeypatch.setattr(
        cost_settings,
        "read_delimited_csv",
        read_mock,
    )

    original = sample_sales.copy(deep=True)

    result, basis, assumed = (
        cost_settings.render_cost_settings(sample_sales)
    )

    assert_frame_equal(result, original)
    assert basis == "unavailable"
    assert assumed is False

    mock_ui["error"].assert_called_once()
    assert "Invalid CSV" in str(
        mock_ui["error"].call_args
    )


def test_partial_cost_data_activates_options(
    mock_ui,
    sample_sales,
):
    """Partially missing costs must show cost handling options."""
    mock_ui["radio"].return_value = (
        "Continue without unit cost"
    )

    result, basis, assumed = (
        cost_settings.render_cost_settings(sample_sales)
    )

    assert basis == "unavailable"
    assert assumed is False

    assert result["unit_cost"].notna().sum() == 1

    mock_ui["radio"].assert_called_once()
    mock_ui["success"].assert_not_called()
