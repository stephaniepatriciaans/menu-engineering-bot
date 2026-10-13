"""Generate universal, professionally formatted PDF decision memos."""

from __future__ import annotations

import io
import re
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

PRIMARY_COLOR = colors.HexColor("#243047")
SECONDARY_COLOR = colors.HexColor("#64748b")
DIVIDER_COLOR = colors.HexColor("#E2E8F0")

DUPLICATE_TITLES = {
    "menu pricing decision memo",
    "menu engineering decision memo",
    "menu decision memo",
}


# --------------------------------------------------
# Markdown helpers
# --------------------------------------------------

def format_inline(text: str) -> str:
    """Convert basic Markdown emphasis to ReportLab formatting."""

    text = str(text)

    # Remove unwanted spaces before punctuation.
    text = re.sub(r"\s+([,;:!?])", r"\1", text)

    # Remove unnecessary spaces inside parentheses.
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)

    replacements = {
        "\u2192": " to ",
        "\u2022": "-",
        "\u2014": " - ",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u200b": "",
        "\u00a0": " ",
    }

    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    text = escape(text)

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text,
    )

    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"<i>\1</i>",
        text,
    )

    return text


def is_markdown_divider(line: str) -> bool:
    """Detect common Markdown horizontal rules."""
    return bool(
        re.fullmatch(
            r"(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,}",
            line.strip(),
        )
    )


def is_duplicate_title(heading: str) -> bool:
    """Identify memo titles already represented by the PDF header."""
    normalized = re.sub(
        r"\s+",
        " ",
        heading.strip().casefold(),
    )
    return normalized in DUPLICATE_TITLES


def parse_heading(line: str) -> tuple[int, str] | None:
    """
    Parse standard Markdown headings.

    Returns:
        (level, heading text), or None
    """
    match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)

    if not match:
        return None

    return len(match.group(1)), match.group(2).strip()


# --------------------------------------------------
# PDF styles
# --------------------------------------------------

def create_pdf_styles() -> dict:
    """Create typography for different heading levels."""

    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        name="MemoTitleCustom",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=10,
    )

    styles["metadata"] = ParagraphStyle(
        name="MemoMetadataCustom",
        parent=base["Normal"],
        fontSize=9,
        leading=13,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    heading_sizes = {
        1: (14, 18),
        2: (12, 16),
        3: (10.5, 14),
        4: (9.5, 13),
        5: (9, 12),
        6: (9, 12),
    }

    for level, (size, leading) in heading_sizes.items():
        styles[f"heading_{level}"] = ParagraphStyle(
            name=f"MemoHeadingLevel{level}",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=size,
            leading=leading,
            textColor=PRIMARY_COLOR,
            spaceBefore=11 if level <= 2 else 7,
            spaceAfter=5,
            keepWithNext=True,
        )

    styles["body"] = ParagraphStyle(
        name="MemoBodyCustom",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=PRIMARY_COLOR,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    styles["bullet"] = ParagraphStyle(
        name="MemoBulletCustom",
        parent=styles["body"],
        leftIndent=17,
        firstLineIndent=-11,
        spaceAfter=4,
    )

    styles["footer"] = ParagraphStyle(
        name="MemoFooterCustom",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER,
    )

    return styles


# --------------------------------------------------
# Universal section grouping
# --------------------------------------------------

def estimate_section_height(
    elements: list,
    available_width: float,
    available_height: float,
) -> float:
    """
    Estimate rendered section height using ReportLab.

    More reliable than counting paragraphs because actual
    text lengths and wrapping affect the page layout.
    """
    total = 0.0

    for element in elements:
        try:
            _, height = element.wrap(
                available_width,
                available_height,
            )

            total += height
            total += element.getSpaceBefore()
            total += element.getSpaceAfter()

        except (AttributeError, ValueError):
            return available_height

    return total


def group_memo_sections(
    sections: list[tuple[int | None, list]],
    available_width: float,
    available_height: float,
) -> list:
    """
    Group short subsections without forcing long ones
    onto a single page.

    Major sections (levels 1-2) flow naturally.
    Subsections (levels 3-6) may be kept together
    when their estimated height is comfortably small.
    """
    result = []

    for level, elements in sections:
        if not elements:
            continue

        height = estimate_section_height(
            elements,
            available_width,
            available_height,
        )

        is_subsection = level is not None and level >= 3

        if is_subsection and height <= available_height * 0.60:
            result.append(KeepTogether(elements))
        else:
            # Heading styles already use keepWithNext=True,
            # preventing an orphaned heading in normal cases.
            result.extend(elements)

    return result


# --------------------------------------------------
# Page footer
# --------------------------------------------------

def draw_page_footer(canvas, doc) -> None:
    """Display page numbers on every page."""

    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SECONDARY_COLOR)

    canvas.drawRightString(
        letter[0] - 0.70 * inch,
        0.38 * inch,
        f"Page {canvas.getPageNumber()}",
    )

    canvas.restoreState()


# --------------------------------------------------
# Main PDF generation
# --------------------------------------------------

def generate_memo_pdf(
    memo: str,
    business_name: str,
    dataset_name: str,
) -> bytes:
    """
    Generate a PDF from any supported AI decision memo.

    The layout is based on Markdown structure, not on
    a particular CSV, business, product, or category.
    """

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.70 * inch,
        leftMargin=0.70 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Menu Engineering Decision Memo",
        author="Menu Engineering Bot",
    )

    styles = create_pdf_styles()
    story = []

    # Report header
    story.append(
        Paragraph(
            "MENU ENGINEERING DECISION MEMO",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            format_inline(business_name),
            styles["metadata"],
        )
    )

    story.append(
        Paragraph(
            "Dataset: " + format_inline(dataset_name),
            styles["metadata"],
        )
    )

    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime("%B %d, %Y"),
            styles["metadata"],
        )
    )

    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=DIVIDER_COLOR,
        )
    )
    story.append(Spacer(1, 8))

    # Parse Markdown into blocks grouped by heading.
    sections: list[tuple[int | None, list]] = []
    current_level: int | None = None
    current_elements: list = []

    def flush_section() -> None:
        nonlocal current_elements

        if current_elements:
            sections.append(
                (current_level, current_elements)
            )
            current_elements = []

    for raw_line in memo.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        heading_info = parse_heading(line)

        if heading_info:
            level, heading = heading_info

            if is_duplicate_title(heading):
                continue

            flush_section()
            current_level = level

            current_elements.append(
                Paragraph(
                    format_inline(heading),
                    styles[f"heading_{level}"],
                )
            )
            continue

        if is_markdown_divider(line):
            flush_section()
            current_level = None

            sections.append((
                None,
                [
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=DIVIDER_COLOR,
                        spaceBefore=5,
                        spaceAfter=6,
                    )
                ],
            ))
            continue

        if line.startswith(("- ", "* ")):
            current_elements.append(
                Paragraph(
                    "&#8226; " + format_inline(line[2:]),
                    styles["bullet"],
                )
            )
            continue

        if re.match(r"^\d+\.\s+", line):
            current_elements.append(
                Paragraph(
                    format_inline(line),
                    styles["bullet"],
                )
            )
            continue

        current_elements.append(
            Paragraph(
                format_inline(line),
                styles["body"],
            )
        )

    flush_section()

    # Calculate usable page size.
    available_width = doc.width
    available_height = doc.height

    # Apply adaptive, dataset-independent grouping.
    story.extend(
        group_memo_sections(
            sections,
            available_width,
            available_height,
        )
    )

    # Closing disclaimer
    disclaimer = Paragraph(
        "AI-generated report based on application calculations. "
        "Pricing recommendations and elasticity estimates "
        "require independent business validation.",
        styles["footer"],
    )

    story.append(
        KeepTogether([
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=DIVIDER_COLOR,
            ),
            Spacer(1, 7),
            disclaimer,
        ])
    )

    doc.build(
        story,
        onFirstPage=draw_page_footer,
        onLaterPages=draw_page_footer,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
