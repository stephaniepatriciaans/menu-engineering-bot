"""Regression tests for Pricing Recommendations UI"""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import pricing_recommendations


def setup_mocks(monkeypatch):
    """Replace Streamlit outputs and pricing helpers with mocks"""

    widgets = {
        "header": Mock(),
        "info": Mock(),
        "caption": Mock(),
        "warning": Mock(),
        "dataframe": Mock(),
        "markdown": Mock(),
        "write": Mock(),
        "divider": Mock(),
        "expander": Mock(return_value=nullcontext()),
    }

    for name, mock in widgets.items():
        monkeypatch.setattr(
            pricing_recommendations.st,
            name,
            mock,
        )

    text_column_mock = Mock(return_value="mock_column")

    monkeypatch.setattr(
        pricing_recommendations.st.column_config,
        "TextColumn",
        text_column_mock,
    )

    widgets["text_column"] = text_column_mock

    return widgets


def test_pricing_recommendations_with_estimated_costs(
    monkeypatch,
):
    """Verify pricing candidates, warnings, and returned moves."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })
    original_summary = summary.copy(deep=True)

    moves = pd.DataFrame({
        "item": ["Latte"],
        "old_price": [5.0],
        "new_price": [5.5],
        "pct_change_recommended": [0.10],
        "daily_profit_delta": [12.5],
        "quadrant": ["Star"],
        "elasticity_source": ["category_prior"],
        "elasticity_confidence": ["low"],
        "pricing_reliability": ["Low"],
        "reliability_reason": [
            "Uses an assumed category elasticity."
        ],
    })

    original_moves = moves.copy(deep=True)

    widgets = setup_mocks(monkeypatch)

    recommend_mock = Mock(return_value=moves)
    format_mock = Mock(
        side_effect=lambda df, currency: df.copy()
    )

    monkeypatch.setattr(
        pricing_recommendations,
        "recommend_price_moves",
        recommend_mock,
    )
    monkeypatch.setattr(
        pricing_recommendations,
        "display_moves_table",
        format_mock,
    )

    result = pricing_recommendations.render_pricing_recommendations(
        summary=summary,
        capabilities={"price_optimization": True},
        currency="USD",
        max_decrease=10,
        max_increase=10,
        cost_is_assumption=True,
    )

    # Original pricing engine must be called once.
    recommend_mock.assert_called_once()

    assert recommend_mock.call_args.args[0] is summary

    # Preserve the original 5% candidate increments.
    assert recommend_mock.call_args.args[1] == [
        -0.10,
        -0.05,
        0.0,
        0.05,
        0.10,
    ]

    # The downstream AI memo receives the same results.
    assert result is moves

    widgets["header"].assert_called_once_with(
        "Pricing Recommendations"
    )

    widgets["caption"].assert_called_once()

    # Scenario-cost warning plus reliability warning.
    assert widgets["warning"].call_count == 2

    warning_messages = [
        call.args[0]
        for call in widgets["warning"].call_args_list
    ]

    assert any(
        "estimated cost percentage" in message
        for message in warning_messages
    )

    assert any(
        "exploratory simulations" in message
        for message in warning_messages
    )

    # Reliability explanation is displayed.
    widgets["expander"].assert_called_once_with(
        "View pricing reliability explanations"
    )

    widgets["markdown"].assert_called_once_with(
        "**Latte**"
    )

    widgets["write"].assert_called_once_with(
        "Uses an assumed category elasticity."
    )

    widgets["divider"].assert_called_once()

    # Reliability reason is excluded from the main table.
    format_mock.assert_called_once()

    formatted_input = format_mock.call_args.args[0]

    assert "pricing_reliability" in formatted_input.columns
    assert "reliability_reason" not in formatted_input.columns

    assert format_mock.call_args.args[1] == "USD"

    widgets["text_column"].assert_called_once_with(
        "Pricing Reliability",
        width="large",
    )

    widgets["dataframe"].assert_called_once()

    assert widgets["dataframe"].call_args.kwargs == {
        "width": "stretch",
        "hide_index": True,
        "column_config": {
            "pricing_reliability": "mock_column",
        },
    }

    widgets["info"].assert_not_called()

    # No unintended mutation of source data.
    assert_frame_equal(summary, original_summary)
    assert_frame_equal(moves, original_moves)


def test_pricing_recommendations_without_costs(
    monkeypatch,
):
    """Verify pricing is disabled when optimization is unavailable."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    widgets = setup_mocks(monkeypatch)

    recommend_mock = Mock()
    format_mock = Mock()

    monkeypatch.setattr(
        pricing_recommendations,
        "recommend_price_moves",
        recommend_mock,
    )

    monkeypatch.setattr(
        pricing_recommendations,
        "display_moves_table",
        format_mock,
    )

    result = pricing_recommendations.render_pricing_recommendations(
        summary=summary,
        capabilities={"price_optimization": False},
        currency="USD",
        max_decrease=10,
        max_increase=10,
        cost_is_assumption=False,
    )

    # The pricing engine must not run
    recommend_mock.assert_not_called()

    # The downstream memo receives an empty DataFrame
    assert isinstance(result, pd.DataFrame)
    assert result.empty

    widgets["header"].assert_called_once_with(
        "Pricing Recommendations"
    )

    widgets["info"].assert_called_once_with(
        "Profit-based price recommendations are disabled "
        "because complete unit cost data is unavailable. "
        "The app will not fabricate cost or profit figures."
    )

    # No fabricated pricing table or profit warnings
    widgets["dataframe"].assert_not_called()
    widgets["warning"].assert_not_called()
    widgets["caption"].assert_not_called()
    format_mock.assert_not_called()

    # Preserve the original explanation expander
    widgets["expander"].assert_called_once_with(
        "View pricing reliability explanations"
    )

    widgets["markdown"].assert_not_called()
    widgets["write"].assert_not_called()
    widgets["divider"].assert_not_called()