"""Regression tests for universal POS dataset adaptation"""

import io

import pandas as pd
import pytest

from data_adapter import (
    adapt_to_canonical,
    apply_known_preset,
    mapping_confidence,
    merge_cost_reference,
    read_delimited_csv,
    validate_mapping,
)


@pytest.mark.parametrize("delimiter", [",", "|", ";", "\t"])
def test_read_delimited_csv_supported_delimiters(delimiter):
    text = (
        f"item{delimiter}price{delimiter}units_sold\n"
        f"Latte{delimiter}5.50{delimiter}2\n"
    )

    result = read_delimited_csv(io.BytesIO(text.encode("utf-8")))

    assert result.columns.tolist() == [
        "item",
        "price",
        "units_sold",
    ]
    assert result.loc[0, "item"] == "Latte"
    assert result.loc[0, "price"] == pytest.approx(5.50)


def test_read_delimited_csv_rejects_empty_upload():
    with pytest.raises(ValueError, match="empty"):
        read_delimited_csv(io.BytesIO(b""))


def test_read_delimited_csv_rejects_unknown_delimiter():
    with pytest.raises(ValueError, match="Could not detect"):
        read_delimited_csv(io.BytesIO(b"item price units_sold\nLatte 5 2"))


def test_apply_known_preset_only_maps_available_columns():
    result = apply_known_preset(
        ["transaction_date", "product_detail", "unit_price"],
        "Starbucks-style POS export",
    )

    assert result == {
        "date": "transaction_date",
        "item": "product_detail",
        "price": "unit_price",
    }


def test_apply_known_preset_unknown_name_returns_empty():
    assert apply_known_preset(["item"], "Unknown POS") == {}


def test_mapping_confidence_identifies_mapping_types():
    result = mapping_confidence(
        ["date", "product_detail", "some_custom_column"],
        {
            "date": "date",
            "item": "product_detail",
            "price": "some_custom_column",
        },
    )

    assert result["date"] == "exact"
    assert result["item"] == "alias"
    assert result["price"] == "review manually"
    assert result["unit_cost"] == "not mapped"


def test_validate_mapping_rejects_missing_core_fields():
    errors = validate_mapping(
        {"item": "item"},
        ["item"],
    )

    assert any("required fields" in error for error in errors)


def test_validate_mapping_rejects_duplicate_columns():
    errors = validate_mapping(
        {
            "date": "date",
            "item": "same",
            "price": "same",
            "units_sold": "quantity",
        },
        ["date", "same", "quantity"],
    )

    assert any("only one field" in error for error in errors)


def test_validate_mapping_rejects_missing_source_columns():
    errors = validate_mapping(
        {
            "date": "date",
            "item": "item",
            "price": "missing_price",
            "units_sold": "quantity",
        },
        ["date", "item", "quantity"],
    )

    assert any("not found" in error for error in errors)


def test_adapt_to_canonical_rejects_invalid_mapping():
    raw = pd.DataFrame(
        {
            "date": ["2026-01-01"],
            "item": ["Latte"],
            "price": [5.0],
            "units_sold": [2],
        }
    )

    with pytest.raises(ValueError, match="required fields"):
        adapt_to_canonical(
            raw,
            {"item": "item"},
        )


def test_merge_cost_reference_matches_case_and_whitespace():
    sales = pd.DataFrame(
        {
            "item": ["Latte", "Mocha"],
            "unit_cost": [pd.NA, pd.NA],
        }
    )

    costs = pd.DataFrame(
        {
            "product": [" LATTE ", "mocha"],
            "cost": [1.50, 2.00],
        }
    )

    merged, warnings = merge_cost_reference(
        sales,
        costs,
        "product",
        "cost",
    )

    assert merged["unit_cost"].tolist() == [1.50, 2.00]
    assert warnings == []
    assert sales["unit_cost"].isna().all()


def test_merge_cost_reference_warns_on_duplicate_items():
    sales = pd.DataFrame(
        {
            "item": ["Latte"],
            "unit_cost": [pd.NA],
        }
    )

    costs = pd.DataFrame(
        {
            "product": ["Latte", "latte"],
            "cost": [1.25, 1.75],
        }
    )

    merged, warnings = merge_cost_reference(
        sales,
        costs,
        "product",
        "cost",
    )

    assert merged.loc[0, "unit_cost"] == pytest.approx(1.75)
    assert any("duplicate" in warning for warning in warnings)


def test_merge_cost_reference_warns_on_unmatched_items():
    sales = pd.DataFrame(
        {
            "item": ["Latte", "Mocha"],
            "unit_cost": [pd.NA, pd.NA],
        }
    )

    costs = pd.DataFrame(
        {
            "product": ["Latte"],
            "cost": [1.50],
        }
    )

    merged, warnings = merge_cost_reference(
        sales,
        costs,
        "product",
        "cost",
    )

    assert merged.loc[0, "unit_cost"] == pytest.approx(1.50)
    assert pd.isna(merged.loc[1, "unit_cost"])
    assert any("did not match" in warning for warning in warnings)


def test_merge_cost_reference_rejects_missing_columns():
    sales = pd.DataFrame(
        {
            "item": ["Latte"],
            "unit_cost": [pd.NA],
        }
    )

    costs = pd.DataFrame({"product": ["Latte"]})

    with pytest.raises(ValueError, match="not found"):
        merge_cost_reference(
            sales,
            costs,
            "product",
            "cost",
        )
