"""Regression tests for Elasticity Reliability UI."""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import elasticity_reliability


EXPECTED_COLUMNS = [
    "item",
    "category",
    "elasticity",
    "elasticity_source",
    "elasticity_confidence",
    "price_points",
    "observations",
    "price_variation_%",
]


def setup_mocks(monkeypatch):
    """Mock Streamlit components without launching the app."""

    container_mock = Mock(return_value=nullcontext())
    header_mock = Mock()
    info_mock = Mock()
    dataframe_mock = Mock()

    monkeypatch.setattr(
        elasticity_reliability.st,
        "container",
        container_mock,
    )
    monkeypatch.setattr(
        elasticity_reliability,
        "render_chart_header",
        header_mock,
    )
    monkeypatch.setattr(
        elasticity_reliability.st,
        "info",
        info_mock,
    )
    monkeypatch.setattr(
        elasticity_reliability.st,
        "dataframe",
        dataframe_mock,
    )

    return {
        "container": container_mock,
        "header": header_mock,
        "info": info_mock,
        "dataframe": dataframe_mock,
    }


def test_elasticity_reliability_columns_and_message(monkeypatch):
    """Verify the displayed columns and explanatory information."""

    summary = pd.DataFrame({
        "item": ["Latte", "Mocha"],
        "category": ["Coffee", "Coffee"],
        "elasticity": [-1.2, -0.8],
        "elasticity_source": ["estimated", "category_prior"],
        "elasticity_confidence": ["high", "low"],
        "price_points": [5, 1],
        "observations": [50, 10],
        "price_variation_%": [12.0, 0.0],
        "extra_column": [123, 456],
    })

    original = summary.copy(deep=True)
    mocks = setup_mocks(monkeypatch)

    elasticity_reliability.render_elasticity_reliability(summary)

    mocks["header"].assert_called_once_with(
        "Elasticity Reliability",
        "Review how each item's demand elasticity was determined "
        "and assess the reliability of those estimates.",
    )

    mocks["info"].assert_called_once()
    message = mocks["info"].call_args.args[0]

    assert "'estimated'" in message
    assert "'category_prior'" in message
    assert "'default_prior'" in message
    assert "not measured demand curves" in message

    mocks["container"].assert_called_with(border=True)
    assert mocks["container"].call_count == 2

    mocks["dataframe"].assert_called_once()

    displayed = mocks["dataframe"].call_args.args[0]

    assert list(displayed.columns) == EXPECTED_COLUMNS
    assert list(displayed["item"]) == ["Latte", "Mocha"]
    assert list(displayed["elasticity_source"]) == [
        "estimated",
        "category_prior",
    ]

    assert mocks["dataframe"].call_args.kwargs == {
        "width": "stretch",
        "hide_index": True,
    }

    assert_frame_equal(summary, original)


def test_elasticity_reliability_empty_summary(monkeypatch):
    """An empty summary should still display an empty table."""

    summary = pd.DataFrame(columns=EXPECTED_COLUMNS)
    mocks = setup_mocks(monkeypatch)

    elasticity_reliability.render_elasticity_reliability(summary)

    mocks["dataframe"].assert_called_once()

    displayed = mocks["dataframe"].call_args.args[0]

    assert displayed.empty
    assert list(displayed.columns) == EXPECTED_COLUMNS

    mocks["info"].assert_called_once()
