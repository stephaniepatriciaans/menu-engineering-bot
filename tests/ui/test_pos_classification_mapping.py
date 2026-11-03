"""Regression tests for optional POS classification column mapping."""

from unittest.mock import patch

import pandas as pd
import pytest

from ui.mapping import (
    transaction_amount_selector,
    transaction_status_selector,
)


@pytest.fixture
def pos_data():
    """Create generic POS data for testing column mappings."""
    return pd.DataFrame({
        "quantity": [2, 1],
        "unit_price": [5.0, 8.0],
        "transaction_status": ["completed", "refunded"],
        "line_total": [10.0, -8.0],
        "custom_state": ["paid", "returned"],
        "custom_amount": [10.0, -8.0],
    })


@pytest.mark.parametrize(
    ("selector", "column"),
    [
        (transaction_status_selector, "transaction_status"),
        (transaction_amount_selector, "line_total"),
    ],
)
def test_pos_selector_auto_detects_known_columns(
    pos_data,
    selector,
    column,
):
    """Known column aliases should be preselected."""
    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = column

        result = selector(pos_data)

    options = selectbox.call_args.args[1]
    selected_index = selectbox.call_args.kwargs["index"]

    assert result == column
    assert options[selected_index] == column


@pytest.mark.parametrize(
    ("selector", "column"),
    [
        (transaction_status_selector, "custom_state"),
        (transaction_amount_selector, "custom_amount"),
    ],
)
def test_pos_selector_allows_manual_mapping(
    pos_data,
    selector,
    column,
):
    """Unfamiliar POS headers must remain manually selectable."""
    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = column

        result = selector(pos_data)

    assert result == column


@pytest.mark.parametrize(
    "selector",
    [
        transaction_status_selector,
        transaction_amount_selector,
    ],
)
def test_pos_selector_can_be_unmapped(selector):
    """Optional fields must not be required."""
    df = pd.DataFrame({
        "quantity": [1],
        "unit_price": [5.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = None

        result = selector(df)

    assert result is None


@pytest.mark.parametrize(
    ("selector", "column"),
    [
        (transaction_status_selector, "transaction_status"),
        (transaction_amount_selector, "line_total"),
    ],
)
def test_pos_selector_excludes_existing_mapping(
    pos_data,
    selector,
    column,
):
    """Existing canonical mappings must not be reused."""
    mapping: dict[str, str | None] = {
        "price": "unit_price",
        "units_sold": "quantity",
    }

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = column

        result = selector(
            pos_data,
            mapping=mapping,
            excluded_columns={"custom_state", "custom_amount"},
        )

    options = selectbox.call_args.args[1]

    assert "unit_price" not in options
    assert "quantity" not in options
    assert "custom_state" not in options
    assert "custom_amount" not in options
    assert result == column


def test_status_and_amount_mapping_can_be_distinct(pos_data):
    """Status and amount must use different source columns."""
    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "transaction_status"

        status_column = transaction_status_selector(pos_data)

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "line_total"

        amount_column = transaction_amount_selector(
            pos_data,
            excluded_columns=(
                {status_column}
                if status_column is not None
                else set()
            ),
        )

    assert status_column != amount_column

    options = selectbox.call_args.args[1]
    assert status_column not in options
