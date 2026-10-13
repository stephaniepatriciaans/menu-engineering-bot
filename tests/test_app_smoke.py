"""Smoke tests for the Menu Engineering Bot Streamlit application"""
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "app.py"

def test_demo_dashboard_starts_without_exceptions():
    """The bundled synthetic demo should render successfully."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    assert any(
        "Menu Engineering Bot" in title.value
        for title in app.title
    )

    assert any(
        "Using the bundled synthetic dataset" in message.value
        for message in app.info
    )


def test_upload_mode_without_file_shows_guidance():
    """Selecting upload mode should show guidance without crashing."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    source_radio = next(
        radio
        for radio in app.radio
        if radio.label == "Data source"
    )

    source_radio.set_value("Upload my own CSV")
    app.run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    assert any(
        "Upload a CSV to start" in message.value
        for message in app.info
    )


def test_category_filter_updates_dashboard_sales_rows():
    """Selecting Drinks must update the dashboard's filtered rows."""
    app = AppTest.from_file(
        str(APP_PATH),
        default_timeout=60,
    ).run()

    assert not app.exception

    def displayed_sales_rows() -> int:
        """Read the filtered-row count shown below category filters."""
        for caption in app.get("caption"):
            caption_value = getattr(caption, "value", "")

            match = re.search(
                r"Showing ([\d,]+) sales rows across",
                str(caption_value),
            )

            if match:
                return int(match.group(1).replace(",", ""))

        raise AssertionError(
            "Could not find the category-filter sales-row caption."
        )

    initial_rows = displayed_sales_rows()

    category_filter = next(
        widget
        for widget in app.multiselect
        if widget.label == "Select food categories"
    )

    assert "Drinks" in category_filter.options
    assert len(category_filter.value) > 1

    category_filter.set_value(["Drinks"]).run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    filtered_rows = displayed_sales_rows()

    assert 0 < filtered_rows < initial_rows

    selected_filter = next(
        widget
        for widget in app.multiselect
        if widget.label == "Select food categories"
    )

    assert selected_filter.value == ["Drinks"]


def test_date_filter_updates_dashboard_sales_rows():
    """Changing the date range must update displayed sales rows."""
    app = AppTest.from_file(
        str(APP_PATH),
        default_timeout=60,
    ).run()

    assert not app.exception

    def displayed_sales_rows() -> int:
        """Read the date-filter sales-row count."""
        for caption in app.get("caption"):
            caption_value = getattr(caption, "value", "")

            match = re.search(
                r"Selected period:.*— ([\d,]+) sales rows",
                str(caption_value),
            )

            if match:
                return int(match.group(1).replace(",", ""))

        raise AssertionError(
            "Could not find the date-filter sales-row caption."
        )

    initial_rows = displayed_sales_rows()

    date_filter = next(
        widget
        for widget in app.date_input
        if widget.label == "Select a date range"
    )

    original_range = date_filter.value

    assert isinstance(original_range, (tuple, list))
    assert len(original_range) == 2

    start_date, end_date = original_range
    assert start_date < end_date

    # Narrow the analysis to the first day.
    date_filter.set_value((start_date, start_date)).run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    filtered_rows = displayed_sales_rows()

    assert 0 < filtered_rows < initial_rows

    selected_filter = next(
        widget
        for widget in app.date_input
        if widget.label == "Select a date range"
    )

    assert selected_filter.value == (start_date, start_date)


def test_pricing_strategy_change_invalidates_previous_memo():
    """Changing optimization strategy must invalidate a stale memo."""
    app = AppTest.from_file(
        str(APP_PATH),
        default_timeout=60,
    ).run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    strategy = next(
        widget
        for widget in app.selectbox
        if widget.label == "Optimization strategy"
    )

    assert strategy.value == "Base case"
    assert "Conservative" in strategy.options

    # Store a deliberately stale memo in this test session.
    # No AI API call is made.
    app.session_state["generated_memo"] = (
        "TEST ONLY: outdated pricing memo"
    )
    app.session_state["generated_memo_audit"] = {
        "finding_count": 0,
        "findings": [],
    }

    # Switch to a different pricing optimization strategy.
    strategy.set_value("Conservative").run()

    assert not app.exception, [
        str(error.message) for error in app.exception
    ]

    assert app.session_state["generated_memo"] is None
    assert app.session_state["generated_memo_audit"] is None
    assert app.session_state["generated_memo_context"] is None

    selected_strategy = next(
        widget
        for widget in app.selectbox
        if widget.label == "Optimization strategy"
    )

    assert selected_strategy.value == "Conservative"
