"""Regression tests for Excel uploads and CSV caching.

Protect against:
1. Breaking Excel worksheet selection.
2. Accidentally routing Excel uploads through the CSV cache.
3. Disabling CSV upload caching.
"""

from io import BytesIO

import pandas as pd

from ui import cached_upload, data_upload


class NamedUpload(BytesIO):
    """In-memory upload that behaves like a Streamlit UploadedFile."""

    def __init__(self, content: bytes, name: str):
        super().__init__(content)
        self.name = name


def _excel_workbook() -> bytes:
    """Create a small workbook containing two distinct worksheets."""
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "Description": ["Latte"],
                "Quantity": [2],
                "UnitPrice": [5.00],
            }
        ).to_excel(
            writer,
            sheet_name="Transactions",
            index=False,
        )

        pd.DataFrame(
            {
                "Description": ["Tea"],
                "Quantity": [3],
                "UnitPrice": [4.00],
            }
        ).to_excel(
            writer,
            sheet_name="Other",
            index=False,
        )

    return buffer.getvalue()


def test_excel_upload_respects_selected_worksheet(monkeypatch):
    """The selected worksheet must reach the Excel reader."""

    def fake_audit(_frame):
        return []

    monkeypatch.setattr(
        data_upload,
        "audit_source_transactions",
        fake_audit,
    )

    content = _excel_workbook()

    transactions, messages = data_upload.load_uploaded_sales(
        NamedUpload(content, "sales.xlsx"),
        sheet_name="Transactions",
    )

    other, other_messages = data_upload.load_uploaded_sales(
        NamedUpload(content, "sales.xlsx"),
        sheet_name="Other",
    )

    assert transactions["Description"].tolist() == ["Latte"]
    assert transactions["Quantity"].tolist() == [2]

    assert other["Description"].tolist() == ["Tea"]
    assert other["Quantity"].tolist() == [3]

    assert messages == []
    assert other_messages == []


def test_excel_upload_does_not_use_csv_cache(monkeypatch):
    """Excel workbooks must never enter the CSV caching function."""

    def forbidden_csv_cache(*_args, **_kwargs):
        raise AssertionError(
            "Excel uploads must not use cached_uploaded_sales"
        )

    monkeypatch.setattr(
        cached_upload,
        "cached_uploaded_sales",
        forbidden_csv_cache,
    )

    monkeypatch.setattr(
        data_upload,
        "audit_source_transactions",
        lambda _frame: [],
    )

    upload = NamedUpload(
        _excel_workbook(),
        "SALES.XLSX",
    )

    result, messages = data_upload.load_uploaded_sales(
        upload,
        sheet_name="Other",
    )

    assert result["Description"].tolist() == ["Tea"]
    assert messages == []


def test_csv_upload_uses_content_based_cache(monkeypatch):
    """CSV uploads must pass filename, bytes and encoding to the cache."""
    observed = {}

    expected_frame = pd.DataFrame(
        {
            "Description": ["Coffee"],
            "Quantity": [2],
            "UnitPrice": [3.50],
        }
    )
    expected_messages = ["Cached upload verified"]

    def fake_cached_upload(filename, file_bytes, encoding):
        observed["filename"] = filename
        observed["file_bytes"] = file_bytes
        observed["encoding"] = encoding

        return expected_frame, expected_messages

    def forbidden_uncached_reader(*_args, **_kwargs):
        raise AssertionError(
            "CSV upload unexpectedly bypassed the cache"
        )

    monkeypatch.setattr(
        cached_upload,
        "cached_uploaded_sales",
        fake_cached_upload,
    )

    monkeypatch.setattr(
        data_upload,
        "_load_uploaded_sales_uncached",
        forbidden_uncached_reader,
    )

    csv_bytes = (
        b"Description,Quantity,UnitPrice\n"
        b"Coffee,2,3.50\n"
    )

    upload = NamedUpload(
        csv_bytes,
        "sales.CSV",
    )

    result, messages = data_upload.load_uploaded_sales(
        upload,
        encoding="utf-8-sig",
    )

    assert observed == {
        "filename": "sales.CSV",
        "file_bytes": csv_bytes,
        "encoding": "utf-8-sig",
    }

    pd.testing.assert_frame_equal(
        result,
        expected_frame,
    )

    assert messages == expected_messages