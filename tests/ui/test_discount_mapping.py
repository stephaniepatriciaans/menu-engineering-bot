"""Regression tests for optional POS discount column mapping."""

from unittest.mock import patch

import pandas as pd

from ui.mapping import (
    discount_amount_selector,
    discount_percent_selector,
)


def test_discount_selector_auto_detects_column():
    """Recognized discount columns should be preselected."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "line_discount": [1.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "line_discount"

        result = discount_amount_selector(raw)

    assert result == "line_discount"

    kwargs = selectbox.call_args.kwargs
    options = selectbox.call_args.args[1]

    assert "line_discount" in options
    assert options[kwargs["index"]] == "line_discount"


def test_discount_selector_allows_manual_mapping():
    """Users can select a discount column with an unfamiliar name."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "promo_reduction": [2.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "promo_reduction"

        result = discount_amount_selector(raw)

    assert result == "promo_reduction"


def test_discount_selector_can_be_unmapped():
    """Datasets without discounts can leave the field unmapped."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = None

        result = discount_amount_selector(raw)

    assert result is None


def test_discount_selector_excludes_price_and_quantity_columns():
    """Price and quantity cannot be selected as discounts."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [1.0],
    })

    mapping: dict[str, str | None] = {
        "price": "price",
        "units_sold": "units_sold",
    }

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "discount_amount"

        result = discount_amount_selector(
            raw,
            mapping=mapping,
        )

    options = selectbox.call_args.args[1]

    assert "price" not in options
    assert "units_sold" not in options
    assert "discount_amount" in options
    assert result == "discount_amount"


def test_percentage_selector_auto_detects_column():
    """Recognized percentage columns are preselected."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
        "discount_pct": [20.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "discount_pct"

        result = discount_percent_selector(raw)

    options = selectbox.call_args.args[1]
    selected_index = selectbox.call_args.kwargs["index"]

    assert result == "discount_pct"
    assert options[selected_index] == "discount_pct"


def test_percentage_selector_excludes_conflicting_columns():
    """Price, quantity and monetary discount columns are excluded."""
    raw = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [2.0],
        "discount_percent": [20.0],
    })

    mapping: dict[str, str | None] = {
        "price": "price",
        "units_sold": "units_sold",
    }

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = "discount_percent"

        result = discount_percent_selector(
            raw,
            mapping=mapping,
            discount_amount_column="discount_amount",
        )

    options = selectbox.call_args.args[1]

    assert "price" not in options
    assert "units_sold" not in options
    assert "discount_amount" not in options
    assert "discount_percent" in options
    assert result == "discount_percent"


def test_percentage_selector_can_be_unmapped():
    """Datasets without percentage discounts remain supported."""
    raw = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    with patch("ui.mapping.st.selectbox") as selectbox:
        selectbox.return_value = None

        result = discount_percent_selector(raw)

    assert result is None
