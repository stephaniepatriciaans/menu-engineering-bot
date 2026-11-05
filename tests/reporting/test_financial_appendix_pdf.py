"""Deterministic audited POS report PDF tests."""

import re

import pytest

from reporting.financial_appendix_pdf import generate_audited_financial_pdf


def test_pdf_is_valid_and_not_empty():
    data = generate_audited_financial_pdf("Audited POS appendix\nEligible: 10.00")
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_pdf_handles_long_reports_with_page_breaks():
    data = generate_audited_financial_pdf("\n".join(f"Item {i} sales 12.00" for i in range(180)))
    assert len(re.findall(rb"/Type /Page\b", data)) >= 2


def test_pdf_rejects_empty_report():
    with pytest.raises(ValueError, match="empty"):
        generate_audited_financial_pdf(" \n")
