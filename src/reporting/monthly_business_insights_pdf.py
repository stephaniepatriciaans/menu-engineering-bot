"""Privacy-preserving PDF export for monthly menu sales and Business Insights.

All content is derived from monthly summary rows; no transaction-level or
profit calculations are inferred. PDF bytes are built entirely in memory.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from analytics.monthly_business_insights import build_monthly_business_insights
from data_pipeline.monthly_report import monthly_overview

_NAVY = colors.HexColor("#122138")
_BLUE = colors.HexColor("#2272A5")
_MUTED = colors.HexColor("#526176")
_PALE = colors.HexColor("#EAF2F7")
_BORDER = colors.HexColor("#DDE5ED")


def _register_fonts() -> tuple[str, str]:
    """Use Unicode TrueType fonts when available; fall back safely."""
    regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    # A cross-platform search also covers common Mac and Windows installations.
    candidates = [
        (regular, bold),
        (Path("/Library/Fonts/Arial Unicode.ttf"), Path("/Library/Fonts/Arial Unicode.ttf")),
        (Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    ]
    for reg, heavy in candidates:
        if reg.is_file() and heavy.is_file():
            if "MonthlyPDFRegular" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("MonthlyPDFRegular", str(reg)))
                pdfmetrics.registerFont(TTFont("MonthlyPDFBold", str(heavy)))
            return "MonthlyPDFRegular", "MonthlyPDFBold"
    return "Helvetica", "Helvetica-Bold"


def _currency(value: float, language: str) -> str:
    rounded = f"{float(value):,.0f}"
    if language == "id":
        rounded = rounded.replace(",", ".")
    return f"Rp {rounded}"


def _quantity(value: float, language: str) -> str:
    rendered = f"{float(value):,.0f}"
    return rendered.replace(",", ".") if language == "id" else rendered


def _month(value: object, language: str) -> str:
    stamp = pd.Timestamp(str(value))
    if language == "id":
        names = (
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        )
        return f"{names[stamp.month - 1]} {stamp.year}"
    return stamp.strftime("%b %Y")


def build_monthly_business_insights_pdf(
    rows: pd.DataFrame,
    *,
    language: str = "en",
    top_n: int = 8,
) -> bytes:
    """Build an in-memory PDF from validated monthly report rows.

    Rows must come from the validated monthly-report importer. Product rankings
    preserve menu code, name, category, and subcategory; sales channels combine
    only for an exact match. No user data is saved to disk or sent externally.
    """
    if language not in {"en", "id"}:
        raise ValueError("language must be 'en' or 'id'")
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if rows.empty:
        raise ValueError("Cannot export an empty monthly report")

    overview = monthly_overview(rows).sort_values("period_start").reset_index(drop=True)
    if overview.empty:
        raise ValueError("Cannot export an empty monthly report")
    commentary = build_monthly_business_insights(rows, language=language)
    font, font_bold = _register_fonts()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PDFTitle", parent=styles["Title"], fontName=font_bold,
        fontSize=19, leading=25, textColor=_NAVY, spaceAfter=9, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="PDFHeading", fontName=font_bold, fontSize=11, leading=16,
        textColor=_NAVY, spaceBefore=16, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="PDFBody", fontName=font, fontSize=9, leading=14,
        textColor=_NAVY, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="PDFSmall", fontName=font, fontSize=7.5, leading=11,
        textColor=_MUTED, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="PDFCell", fontName=font, fontSize=8, leading=12,
        textColor=_NAVY,
    ))
    styles.add(ParagraphStyle(
        name="PDFCellHead", parent=styles["PDFCell"], fontName=font_bold,
        textColor=colors.white,
    ))

    t = {
        "title": "Laporan Wawasan Bisnis Bulanan" if language == "id" else "Monthly Business Insights Report",
        "period": "Periode" if language == "id" else "Period",
        "summary": "Ringkasan Penjualan" if language == "id" else "Sales Summary",
        "month": "Bulan" if language == "id" else "Month",
        "units": "Unit tercatat" if language == "id" else "Recorded units",
        "net": "Penjualan bersih" if language == "id" else "Net sales",
        "total": "Total keseluruhan" if language == "id" else "Grand total",
        "detail": "Kinerja Bulanan" if language == "id" else "Monthly Performance",
        "products": "Kontributor Pendapatan Produk" if language == "id" else "Product Revenue Contributors",
        "popular": "Item dengan Volume Tertinggi" if language == "id" else "Highest-Volume Menu Entries",
        "categories": "Kategori berdasarkan Volume" if language == "id" else "Categories by Recorded Volume",
        "popular_note": ("Termasuk tambahan dan entri paket; kuantitas bukan jumlah pesanan pelanggan." if language == "id" else "Includes modifiers and bundled entries; quantities are not customer orders."),
        "category": "Kategori" if language == "id" else "Category",
        "item": "Menu" if language == "id" else "Menu item",
        "insights": "Analisis dan Tindak Lanjut" if language == "id" else "Insights and Next Checks",
        "next": "Langkah selanjutnya: " if language == "id" else "Next check: ",
        "limits": (
            "Data merupakan ringkasan menu bulanan. Unit bukan jumlah transaksi atau pelanggan unik. "
            "Nominal adalah nilai yang dilaporkan sistem, bukan laba. Item komponen, paket, "
            "dan promosi dapat muncul dalam pemeringkatan. Tidak ada penyebab perubahan penjualan "
            "yang dapat dipastikan hanya dari data ini."
            if language == "id" else
            "Data are monthly menu summaries. Units are not distinct transactions or customers. "
            "Financial amounts are source-reported, not profit. Components, bundles and promotions "
            "may appear in rankings. The data alone cannot establish causes of sales changes."
        ),
        "candidate": (
            "Kandidat berdasarkan kategori BEVERAGE/FOOD; belum diverifikasi sebagai produk mandiri."
            if language == "id" else
            "Candidates based on BEVERAGE/FOOD category; not verified as standalone retail items."
        ),
        "disclaimer": "Catatan Interpretasi" if language == "id" else "Interpretation Notes",
    }

    start, end = overview.iloc[0], overview.iloc[-1]
    period_line = f"{_month(start['period_start'], language)} - {_month(end['period_start'], language)}"
    buffer = BytesIO()

    def footer(canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.setStrokeColor(_BORDER)
        canvas.line(42, 43, 553, 43)
        canvas.setFont(font, 7)
        canvas.setFillColor(_MUTED)
        canvas.drawString(42, 31, "Menu Engineering Bot  |  Monthly summary reports")
        canvas.drawRightString(553, 31, f"{doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=(595.28, 841.89),
        leftMargin=42, rightMargin=42, topMargin=46, bottomMargin=56,
        title=t["title"],
        author="Menu Engineering Bot",
    )
    frame = Frame(42, 56, 511.28, 739.89, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Report", frames=[frame], onPage=footer))
    story = []

    def paragraph(value: object, style: str = "PDFBody") -> Paragraph:
        return Paragraph(escape(str(value)), styles[style])

    def add_table(headers: list[str], body: list[list[object]], widths: list[float]) -> None:
        values = [[paragraph(x, "PDFCellHead") for x in headers]]
        values.extend([[paragraph(v, "PDFCell") for v in row] for row in body])
        table = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, _BLUE),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)

    story.append(paragraph(t["title"], "PDFTitle"))
    story.append(paragraph(f"{t['period']}: {period_line}", "PDFSmall"))
    story.append(Spacer(1, 9))
    story.append(paragraph(t["summary"], "PDFHeading"))
    total_units = float(overview["units_sold"].sum())
    total_net = float(overview["reported_net_sales"].sum())
    total_grand = float(overview["reported_grand_total"].sum())
    add_table(
        [t["net"], t["units"], t["total"]],
        [[_currency(total_net, language), _quantity(total_units, language), _currency(total_grand, language)]],
        [188, 135, 188],
    )

    story.append(paragraph(t["detail"], "PDFHeading"))
    add_table(
        [t["month"], t["units"], f"{t['net']} (IDR)"],
        [[_month(r["period_start"], language), _quantity(r["units_sold"], language),
          _currency(r["reported_net_sales"], language)] for _, r in overview.iterrows()],
        [130, 116, 265],
    )

    if len(overview) <= 24:
        # A small chart is sufficient for month-level reporting, with values
        # taken directly from the already aggregated monthly overview.
        n = len(overview)
        chart = Drawing(511, 138)
        maximum = max(1.0, float(overview["reported_net_sales"].max()))
        spacing = 511 / n
        bar_width = min(45, spacing * 0.54)
        for index, (_, month_row) in enumerate(overview.iterrows()):
            net = float(month_row["reported_net_sales"])
            height = 93 * max(0.0, net) / maximum
            center = (index + 0.5) * spacing
            chart.add(Rect(center - bar_width / 2, 29, bar_width, height,
                           fillColor=_BLUE, strokeColor=None))
            chart.add(String(center, 16, _month(month_row["period_start"], language),
                             fontName=font, fontSize=7, textAnchor="middle"))
            chart.add(String(center, 124, _currency(net, language),
                             fontName=font, fontSize=7, textAnchor="middle"))
        story.append(Spacer(1, 10))
        story.append(chart)

    dims = ["Menu Code", "Menu", "Menu Category", "Menu Category Detail"]
    category = rows["Menu Category"].fillna("").astype(str).str.strip().str.upper()
    candidates = rows.loc[category.str.startswith("BEVERAGE") | category.eq("FOOD")]
    if not candidates.empty:
        ranked = (
            candidates.groupby(dims, dropna=False, as_index=False)
            .agg(units=("Qty", "sum"), net_sales=("Net Sales Total", "sum"))
            .sort_values(["net_sales", "units"], ascending=[False, False])
            .head(top_n)
        )
        story.append(paragraph(t["products"], "PDFHeading"))
        story.append(paragraph(t["candidate"], "PDFSmall"))
        add_table(
            [t["item"], t["units"], f"{t['net']} (IDR)"],
            [[str(r["Menu"]), _quantity(r["units"], language),
              _currency(r["net_sales"], language)] for _, r in ranked.iterrows()],
            [246, 92, 173],
        )

    popular = (
        rows.groupby(dims, dropna=False, as_index=False)
        .agg(units=("Qty", "sum"), net_sales=("Net Sales Total", "sum"))
        .sort_values(["units", "net_sales"], ascending=[False, False])
        .head(top_n)
    )
    story.append(paragraph(t["popular"], "PDFHeading"))
    story.append(paragraph(t["popular_note"], "PDFSmall"))
    add_table(
        [t["item"], t["units"], f"{t['net']} (IDR)"],
        [[str(r["Menu"]), _quantity(r["units"], language),
          _currency(r["net_sales"], language)] for _, r in popular.iterrows()],
        [246, 92, 173],
    )

    category_totals = (
        rows.groupby("Menu Category", dropna=False, as_index=False)
        .agg(units=("Qty", "sum"), net_sales=("Net Sales Total", "sum"))
        .sort_values("units", ascending=False)
        .head(8)
    )
    story.append(paragraph(t["categories"], "PDFHeading"))
    add_table(
        [t["category"], t["units"], f"{t['net']} (IDR)"],
        [[str(r["Menu Category"]), _quantity(r["units"], language),
          _currency(r["net_sales"], language)] for _, r in category_totals.iterrows()],
        [246, 92, 173],
    )

    story.append(paragraph(t["insights"], "PDFHeading"))
    for insight in commentary:
        story.append(KeepTogether([
            paragraph(insight.heading, "PDFHeading"),
            paragraph(insight.observation),
            paragraph(t["next"] + insight.next_step, "PDFSmall"),
        ]))

    doc.build(story)
    return buffer.getvalue()
