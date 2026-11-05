"""Safe, deterministic POS audit appendix PDF (not an AI-generated memo)."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


def generate_audited_financial_pdf(report_text: str) -> bytes:
    """Convert a validated financial appendix into a readable multi-page PDF."""
    if not report_text.strip():
        raise ValueError("Financial report cannot be empty.")
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=letter)
    width, height = letter
    x = 48
    y = height - 55
    pdf.setTitle("Audited POS Financial Appendix")
    pdf.setFont("Helvetica", 10)
    for line in report_text.splitlines():
        for visual_line in simpleSplit(line, "Helvetica", 10, width - 2 * x) or [""]:
            if y < 55:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 55
            pdf.drawString(x, y, visual_line)
            y -= 16
    pdf.save()
    return stream.getvalue()
