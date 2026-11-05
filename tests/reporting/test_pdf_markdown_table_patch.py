"""Ensure Markdown pipe tables become ReportLab tables."""

from __future__ import annotations

from reportlab.platypus import Table

from reporting.pdf_report import (
    create_pdf_styles,
    generate_memo_pdf,
    make_markdown_table,
)


def test_markdown_table_is_a_real_table_and_exports_to_pdf():
    rows = [
        "| Item | Revenue | Confidence |",
        "| **PARTY BUNTING** | £99,504.33 | High |",
        "| RABBIT NIGHT LIGHT | £66,964.99 | High |",
    ]
    table = make_markdown_table(rows, create_pdf_styles(), 470)
    assert isinstance(table, Table)
    assert table.repeatRows == 1
    assert len(table._cellvalues) == 3

    markdown = "## Evidence\n\n" + rows[0] + "\n|---|---|---|\n" + "\n".join(rows[1:])
    result = generate_memo_pdf(markdown, "Example Shop", "Retail Sample")
    assert result.startswith(b"%PDF-")
    assert len(result) > 1000
