"""Load uploaded Excel workbooks without modifying the source transactions."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd


def _read_bytes(uploaded: BinaryIO) -> bytes:
    """Read a Streamlit upload from the beginning, independent of cursor state."""
    uploaded.seek(0)
    payload = uploaded.read()
    if not payload:
        raise ValueError("The uploaded Excel workbook is empty.")
    return payload


def list_excel_sheets(uploaded: BinaryIO) -> list[str]:
    """Return worksheet names in their original workbook order."""
    try:
        with pd.ExcelFile(BytesIO(_read_bytes(uploaded)), engine="openpyxl") as book:
            return book.sheet_names
    except Exception as exc:
        raise ValueError(f"Cannot inspect the Excel workbook: {exc}") from exc


def read_excel_sales(uploaded: BinaryIO, *, sheet_name: str | None = None) -> pd.DataFrame:
    """Read one worksheet, retaining original column names and signed records.

    Excel values are imported, not recalculated; formulas without cached values
    can appear missing. Source datasets are never modified by this function.
    """
    data = _read_bytes(uploaded)
    try:
        with pd.ExcelFile(BytesIO(data), engine="openpyxl") as book:
            names = book.sheet_names
            if not names:
                raise ValueError("The workbook does not contain any worksheets.")
            selected = names[0] if sheet_name is None else sheet_name
            if selected not in names:
                raise ValueError(f"Worksheet {selected!r} does not exist. Available: {names}")
            frame = pd.read_excel(book, sheet_name=selected)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Cannot read the Excel workbook: {exc}") from exc

    if frame.empty:
        raise ValueError("The selected worksheet has no transaction rows.")
    if not frame.columns.is_unique:
        raise ValueError("The selected worksheet contains duplicate column names.")
    return frame
