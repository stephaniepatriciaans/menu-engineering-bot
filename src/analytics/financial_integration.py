"""Audited POS financial analytics that never infer refund item attribution.

An independent, cent-matched POS audit is mandatory. Summaries can be filtered
by the dashboard's existing date/category selections without changing forecasts
or treating discounted effective prices as listed menu prices.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd

from pos.export_validation import POSAudit

_CENT = Decimal("0.01")


def _cents(value: object, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a finite amount") from exc
    if not number.is_finite() or number != number.quantize(_CENT):
        raise ValueError(f"{label} must be finite and specified to exact cents")
    return number


@dataclass(frozen=True)
class AuditedFinancials:
    """Filtered eligible sales plus a separate full-export net-sales audit."""

    eligible_sales: Decimal
    eligible_units: int
    eligible_rows: int
    contribution_profit: Decimal | None
    by_item: pd.DataFrame
    by_category: pd.DataFrame
    by_day: pd.DataFrame
    by_hour: pd.DataFrame
    full_export_net_sales: Decimal
    has_refund_events: bool


def build_audited_financials(
    filtered_sales: pd.DataFrame,
    reconciled_rows: pd.DataFrame,
    audit: POSAudit,
) -> AuditedFinancials:
    """Aggregate only rows supported by an independent matched POS audit.

    ``filtered_sales`` is the already validated, cost-enriched and filtered
    canonical dataset. Index labels must still identify original POS rows.
    Refunds remain part of ``audit.proposed_net_sales`` at export level; they
    are never assigned to particular products or reporting dates.
    """
    if audit.outcome != "matched" or audit.findings or audit.proposed_net_sales is None:
        raise ValueError("An independently matched POS export audit is required.")
    if audit.expected_net_sales != audit.proposed_net_sales:
        raise ValueError("POS settlement does not match independently audited net sales.")
    if not filtered_sales.index.is_unique or not reconciled_rows.index.is_unique:
        raise ValueError("Financial integration requires unique POS row indices.")
    if not filtered_sales.index.isin(reconciled_rows.index).all():
        raise ValueError("Dashboard rows must come from the audited POS export.")
    eligible_all = reconciled_rows[reconciled_rows["eligible_sale"]]
    if not eligible_all["accounting_status"].eq("verified_sale_conventions").all():
        raise ValueError("Unverified sale conventions in audited export.")
    eligible_total = sum(
        (_cents(value, "Eligible sales") for value in eligible_all["eligible_sales_amount"]),
        Decimal("0.00"),
    )
    if eligible_total != audit.eligible_sales or len(eligible_all) != audit.eligible_rows:
        raise ValueError("Reconciled sale rows disagree with the matched POS audit.")
    if int(reconciled_rows["transaction_class"].eq("refund_candidate").sum()) != audit.refund_candidates:
        raise ValueError("Refund candidates disagree with the matched POS audit.")
    if int(reconciled_rows["transaction_class"].eq("cancelled").sum()) != audit.cancelled_rows:
        raise ValueError("Cancelled rows disagree with the matched POS audit.")

    needed = {"item", "date", "units_sold", "unit_cost"}
    if needed.difference(filtered_sales.columns):
        raise ValueError("The canonical sales data is missing required fields.")
    needed_audit = {"eligible_sale", "eligible_sales_amount", "accounting_status"}
    if needed_audit.difference(reconciled_rows.columns):
        raise ValueError("The reconciled POS data is missing audit fields.")

    selected = reconciled_rows.loc[filtered_sales.index]
    selected = selected.loc[selected["eligible_sale"].astype(bool)]
    canonical = filtered_sales.loc[selected.index].copy()
    if not selected["accounting_status"].eq("verified_sale_conventions").all():
        raise ValueError("Unverified sale conventions cannot enter financial analytics.")
    amounts: list[Decimal] = []
    units: list[int] = []
    costs: list[Decimal | None] = []
    for idx, row in canonical.iterrows():
        amount = _cents(selected.at[idx, "eligible_sales_amount"], "Eligible sales")
        quantity = Decimal(str(row["units_sold"]))
        if not quantity.is_finite() or quantity <= 0 or quantity != quantity.to_integral_value():
            raise ValueError("Eligible quantities must be positive whole numbers.")
        unit_count = int(quantity)
        if amount < 0:
            raise ValueError("Eligible sales cannot be negative.")
        amounts.append(amount)
        units.append(unit_count)
        cost_input = row["unit_cost"]
        if pd.isna(cost_input):
            costs.append(None)
        else:
            try:
                per_unit = Decimal(str(cost_input))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Unit cost must be finite and numeric.") from exc
            if not per_unit.is_finite() or per_unit < 0:
                raise ValueError("Unit cost must be nonnegative and finite.")
            costs.append((per_unit * unit_count).quantize(_CENT, rounding=ROUND_HALF_UP))

    hours = pd.Series(pd.NA, index=canonical.index, dtype="Int64")
    if "transaction_time" in canonical.columns:
        parsed_time = pd.to_datetime(
            canonical["transaction_time"].astype("string"),
            format="%H:%M:%S", errors="coerce",
        )
        fallback_time = pd.to_datetime(
            canonical["transaction_time"].astype("string"),
            format="%H:%M", errors="coerce",
        )
        hours = parsed_time.fillna(fallback_time).dt.hour.astype("Int64")

    records = pd.DataFrame({
        "item": canonical["item"].astype(str).to_numpy(),
        "category": canonical["category"].astype(str).to_numpy()
        if "category" in canonical.columns else ["Uncategorized"] * len(canonical),
        "date": pd.to_datetime(canonical["date"], errors="raise").dt.normalize().to_numpy(),
        "units": units,
        "revenue": amounts,
        "cost": costs,
        "hour": hours.to_numpy(),
    })
    records["profit"] = [
        revenue - cost if cost is not None else None
        for revenue, cost in zip(amounts, costs, strict=True)
    ]

    def aggregate(group_col: str) -> pd.DataFrame:
        entries: list[dict[str, object]] = []
        for key, group in records.groupby(group_col, sort=True, dropna=False):
            group_profit = (
                sum(group["profit"], Decimal("0.00"))
                if group["profit"].notna().all() else None
            )
            entries.append({
                group_col: key,
                "units": int(group["units"].sum()),
                "revenue": sum(group["revenue"], Decimal("0.00")),
                "contribution_profit": group_profit,
                "sale_rows": len(group),
            })
        return pd.DataFrame(
            entries,
            columns=[group_col, "units", "revenue", "contribution_profit", "sale_rows"],
        )

    profit = (
        sum(records["profit"], Decimal("0.00"))
        if records["profit"].notna().all() else None
    )
    return AuditedFinancials(
        eligible_sales=sum(amounts, Decimal("0.00")),
        eligible_units=sum(units),
        eligible_rows=len(records),
        contribution_profit=profit,
        by_item=aggregate("item"),
        by_category=aggregate("category"),
        by_day=aggregate("date"),
        by_hour=aggregate("hour").dropna(subset=["hour"]),
        full_export_net_sales=audit.proposed_net_sales,
        has_refund_events=audit.signed_refund_events is not None
        and audit.signed_refund_events < 0,
    )


def financial_report_text(financials: AuditedFinancials, *, business_name: str) -> str:
    """Deterministic appendix; never invent refund-level product performance."""
    profit = (
        f"{financials.contribution_profit:.2f}"
        if financials.contribution_profit is not None else "not available (missing costs)"
    )
    lines = [
        f"Audited financial appendix — {business_name}",
        "Scope: independently matched pre-tax item-sales export",
        f"Full-export audited net sales: {financials.full_export_net_sales:.2f}",
        f"Filtered eligible sales: {financials.eligible_sales:.2f}",
        f"Filtered contribution profit (eligible sales only): {profit}",
        f"Filtered eligible units: {financials.eligible_units}",
        f"Filtered eligible rows: {financials.eligible_rows}",
        "Net sales are for the full export; filtered item totals EXCLUDE refunds.",
        "Contribution profit is an estimate using supplied or assumed unit costs;",
        "unit costs were not verified against the POS settlement.",
        "Refund events have no inferred item/date/cost allocation.",
        "No historical price elasticity or menu-price recommendation is certified by this audit.",
        "", "Eligible-sales performance by item:",
    ]
    for row in financials.by_item.itertuples(index=False):
        lines.append(f"{row.item}: sales {row.revenue:.2f}, units {row.units}")
    return "\n".join(lines) + "\n"


def audited_menu_quadrants(financials: AuditedFinancials) -> pd.DataFrame:
    """Eligible-sales-only quadrants, without claiming refund-attributed margins.

    Uses aggregated per-item contribution margin and normalized quantity.
    These are NOT historical price-elasticity estimates or menu-list prices.
    """
    if financials.by_item.empty:
        return pd.DataFrame(columns=[
            "item", "units", "revenue", "margin_pct",
            "avg_daily_units", "quadrant",
        ])
    if financials.by_item["contribution_profit"].isna().any():
        return pd.DataFrame(columns=[
            "item", "units", "revenue", "margin_pct",
            "avg_daily_units", "quadrant",
        ])
    days = max(1, len(financials.by_day))
    data = financials.by_item.copy()
    data["margin_pct"] = [
        float(profit / revenue * 100) if revenue > 0 else float("nan")
        for profit, revenue in zip(
            data["contribution_profit"], data["revenue"], strict=True
        )
    ]
    if data["margin_pct"].isna().any():
        return pd.DataFrame(columns=[
            "item", "units", "revenue", "margin_pct",
            "avg_daily_units", "quadrant",
        ])
    data["avg_daily_units"] = data["units"] / days
    median_margin = data["margin_pct"].median()
    median_popularity = data["avg_daily_units"].median()
    data["quadrant"] = [
        "Star" if margin >= median_margin and popularity >= median_popularity
        else "Plowhorse" if popularity >= median_popularity
        else "Puzzle" if margin >= median_margin else "Dog"
        for margin, popularity in zip(
            data["margin_pct"], data["avg_daily_units"], strict=True
        )
    ]
    return data
