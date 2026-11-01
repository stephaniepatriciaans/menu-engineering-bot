"""Tests for POS accounting integration with column mapping."""

from unittest.mock import MagicMock, patch

import pandas as pd

from ui.data_upload import render_pos_accounting_summary


def test_pos_accounting_uses_selected_column_mapping():
    """Accounting must display correct values from mapped columns."""
    raw_df = pd.DataFrame({
        "Product": ["Latte", "Latte", "Tea"],
        "Selling Price": [5.0, 5.0, 3.0],
        "Quantity": [3, -1, 2],
        "Other Number": [100, 200, 300],
    })

    mapping: dict[str, str | None] = {
        "price": "Selling Price",
        "units_sold": "Quantity",
    }

    with (
        patch("ui.data_upload.st.expander") as expander_mock,
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
    ):
        
        # Give each Streamlit metric column its own mock.
        metric_columns = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        columns_mock.return_value = metric_columns

        render_pos_accounting_summary(raw_df, mapping)

        expander_mock.assert_called_once_with(
            "POS transaction accounting",
            expanded=False,
        )

        columns_mock.assert_called_once_with(3)

        metric_columns[0].metric.assert_called_once_with(
            "Gross Revenue",
            "21.00",
        )

        metric_columns[1].metric.assert_called_once_with(
            "Refund Candidates",
            1,
        )

        metric_columns[2].metric.assert_called_once_with(
            "Net Revenue",
            "16.00",
        )


def test_pos_accounting_skips_missing_mapping():
    """Do not show accounting when price or quantity is unmapped."""
    raw_df = pd.DataFrame({
        "Product": ["Latte"],
        "Quantity": [2],
    })

    mapping = {
        "price": None,
        "units_sold": "Quantity",
    }

    with patch("ui.data_upload.st.expander") as expander_mock:
        render_pos_accounting_summary(raw_df, mapping)

        expander_mock.assert_not_called()
