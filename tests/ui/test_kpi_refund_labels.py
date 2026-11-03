"""Regression tests for refund-aware dashboard KPI labels."""

from unittest.mock import MagicMock, patch

import pandas as pd

from ui.components import render_kpi_cards


def make_sales_data() -> pd.DataFrame:
    """Create sales-only data after refund candidates are separated."""
    return pd.DataFrame({
        "item": ["Latte", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [3, 2],
    })


def test_kpi_labels_with_refund_candidates():
    """Refund datasets must clearly label gross sales revenue."""
    df = make_sales_data()

    with (
        patch("ui.components.st.columns") as columns_mock,
        patch("ui.components.st.container") as container_mock,
        patch("ui.components.st.markdown") as markdown_mock,
        patch("ui.components.st.caption") as caption_mock,
    ):
        columns_mock.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        container_mock.return_value = MagicMock()

        render_kpi_cards(
            df,
            currency="USD",
            has_refund_candidates=True,
        )

        rendered_text = " ".join(
            str(call.args[0])
            for call in markdown_mock.call_args_list
        )

        captions = " ".join(
            str(call.args[0])
            for call in caption_mock.call_args_list
        )

        assert "Gross Sales Revenue" in rendered_text
        assert "$21.00" in rendered_text
        assert "Before refund candidates; not net revenue" in captions


def test_kpi_labels_without_refund_candidates():
    """Ordinary sales datasets retain their original revenue label."""
    df = make_sales_data()

    with (
        patch("ui.components.st.columns") as columns_mock,
        patch("ui.components.st.container") as container_mock,
        patch("ui.components.st.markdown") as markdown_mock,
        patch("ui.components.st.caption") as caption_mock,
    ):
        columns_mock.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        container_mock.return_value = MagicMock()

        render_kpi_cards(
            df,
            currency="USD",
            has_refund_candidates=False,
        )

        rendered_text = " ".join(
            str(call.args[0])
            for call in markdown_mock.call_args_list
        )

        captions = " ".join(
            str(call.args[0])
            for call in caption_mock.call_args_list
        )

        assert "Total Revenue" in rendered_text
        assert "Gross Sales Revenue" not in rendered_text
        assert "Sales revenue" in captions
