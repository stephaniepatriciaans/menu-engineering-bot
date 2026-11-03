"""Regression tests for POS CSV compatibility."""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_adapter import read_delimited_csv


def test_semicolon_csv_with_quoted_commas_in_header():
    """Quoted commas must not override the real separator."""
    csv_data = (
        '"Product, Full, Display, Name";date;price;units_sold\n'
        'Latte;2026-01-01;5.00;2\n'
        'Tea;2026-01-02;3.00;4\n'
    )

    uploaded = io.BytesIO(csv_data.encode("utf-8"))

    result = read_delimited_csv(uploaded)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2

    assert result.columns.tolist() == [
        "Product, Full, Display, Name",
        "date",
        "price",
        "units_sold",
    ]

    assert result.loc[0, "price"] == 5.0
    assert result.loc[1, "units_sold"] == 4


def test_utf8_bom_csv_is_supported():
    """UTF-8 BOM files should parse correctly."""
    csv_data = (
        "item,date,price,units_sold\n"
        "Latte,2026-01-01,5.00,2\n"
    )

    uploaded = io.BytesIO(
        csv_data.encode("utf-8-sig")
    )

    result = read_delimited_csv(uploaded)

    assert result.columns.tolist() == [
        "item",
        "date",
        "price",
        "units_sold",
    ]

    assert result.loc[0, "item"] == "Latte"


@pytest.mark.parametrize(
    ("delimiter", "expected"),
    [
        (",", "Latte"),
        (";", "Latte"),
        ("|", "Latte"),
        ("\t", "Latte"),
    ],
)
def test_supported_csv_delimiters(delimiter, expected):
    """All four supported delimiters must parse correctly."""
    csv_text = (
        f"item{delimiter}date{delimiter}price{delimiter}units_sold\n"
        f"Latte{delimiter}2026-01-01{delimiter}5.00{delimiter}2\n"
        f"Tea{delimiter}2026-01-02{delimiter}3.00{delimiter}4\n"
    )

    result = read_delimited_csv(
        io.BytesIO(csv_text.encode("utf-8"))
    )

    assert result.columns.tolist() == [
        "item",
        "date",
        "price",
        "units_sold",
    ]
    assert len(result) == 2
    assert result.loc[0, "item"] == expected


def test_quoted_multiline_csv_field():
    """A newline inside a quoted field must remain in that field."""
    csv_text = (
        "item,date,price,units_sold\n"
        '"Iced Latte\nLarge",2026-01-01,5.50,2\n'
        "Tea,2026-01-02,3.00,4\n"
    )

    result = read_delimited_csv(
        io.BytesIO(csv_text.encode("utf-8"))
    )

    assert len(result) == 2
    assert result.loc[0, "item"] == "Iced Latte\nLarge"
    assert result.loc[0, "price"] == 5.50
    assert result.loc[1, "item"] == "Tea"


def test_delimiter_inside_quoted_product_name():
    """A quoted delimiter is part of the name, not a separator."""
    csv_text = (
        "item;date;price;units_sold\n"
        '"Latte; Large";2026-01-01;5.50;2\n'
    )

    result = read_delimited_csv(
        io.BytesIO(csv_text.encode("utf-8"))
    )

    assert result.loc[0, "item"] == "Latte; Large"
    assert len(result.columns) == 4


def test_explicit_windows_1252_encoding():
    """Legacy POS CSV files can be decoded when explicitly requested."""
    csv_text = (
        "item,date,price,units_sold\n"
        "Café Latte,2026-01-01,5.00,2\n"
    )

    uploaded = io.BytesIO(
        csv_text.encode("cp1252")
    )

    result = read_delimited_csv(
        uploaded,
        encoding="cp1252",
    )

    assert len(result) == 1
    assert result.loc[0, "item"] == "Café Latte"


def test_invalid_utf8_is_not_silently_reinterpreted():
    """Invalid UTF-8 must fail without an explicit encoding override."""
    csv_text = (
        "item,date,price,units_sold\n"
        "Café Latte,2026-01-01,5.00,2\n"
    )

    uploaded = io.BytesIO(
        csv_text.encode("cp1252")
    )

    with pytest.raises(
        ValueError,
        match="Unable to parse",
    ):
        read_delimited_csv(uploaded)
