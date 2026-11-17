"""PDF report tests with fully synthetic, nonconfidential monthly sales rows."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from reporting.monthly_business_insights_pdf import build_monthly_business_insights_pdf


def _rows() -> pd.DataFrame:
    entries = []
    for period, latte, food in [
        (date(2026, 8, 1), 50, 20),
        (date(2026, 9, 1), 80, 25),
    ]:
        for code, name, category, units, revenue in [
            ("A", "Iced Latte", "BEVERAGE", latte, latte * 25_000),
            ("B", "Long Matcha Name with < & >", "BEVERAGE", 10, 450_000),
            ("C", "Makanan Manis", "FOOD", food, food * 21_000),
            ("D", "Add Ice", "ADDITIONAL", 130, 0),
        ]:
            entries.append({
                "period_start": period,
                "period_end": period,
                "Menu Code": code,
                "Menu": name,
                "Menu Category": category,
                "Menu Category Detail": category,
                "Sales Type": "POS",
                "Qty": units,
                "Net Sales Total": revenue,
                "Grand Total": revenue,
                "Subtotal": revenue,
                "Menu Discount Total": 0,
                "Bill Discount Total": 0,
                "Tax Total": 0,
                "VAT Total": 0,
                "Service Charge Total": 0,
            })
    return pd.DataFrame(entries)


@pytest.mark.parametrize("language", ["en", "id"])
def test_pdf_export_is_real_pdf_and_reproducible(language: str) -> None:
    first = build_monthly_business_insights_pdf(_rows(), language=language)
    second = build_monthly_business_insights_pdf(_rows(), language=language)
    assert first.startswith(b"%PDF-")
    assert len(first) > 3_000
    assert second.startswith(b"%PDF-")


def test_pdf_export_handles_long_table_rows() -> None:
    data = _rows()
    data.loc[data["Menu Code"] == "B", "Menu"] = "Café " + "Very long name & milk " * 30
    content = build_monthly_business_insights_pdf(data, top_n=4)
    assert content.startswith(b"%PDF-")


def test_pdf_export_does_not_modify_input() -> None:
    data = _rows()
    original = data.copy(deep=True)
    build_monthly_business_insights_pdf(data, language="id")
    pd.testing.assert_frame_equal(data, original)


def test_pdf_export_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError, match="language"):
        build_monthly_business_insights_pdf(_rows(), language="es")
    with pytest.raises(ValueError, match="top_n"):
        build_monthly_business_insights_pdf(_rows(), top_n=0)
    with pytest.raises(ValueError, match="empty"):
        build_monthly_business_insights_pdf(_rows().iloc[:0])
