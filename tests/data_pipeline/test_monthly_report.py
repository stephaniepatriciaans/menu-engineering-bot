"""Synthetic, non-confidential fixtures for monthly menu-report preservation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.monthly_report import (
    SOURCE_COLUMNS,
    category_performance,
    item_performance,
    load_monthly_reports,
    monthly_overview,
    read_monthly_report,
)


def _workbook(path: Path, period: str, *, corrupt: bool = False) -> Path:
    raw = pd.DataFrame([[None] * len(SOURCE_COLUMNS) for _ in range(13)])
    raw.iat[0, 0] = "Sales Menu Recapitulation Report"
    raw.iat[1, 0] = "Synthetic Fixture"
    raw.iat[4, 0] = "Period"
    raw.iat[4, 1] = period
    raw.iloc[9] = list(SOURCE_COLUMNS)
    records = [
        ["BEVERAGE", "COFFEE", "Latte", "Latte", None, "CODE-1", "Ala Carte", None, "POS", 2, 5, 10, 1, 1, 8, 0, 0.8, 0, 8.8],
        ["BEVERAGE", "TEA", "Tea", "Tea", None, "CODE-1", "Ala Carte", None, "MO&P", 3, -1, 12, 0, 0, 12, 0, 1.2, 0, 13.2],
        ["BEVERAGE", "COFFEE", "Latte", "Latte", None, "CODE-1", "Ala Carte", None, "POS", 1, 5, 5, 0, 0, 5, 0, 0.5, 0, 5.5],
    ]
    if corrupt:
        records[0][14] = 999
    for idx, record in enumerate(records, start=10):
        raw.iloc[idx] = record
    raw.to_excel(path, sheet_name="Report", header=False, index=False)
    return path


def test_read_preserves_rows_and_flags_anomalies(tmp_path):
    path = _workbook(tmp_path / "aug.xlsx", "01-08-2026 - 31-08-2026")
    result = read_monthly_report(path)
    assert len(result.rows) == 3
    assert result.rows["source_excel_row"].tolist() == [11, 12, 13]
    assert result.audit.loc[0, "negative_reported_unit_prices"] == 1
    assert result.audit.loc[0, "repeated_identity_rows"] == 2
    assert result.rows["Unit Price"].tolist() == [5, -1, 5]
    assert result.rows["period_start"].iloc[0].isoformat() == "2026-08-01"


def test_aggregations_never_merge_different_names_or_channels(tmp_path):
    result = read_monthly_report(_workbook(tmp_path / "aug.xlsx", "01-08-2026 - 31-08-2026"))
    items = item_performance(result.rows)
    assert len(items) == 2
    latte = items.loc[items["Menu"].eq("Latte")].iloc[0]
    assert latte["units_sold"] == 3
    assert latte["reported_net_sales"] == 13
    assert monthly_overview(result.rows).loc[0, "reported_net_sales"] == 25
    assert category_performance(result.rows)["units_sold"].sum() == 6


def test_multiple_months_remain_distinct(tmp_path):
    aug = _workbook(tmp_path / "aug.xlsx", "01-08-2026 - 31-08-2026")
    sep = _workbook(tmp_path / "sep.xlsx", "01-09-2026 - 30-09-2026")
    result = load_monthly_reports([sep, aug])
    assert len(result.rows) == 6
    assert len(monthly_overview(result.rows)) == 2
    assert result.audit["period_start"].tolist()[0].month == 8


def test_duplicate_month_rejected(tmp_path):
    aug1 = _workbook(tmp_path / "aug1.xlsx", "01-08-2026 - 31-08-2026")
    aug2 = _workbook(tmp_path / "aug2.xlsx", "01-08-2026 - 31-08-2026")
    with pytest.raises(ValueError, match="same month"):
        load_monthly_reports([aug1, aug2])


def test_broken_accounting_rejected(tmp_path):
    path = _workbook(tmp_path / "bad.xlsx", "01-08-2026 - 31-08-2026", corrupt=True)
    with pytest.raises(ValueError, match="do not reconcile"):
        read_monthly_report(path)


def test_no_daily_or_transaction_data_created(tmp_path):
    result = read_monthly_report(_workbook(tmp_path / "aug.xlsx", "01-08-2026 - 31-08-2026"))
    for column in ("date", "transaction_id", "unit_cost", "daily_sales", "predicted_demand"):
        assert column not in result.rows.columns


def test_no_workbooks_rejected():
    with pytest.raises(ValueError, match="No monthly"):
        load_monthly_reports([])


def test_uploaded_file_like_workbook(tmp_path):
    path = _workbook(tmp_path / "aug.xlsx", "01-08-2026 - 31-08-2026")
    upload = BytesIO(path.read_bytes())
    upload.name = "aug.xlsx"
    report = load_monthly_reports([upload])
    assert report.audit.loc[0, "summary_rows"] == 3
    assert report.rows["source_file"].unique().tolist() == ["aug.xlsx"]
