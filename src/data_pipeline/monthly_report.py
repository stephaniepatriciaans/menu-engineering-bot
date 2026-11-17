"""Read-only importer and analysis for monthly *aggregated* menu-sales reports.

This module deliberately does not produce transaction-level data, daily dates,
unit prices, product margins, or forecasts. Original financial columns are kept.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

SOURCE_COLUMNS = (
    "Menu Category", "Menu Category Detail", "Menu", "Menu Short Name",
    "Menu Custom Name", "Menu Code", "Menu Info", "Menu Bundling",
    "Sales Type", "Qty", "Unit Price", "Subtotal",
    "Menu Discount Total", "Bill Discount Total", "Net Sales Total",
    "Service Charge Total", "Tax Total", "VAT Total", "Grand Total",
)
FINANCIAL_COLUMNS = (
    "Subtotal", "Menu Discount Total", "Bill Discount Total",
    "Net Sales Total", "Service Charge Total", "Tax Total", "VAT Total",
    "Grand Total",
)
NUMERIC_COLUMNS = ("Qty", "Unit Price", *FINANCIAL_COLUMNS)
IDENTITY_COLUMNS = (
    "Menu Code", "Menu", "Menu Category", "Menu Category Detail", "Sales Type"
)
HEADER_ROW = 9  # Zero-based: Excel row 10.


@dataclass(frozen=True)
class MonthlyReport:
    """Preserved source rows, period metadata, and read-only audit summary."""

    rows: pd.DataFrame
    audit: pd.DataFrame


def _period_from_workbook(raw: pd.DataFrame, filename: str) -> tuple[date, date]:
    metadata = raw.iloc[:HEADER_ROW, :2]
    period_rows = metadata.loc[
        metadata.iloc[:, 0].astype("string").str.strip().eq("Period")
    ]
    if len(period_rows) != 1:
        raise ValueError(f"{filename}: expected exactly one Period metadata row")
    period = str(period_rows.iloc[0, 1]).strip()
    match = re.fullmatch(r"(\d{2}-\d{2}-\d{4})\s*-\s*(\d{2}-\d{2}-\d{4})", period)
    if match is None:
        raise ValueError(f"{filename}: unexpected report period format: {period!r}")
    start, end = (datetime.strptime(value, "%d-%m-%Y").date() for value in match.groups())
    if start > end or start.year != end.year or start.month != end.month:
        raise ValueError(f"{filename}: report period is not a single calendar month")
    if start.day != 1 or (end + pd.Timedelta(days=1)).day != 1:
        raise ValueError(f"{filename}: report period must cover a complete calendar month")
    return start, end


def read_monthly_report(path: str | Path | BytesIO, *, tolerance: float = 1.0,) -> MonthlyReport:
    """Read one report without altering or inferring any source financial values.

    Fails closed on missing fields, invalid numeric data, or unbalanced financial
    identities. A negative 'Unit Price' is flagged, not silently corrected.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    filename = getattr(path, "name", None) or str(path)
    filename = Path(str(filename)).name
    raw = pd.read_excel(path, sheet_name="Report", header=None)
    if len(raw) <= HEADER_ROW or raw.shape[1] != len(SOURCE_COLUMNS):
        raise ValueError(f"{filename}: unexpected report layout")
    actual_headers = tuple(str(v).strip() for v in raw.iloc[HEADER_ROW, :].tolist())
    if actual_headers != SOURCE_COLUMNS:
        raise ValueError(f"{filename}: unexpected column headers; no implicit remapping")
    period_start, period_end = _period_from_workbook(raw, filename)
    frame = raw.iloc[HEADER_ROW + 1 :].copy().reset_index(drop=True)
    frame.columns = list(SOURCE_COLUMNS)
    if frame.empty:
        raise ValueError(f"{filename}: no menu-summary rows")
    if frame["Menu"].isna().any() or frame["Menu Code"].isna().any():
        raise ValueError(f"{filename}: missing menu names or codes")
    for column in NUMERIC_COLUMNS:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any() or (~numeric.map(pd.notna)).any():
            raise ValueError(f"{filename}: invalid values in {column}")
        if not numeric.map(lambda v: bool(pd.notna(v) and abs(v) != float('inf'))).all():
            raise ValueError(f"{filename}: non-finite values in {column}")
        frame[column] = numeric

    net_error = (
        frame["Subtotal"] - frame["Menu Discount Total"]
        - frame["Bill Discount Total"] - frame["Net Sales Total"]
    ).abs()
    grand_error = (
        frame["Net Sales Total"] + frame["Service Charge Total"]
        + frame["Tax Total"] + frame["VAT Total"] - frame["Grand Total"]
    ).abs()
    if (net_error > tolerance).any() or (grand_error > tolerance).any():
        raise ValueError(f"{filename}: financial identities do not reconcile")

    # A source report row is an aggregate, not a transaction or a daily sale.
    frame.insert(0, "source_excel_row", range(HEADER_ROW + 2, HEADER_ROW + 2 + len(frame)))
    frame.insert(0, "source_file", filename)
    frame.insert(0, "period_end", period_end)
    frame.insert(0, "period_start", period_start)
    frame["negative_reported_unit_price"] = frame["Unit Price"].lt(0)
    frame["zero_net_sales"] = frame["Net Sales Total"].eq(0)

    audit = pd.DataFrame([{
        "source_file": filename,
        "period_start": period_start,
        "period_end": period_end,
        "summary_rows": len(frame),
        "net_identity_mismatches": int((net_error > tolerance).sum()),
        "grand_identity_mismatches": int((grand_error > tolerance).sum()),
        "negative_reported_unit_prices": int(frame["negative_reported_unit_price"].sum()),
        "zero_net_sales_rows": int(frame["zero_net_sales"].sum()),
        "repeated_code_rows": int(frame.duplicated("Menu Code", keep=False).sum()),
        "repeated_identity_rows": int(frame.duplicated(list(IDENTITY_COLUMNS), keep=False).sum()),
    }])
    return MonthlyReport(rows=frame, audit=audit)


def load_monthly_reports(paths: Iterable[str | Path | BytesIO], *, tolerance: float = 1.0) -> MonthlyReport:
    """Combine distinct periods, preserving every source summary row."""
    paths = list(paths)
    if not paths:
        raise ValueError("No monthly report workbooks supplied")
    reports = [read_monthly_report(path, tolerance=tolerance) for path in paths]
    audit = pd.concat([r.audit for r in reports], ignore_index=True)
    if audit["period_start"].duplicated().any():
        raise ValueError("More than one source workbook covers the same month")
    rows = pd.concat([r.rows for r in reports], ignore_index=True)
    return MonthlyReport(rows=rows, audit=audit.sort_values("period_start").reset_index(drop=True))


def monthly_overview(rows: pd.DataFrame) -> pd.DataFrame:
    """Report totals by calendar month; sums precomputed report values only."""
    grouped = rows.groupby(["period_start", "period_end"], dropna=False, as_index=False)
    result = grouped.agg(
        summary_rows=("Qty", "size"),
        units_sold=("Qty", "sum"),
        subtotal=("Subtotal", "sum"),
        menu_discount=("Menu Discount Total", "sum"),
        bill_discount=("Bill Discount Total", "sum"),
        reported_net_sales=("Net Sales Total", "sum"),
        tax=("Tax Total", "sum"),
        vat=("VAT Total", "sum"),
        service_charge=("Service Charge Total", "sum"),
        reported_grand_total=("Grand Total", "sum"),
    )
    return result.sort_values("period_start").reset_index(drop=True)


def item_performance(rows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate only exact item/category/channel identities, never code alone."""
    dims = ["period_start", *IDENTITY_COLUMNS]
    result = rows.groupby(dims, dropna=False, as_index=False).agg(
        source_rows=("Qty", "size"),
        units_sold=("Qty", "sum"),
        reported_net_sales=("Net Sales Total", "sum"),
        reported_grand_total=("Grand Total", "sum"),
    )
    return result.sort_values(["period_start", "reported_net_sales"], ascending=[True, False]).reset_index(drop=True)


def category_performance(rows: pd.DataFrame) -> pd.DataFrame:
    """Category/channel performance using the reported monetary amounts."""
    return rows.groupby(
        ["period_start", "Menu Category", "Menu Category Detail", "Sales Type"],
        dropna=False, as_index=False,
    ).agg(
        summary_rows=("Qty", "size"),
        units_sold=("Qty", "sum"),
        reported_net_sales=("Net Sales Total", "sum"),
    ).sort_values(["period_start", "reported_net_sales"], ascending=[True, False]).reset_index(drop=True)
