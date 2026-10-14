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


# ================================================================
# DEPLOYMENT SAFETY — CSV UPLOAD REGRESSION TESTS
# ================================================================


def test_read_delimited_csv_rejects_file_over_200mb(tmp_path):
    """Reject oversized files without reading them into memory."""
    oversized_path = tmp_path / "oversized.csv"

    # Create a sparse file. This does not write 200 MB of CSV data.
    with oversized_path.open("wb") as file:
        file.write(b"item,price\n")
        file.truncate(200 * 1024 * 1024 + 1)

    with (
        oversized_path.open("rb") as file,
        pytest.raises(ValueError, match="200 MB"),
    ):
        read_delimited_csv(file)


def test_read_delimited_csv_accepts_200_columns():
    """Accept a CSV at the supported column-count boundary."""
    headers = [f"column_{i}" for i in range(200)]
    values = ["1"] * 200

    csv_text = (
        ",".join(headers)
        + "\n"
        + ",".join(values)
        + "\n"
    )

    result = read_delimited_csv(
        io.BytesIO(csv_text.encode("utf-8"))
    )

    assert len(result.columns) == 200
    assert len(result) == 1


def test_read_delimited_csv_rejects_more_than_200_columns():
    """Reject datasets that exceed the column-count limit."""
    headers = [f"column_{i}" for i in range(201)]
    values = ["1"] * 201

    csv_text = (
        ",".join(headers)
        + "\n"
        + ",".join(values)
        + "\n"
    )

    with pytest.raises(ValueError, match="too many columns"):
        read_delimited_csv(
            io.BytesIO(csv_text.encode("utf-8"))
        )


def test_read_delimited_csv_accepts_utf8_bom():
    """Read UTF-8 CSVs containing a byte-order mark."""
    csv_bytes = (
        "item,price\n"
        "Latte,5.50\n"
    ).encode("utf-8-sig")

    result = read_delimited_csv(io.BytesIO(csv_bytes))

    assert result.columns.tolist() == ["item", "price"]
    assert result.loc[0, "item"] == "Latte"


def test_read_delimited_csv_rejects_invalid_utf8():
    """Report an understandable error for invalid UTF-8 files."""
    invalid_csv = b"item,price\nLatte,\xff\n"

    with pytest.raises(ValueError, match="Unable to parse"):
        read_delimited_csv(io.BytesIO(invalid_csv))


def test_read_delimited_csv_rejects_more_than_500k_rows(
    monkeypatch,
):
    """Stop processing once the cumulative row limit is exceeded."""
    sample_chunk = pd.DataFrame(
        {"item": ["Latte"] * 25_000}
    )

    def fake_read_csv(*args, **kwargs):
        del args, kwargs

        # 21 chunks * 25,000 rows = 525,000 rows.
        for _ in range(21):
            yield sample_chunk

    monkeypatch.setattr(
        pd,
        "read_csv",
        fake_read_csv,
    )

    with pytest.raises(ValueError, match="too many rows"):
        read_delimited_csv(
            io.BytesIO(b"item,price\nLatte,5.50\n")
        )


def test_read_delimited_csv_handles_multiple_chunks(
    monkeypatch,
):
    """Concatenate parsed chunks in their original order."""
    chunks = [
        pd.DataFrame({
            "item": ["Latte"],
            "price": [5.50],
        }),
        pd.DataFrame({
            "item": ["Mocha"],
            "price": [6.00],
        }),
    ]

    def fake_read_csv(*args, **kwargs):
        del args, kwargs
        return iter(chunks)

    monkeypatch.setattr(
        pd,
        "read_csv",
        fake_read_csv,
    )

    result = read_delimited_csv(
        io.BytesIO(b"item,price\nLatte,5.50\n")
    )

    assert result["item"].tolist() == [
        "Latte",
        "Mocha",
    ]
    assert result["price"].tolist() == [
        5.50,
        6.00,
    ]
