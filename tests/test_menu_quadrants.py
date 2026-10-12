"""Regression tests for Menu Engineering Quadrants UI"""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import menu_quadrants


def setup_mocks(monkeypatch):
    """Mock the Streamlit interface and Plotly chart"""

    container_mock = Mock(return_value=nullcontext())
    header_mock = Mock()
    chart_mock = Mock()
    scatter_mock = Mock(return_value=chart_mock)
    style_mock = Mock(return_value=chart_mock)

    plot_mock = Mock()
    warning_mock = Mock()
    info_mock = Mock()

    monkeypatch.setattr(
        menu_quadrants.st,
        "container",
        container_mock,
    )

    monkeypatch.setattr(
        menu_quadrants,
        "render_chart_header",
        header_mock,
    )

    monkeypatch.setattr(
        menu_quadrants.px,
        "scatter",
        scatter_mock,
    )

    monkeypatch.setattr(
        menu_quadrants,
        "style_chart",
        style_mock,
    )

    monkeypatch.setattr(
        menu_quadrants.st,
        "plotly_chart",
        plot_mock,
    )

    monkeypatch.setattr(
        menu_quadrants.st,
        "warning",
        warning_mock,
    )

    monkeypatch.setattr(
        menu_quadrants.st,
        "info",
        info_mock,
    )

    return {
        "container": container_mock,
        "header": header_mock,
        "chart": chart_mock,
        "scatter": scatter_mock,
        "style": style_mock,
        "plot": plot_mock,
        "warning": warning_mock,
        "info": info_mock,
    }


def test_menu_quadrants_chart_and_assumption_warning(
    monkeypatch,
):
    """Verify chart axes, median lines, and cost warning."""

    summary = pd.DataFrame({
        "item": ["Latte", "Mocha", "Tea"],
        "category": ["Coffee", "Coffee", "Tea"],
        "price": [5.0, 6.0, 3.0],
        "avg_daily_units": [10.0, 20.0, 30.0],
        "contribution_margin_%": [40.0, 60.0, 80.0],
        "quadrant": ["Puzzle", "Star", "Plowhorse"],
        "total_profit": [100.0, 200.0, 300.0],
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

    original = summary.copy(deep=True)

    capabilities = {
        "menu_engineering_quadrants": True,
    }

    mocks = setup_mocks(monkeypatch)

    menu_quadrants.render_menu_quadrants(
        summary,
        capabilities,
        cost_is_assumption=True,
    )

    # Correct heading
    mocks["header"].assert_called_once_with(
        "Menu Engineering Quadrants",
        "Evaluate menu performance using popularity "
        "and contribution margin.",
    )

    # Scatterplot is generated once
    mocks["scatter"].assert_called_once()

    scatter_call = mocks["scatter"].call_args

    assert scatter_call.args[0] is summary

    assert scatter_call.kwargs["x"] == "avg_daily_units"
    assert scatter_call.kwargs["y"] == "contribution_margin_%"
    assert scatter_call.kwargs["color"] == "quadrant"
    assert scatter_call.kwargs["size"] == "total_profit"
    assert scatter_call.kwargs["hover_name"] == "item"

    assert scatter_call.kwargs["hover_data"] == [
        "category",
        "price",
        "elasticity_source",
        "elasticity_confidence",
    ]

    # Median vertical line: 20 units
    mocks["chart"].add_vline.assert_called_once_with(
        x=20.0,
        line_dash="dash",
        line_color="gray",
    )

    # Median horizontal line: 60% margin
    mocks["chart"].add_hline.assert_called_once_with(
        y=60.0,
        line_dash="dash",
        line_color="gray",
    )

    mocks["style"].assert_called_once_with(
        mocks["chart"],
        title="Menu Engineering Quadrants",
    )

    mocks["plot"].assert_called_once_with(
        mocks["chart"],
        width="stretch",
        config={"displayModeBar": False},
    )

    # Estimated costs must show a warning
    mocks["warning"].assert_called_once_with(
        "Quadrants use the estimated cost-percentage "
        "scenario, not actual unit costs."
    )

    mocks["info"].assert_not_called()

    # Two nested Streamlit containers
    assert mocks["container"].call_count == 2

    # Input DataFrame must remain unchanged
    assert_frame_equal(summary, original)


def test_menu_quadrants_unavailable_without_costs(
    monkeypatch,
):
    """Verify explanatory message when margins are unavailable."""

    summary = pd.DataFrame({
        "item": ["Latte"],
    })

    capabilities = {
        "menu_engineering_quadrants": False,
    }

    mocks = setup_mocks(monkeypatch)

    menu_quadrants.render_menu_quadrants(
        summary,
        capabilities,
        cost_is_assumption=False,
    )

    # The header should still display
    mocks["header"].assert_called_once()

    # Without required costs, no chart should be created
    mocks["scatter"].assert_not_called()
    mocks["plot"].assert_not_called()
    mocks["style"].assert_not_called()

    # No cost assumption warning
    mocks["warning"].assert_not_called()

    # Explanation should be displayed
    mocks["info"].assert_called_once_with(
        "Menu quadrants require complete unit cost data "
        "because margin is one axis of the classification."
    )

    # Only the outer container is rendered
    assert mocks["container"].call_count == 1
