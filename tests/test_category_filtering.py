"""Regression tests for menu category classification."""

import sys
from pathlib import Path

import pandas as pd

# Allow tests to import modules from src/
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from config import category_group, classify_menu_item
from data_adapter import adapt_to_canonical


def test_basic_category_mapping():
    """Standard restaurant categories map correctly."""
    assert category_group("Coffee") == "Drinks"
    assert category_group("Tea") == "Drinks"
    assert category_group("Drinking Chocolate") == "Drinks"
    assert category_group("Bakery") == "Dessert"
    assert category_group("Unknown") == "Other"


def test_case_insensitive_mapping():
    """Category matching ignores capitalization."""
    assert category_group("COFFEE") == "Drinks"
    assert category_group("coffee") == "Drinks"
    assert category_group("  Coffee  ") == "Drinks"


def test_savory_item_override():
    """Specific menu items override broad categories."""
    assert (
        classify_menu_item("Bakery", "Jumbo Savory Scone")
        == "Savory"
    )

    assert (
        classify_menu_item("Bakery", "Chocolate Croissant")
        == "Dessert"
    )


def test_unknown_category_fallback():
    """Unknown categories must not crash the pipeline."""
    assert category_group("Mystery Category") == "Other"

    assert (
        classify_menu_item("Unknown", "Mystery Item")
        == "Other"
    )


def test_category_group_added_to_uploaded_data():
    """CSV adaptation automatically generates category groups."""
    raw_df = pd.DataFrame({
        "date": [
            "2023-03-01",
            "2023-03-01",
            "2023-03-02",
        ],
        "item": [
            "Latte",
            "Chocolate Croissant",
            "Jumbo Savory Scone",
        ],
        "category": [
            "Coffee",
            "Bakery",
            "Bakery",
        ],
        "price": [3.75, 3.75, 3.75],
        "units_sold": [10, 5, 8],
    })

    result, warnings = adapt_to_canonical(raw_df)

    assert "category_group" in result.columns

    assert result["category_group"].tolist() == [
        "Drinks",
        "Dessert",
        "Savory",
    ]

    assert len(result) == 3
