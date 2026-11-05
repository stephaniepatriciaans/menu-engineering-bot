"""Workbook ingestion keeps raw transaction evidence and worksheet selection."""

from io import BytesIO

import pandas as pd
import pytest

from data_pipeline.excel_import import list_excel_sheets, read_excel_sales


def _workbook() -> BytesIO:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({
            "InvoiceNo": ["1001", "C1001"],
            "Description": ["Latte", "Latte"],
            "Quantity": [2, -2],
            "UnitPrice": [5.0, 5.0],
        }).to_excel(writer, sheet_name="Transactions", index=False)
        pd.DataFrame({"Description": ["Tea"], "Quantity": [1]}).to_excel(
            writer, sheet_name="Other", index=False
        )
    buf.seek(0)
    return buf


def test_sheet_names_and_selected_sheet_preserve_negative_quantities():
    stream = _workbook()
    assert list_excel_sheets(stream) == ["Transactions", "Other"]
    frame = read_excel_sales(stream, sheet_name="Transactions")
    assert frame["Quantity"].tolist() == [2, -2]
    assert frame["Description"].tolist() == ["Latte", "Latte"]
    assert frame.columns.tolist() == ["InvoiceNo", "Description", "Quantity", "UnitPrice"]


def test_sheet_selection_works_after_other_read():
    stream = _workbook()
    list_excel_sheets(stream)
    other = read_excel_sales(stream, sheet_name="Other")
    assert len(other) == 1
    assert other.at[0, "Description"] == "Tea"


def test_unknown_sheet_rejected():
    with pytest.raises(ValueError, match="does not exist"):
        read_excel_sales(_workbook(), sheet_name="Missing")


def test_empty_or_invalid_workbook_rejected():
    with pytest.raises(ValueError, match="empty"):
        read_excel_sales(BytesIO())
    with pytest.raises(ValueError, match="Cannot read"):
        read_excel_sales(BytesIO(b"not an xlsx"))


def test_blank_sheet_rejected():
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(columns=["date", "item"]).to_excel(writer, index=False)
    with pytest.raises(ValueError, match="no transaction rows"):
        read_excel_sales(buf)
