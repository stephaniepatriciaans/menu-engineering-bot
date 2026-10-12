"""Behavior-focused regression tests for the Pricing Recommendations UI."""

import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui.sections import pricing_recommendations


# ============================================================
# Shared test helpers
# ============================================================

def setup_mocks(monkeypatch, selected_item="Matcha Latte"):
    """Mock Streamlit without depending on presentation-only call counts."""

    widgets = {
        "header": Mock(),
        "subheader": Mock(),
        "info": Mock(),
        "caption": Mock(),
        "warning": Mock(),
        "dataframe": Mock(),
        "markdown": Mock(),
        "write": Mock(),
        "divider": Mock(),
        "metric": Mock(),
        "altair_chart": Mock(),
        "expander": Mock(return_value=nullcontext()),
        "container": Mock(return_value=nullcontext()),
        "columns": Mock(
            side_effect=lambda count: [
                nullcontext()
                for _ in range(count)
            ]
        ),
    }

    for name, widget_mock in widgets.items():
        monkeypatch.setattr(
            pricing_recommendations.st,
            name,
            widget_mock,
        )

    widgets["text_column"] = Mock(return_value="mock_column")

    monkeypatch.setattr(
        pricing_recommendations.st.column_config,
        "TextColumn",
        widgets["text_column"],
    )

    def selectbox_value(label, options, **kwargs):
        """Return the requested item only when the item exists."""
        if label == "Optimization strategy":
            return "Base case"

        if label == "Menu item to compare":
            if selected_item in options:
                return selected_item
            return options[0]

        return options[0]

    widgets["selectbox"] = Mock(side_effect=selectbox_value)

    monkeypatch.setattr(
        pricing_recommendations.st,
        "selectbox",
        widgets["selectbox"],
    )

    return widgets


def rendered_text(widget_mock):
    """Collect text passed to a mocked Streamlit component."""
    return [
        str(call.args[0])
        for call in widget_mock.call_args_list
        if call.args
    ]


def assert_text_contains(widget_mock, expected):
    """Verify important text exists without enforcing display order."""
    texts = rendered_text(widget_mock)

    assert any(
        expected in text
        for text in texts
    ), f"Expected {expected!r} in rendered text: {texts}"


def get_displayed_table(widgets, required_columns):
    """Find a displayed DataFrame by its columns, not call position."""
    required = set(required_columns)

    for call in widgets["dataframe"].call_args_list:
        if not call.args:
            continue

        table = call.args[0]

        if (
            isinstance(table, pd.DataFrame)
            and required.issubset(set(table.columns))
        ):
            return table

    raise AssertionError(
        f"No displayed table contains columns: {required_columns}"
    )


def make_moves(include_scenarios=False):
    """Build a controlled pricing-engine result for regression tests."""

    data = {
        "item": ["Latte", "Matcha Latte"],
        "old_price": [4.75, 5.25],
        "new_price": [5.46, 6.04],
        "pct_change_recommended": [14.9, 15.0],
        "daily_profit_delta": [14.03, 3.90],
        "quadrant": ["Star", "Plowhorse"],
        "elasticity_source": [
            "category_prior",
            "category_prior",
        ],
        "elasticity_confidence": ["low", "low"],
        "pricing_reliability": ["Low", "Low"],
        "reliability_reason": [
            "Latte uses an assumed category elasticity.",
            "Matcha Latte uses an assumed category elasticity.",
        ],
    }

    if include_scenarios:
        data.update({
            "base_case_daily_profit_delta": [14.03, 3.90],
            "best_case_daily_profit_delta": [23.73, 9.25],
            "worst_case_daily_profit_delta": [4.34, -1.44],
            "worst_case_loss": [False, True],
            "selection_mode": ["base_case", "base_case"],
        })

    return pd.DataFrame(data)


def render_with_mocked_pricing(
    monkeypatch,
    moves,
    selected_item="Matcha Latte",
    cost_is_assumption=False,
):
    """Render the UI using controlled pricing results."""

    widgets = setup_mocks(
        monkeypatch,
        selected_item=selected_item,
    )

    pricing_mock = Mock(return_value=moves)

    formatting_mock = Mock(
        side_effect=lambda df, currency: df.copy()
    )

    monkeypatch.setattr(
        pricing_recommendations,
        "recommend_price_moves",
        pricing_mock,
    )

    monkeypatch.setattr(
        pricing_recommendations,
        "display_moves_table",
        formatting_mock,
    )

    summary = pd.DataFrame({
        "item": moves["item"].tolist(),
        "price": moves["old_price"].tolist(),
    })

    original_summary = summary.copy(deep=True)
    original_moves = moves.copy(deep=True)

    result = pricing_recommendations.render_pricing_recommendations(
        summary=summary,
        capabilities={"price_optimization": True},
        currency="USD",
        max_decrease=10,
        max_increase=15,
        cost_is_assumption=cost_is_assumption,
    )

    return {
        "widgets": widgets,
        "pricing_mock": pricing_mock,
        "formatting_mock": formatting_mock,
        "summary": summary,
        "original_summary": original_summary,
        "moves": moves,
        "original_moves": original_moves,
        "result": result,
    }


# ============================================================
# Test 1: Pricing engine and recommendations
# ============================================================

def test_pricing_recommendations_with_estimated_costs(
    monkeypatch,
):
    """Verify pricing results, required disclosures, and data safety."""

    moves = make_moves(include_scenarios=False)

    context = render_with_mocked_pricing(
        monkeypatch,
        moves,
        cost_is_assumption=True,
    )

    widgets = context["widgets"]
    pricing_mock = context["pricing_mock"]

    # The pricing engine runs once with the original summary.
    pricing_mock.assert_called_once()

    assert (
        pricing_mock.call_args.args[0]
        is context["summary"]
    )

    # Verify the candidate price grid without hard-coding
    # an arbitrary number of candidates.
    candidate_changes = pricing_mock.call_args.args[1]

    expected_changes = [
        value / 100
        for value in range(-10, 16, 5)
    ]

    assert candidate_changes == expected_changes

    # Verify the UI forwards the expected controls.
    assert (
        pricing_mock.call_args.kwargs["selection_mode"]
        == "base_case"
    )

    assert (
        pricing_mock.call_args.kwargs["elasticity_uncertainty"]
        == 0.25
    )

    # The downstream AI memo receives unmodified results.
    assert context["result"] is moves

    # Required financial disclosures must be visible.
    assert_text_contains(
        widgets["caption"],
        "All simulated outcomes depend on elasticity",
    )

    assert_text_contains(
        widgets["caption"],
        "Candidate moves are tested from",
    )

    assert_text_contains(
        widgets["warning"],
        "estimated cost percentage",
    )

    assert_text_contains(
        widgets["warning"],
        "exploratory simulations",
    )

    # Verify the important dashboard sections exist.
    assert_text_contains(
        widgets["markdown"],
        "Pricing Risk Overview",
    )

    assert_text_contains(
        widgets["markdown"],
        "Recommended Price Moves",
    )

    # Verify important pricing columns, regardless
    # of surrounding tables or their display order.
    recommendations = get_displayed_table(
        widgets,
        {
            "Menu Item",
            "Current Price",
            "Recommended Price",
            "Price Change",
            "Estimated Daily Contribution Impact",
            "Pricing Reliability",
        },
    )

    assert len(recommendations) == len(moves)

    assert "reliability_reason" not in recommendations.columns

    # The scenario details should preserve model metadata.
    details = get_displayed_table(
        widgets,
        {
            "Menu Item",
            "Quadrant",
            "Elasticity Source",
            "Confidence",
        },
    )

    assert len(details) == len(moves)

    # Each formatting call must preserve the currency.
    for call in context["formatting_mock"].call_args_list:
        assert call.args[1] == "USD"

    # Verify pricing risk cards without depending
    # on their visual order.
    metrics = {
        call.args[0]: call.args[1]
        for call in widgets["metric"].call_args_list
    }

    assert metrics["Menu Items Assessed"] == str(len(moves))

    # Without scenario flags, the app must not
    # fabricate risk classifications.
    assert metrics["Negative Worst-Case"] == "Incomplete"
    assert metrics["No Simulated Downside Loss"] == "Incomplete"

    # Required risk disclosures must remain visible.
    for expected in (
        "Pricing scenarios analyzed",
        "Potential downside in simulation",
        "Nonnegative in tested scenarios",
    ):
        assert_text_contains(widgets["caption"], expected)

    # Original data cannot be modified by presentation logic.
    assert_frame_equal(
        context["summary"],
        context["original_summary"],
    )

    assert_frame_equal(
        context["moves"],
        context["original_moves"],
    )


# ============================================================
# Test 2: Missing-cost financial safeguard
# ============================================================

def test_pricing_recommendations_without_costs(
    monkeypatch,
):
    """Missing costs must disable profit-based recommendations."""

    widgets = setup_mocks(monkeypatch)

    pricing_mock = Mock()
    formatting_mock = Mock()

    monkeypatch.setattr(
        pricing_recommendations,
        "recommend_price_moves",
        pricing_mock,
    )

    monkeypatch.setattr(
        pricing_recommendations,
        "display_moves_table",
        formatting_mock,
    )

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    original_summary = summary.copy(deep=True)

    result = pricing_recommendations.render_pricing_recommendations(
        summary=summary,
        capabilities={"price_optimization": False},
        currency="USD",
        max_decrease=10,
        max_increase=15,
        cost_is_assumption=False,
    )

    assert isinstance(result, pd.DataFrame)
    assert result.empty

    # No pricing estimates may be generated.
    pricing_mock.assert_not_called()
    formatting_mock.assert_not_called()

    # No fabricated financial content may appear.
    widgets["dataframe"].assert_not_called()
    widgets["metric"].assert_not_called()
    widgets["altair_chart"].assert_not_called()

    assert_text_contains(
        widgets["info"],
        "complete unit cost data is unavailable",
    )

    assert_text_contains(
        widgets["write"],
        "No pricing recommendations are available",
    )

    # Existing input data must remain unchanged.
    assert_frame_equal(summary, original_summary)


# ============================================================
# Test 3: Scenario chart and shared item selection
# ============================================================

def test_scenario_chart_selected_item_and_negative_value(
    monkeypatch,
):
    """Chart and reliability details must follow the selected item."""

    moves = make_moves(include_scenarios=True)

    context = render_with_mocked_pricing(
        monkeypatch,
        moves,
        selected_item="Matcha Latte",
    )

    widgets = context["widgets"]

    # The selector must offer the items from the data.
    selector_calls = [
        call
        for call in widgets["selectbox"].call_args_list
        if call.args
        and call.args[0] == "Menu item to compare"
    ]

    assert selector_calls

    offered_items = selector_calls[0].kwargs["options"]

    assert set(offered_items) == set(moves["item"])

    # Check that the chart contains the selected item's
    # exact scenario values, including negative downside.
    widgets["altair_chart"].assert_called_once()

    chart = widgets["altair_chart"].call_args.args[0]
    chart_spec = chart.to_dict()

    assert "layer" in chart_spec

    actual_values = [
        row["Daily contribution impact"]
        for dataset in chart_spec.get("datasets", {}).values()
        for row in dataset
        if "Daily contribution impact" in row
    ]

    selected_row = moves.loc[
        moves["item"] == "Matcha Latte"
    ].iloc[0]

    expected_values = [
        selected_row["worst_case_daily_profit_delta"],
        selected_row["base_case_daily_profit_delta"],
        selected_row["best_case_daily_profit_delta"],
    ]

    for expected in expected_values:
        assert expected in actual_values

    assert selected_row["worst_case_daily_profit_delta"] < 0

    # Reliability details must follow the same selection.
    assert_text_contains(
        widgets["markdown"],
        "**Matcha Latte**",
    )

    assert_text_contains(
        widgets["write"],
        selected_row["reliability_reason"],
    )

    # Verify the risk cards use the actual scenario flags.
    metrics = {
        call.args[0]: call.args[1]
        for call in widgets["metric"].call_args_list
    }

    negative_count = int(moves["worst_case_loss"].eq(True).sum())
    nonnegative_count = int(moves["worst_case_loss"].eq(False).sum())

    assert metrics["Menu Items Assessed"] == str(len(moves))
    assert metrics["Negative Worst-Case"] == str(negative_count)
    assert metrics["No Simulated Downside Loss"] == str(
        nonnegative_count
    )

    # Source results must remain unchanged.
    assert context["result"] is moves

    assert_frame_equal(
        moves,
        context["original_moves"],
    )


# ============================================================
# Test 4: Scenario chart disabled without costs
# ============================================================

def test_scenario_chart_disabled_without_costs(
    monkeypatch,
):
    """The app must not display a profit scenario chart without costs."""

    widgets = setup_mocks(monkeypatch)
    pricing_mock = Mock()

    monkeypatch.setattr(
        pricing_recommendations,
        "recommend_price_moves",
        pricing_mock,
    )

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    result = pricing_recommendations.render_pricing_recommendations(
        summary=summary,
        capabilities={"price_optimization": False},
        currency="USD",
        max_decrease=10,
        max_increase=15,
        cost_is_assumption=False,
    )

    assert result.empty

    pricing_mock.assert_not_called()

    widgets["altair_chart"].assert_not_called()
    widgets["dataframe"].assert_not_called()
    widgets["metric"].assert_not_called()

    # A scenario item selector must not appear.
    scenario_selector_calls = [
        call
        for call in widgets["selectbox"].call_args_list
        if call.args
        and call.args[0] == "Menu item to compare"
    ]

    assert scenario_selector_calls == []
