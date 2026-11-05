"""Conservative, cent-accurate POS discount and transaction reconciliation.

This module only estimates revenue for eligible sales rows. It never treats
status flags, negative amounts or negative quantities as proven refunds, and it
never subtracts candidate refunds to produce a misleading 'net revenue'.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import pandas as pd

from pos.classification import classify_pos_transactions
from pos.transactions import validate_discount_price_basis

_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")


def _money(value: object, label: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain finite monetary values.") from exc
    if not amount.is_finite():
        raise ValueError(f"{label} must contain finite monetary values.")
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def _number(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite and numeric.") from exc
    if not result.is_finite():
        raise ValueError(f"{label} must be finite and numeric.")
    return result


def _is_missing(value: object) -> bool:
    """Check a scalar value for missingness with safe Pandas typing."""
    return bool(pd.Series([value], dtype="object").isna().iat[0])


def _optional_money(value: object, label: str) -> Decimal:
    return _ZERO if _is_missing(value) else _money(value, label)


def _optional_number(value: object, label: str) -> Decimal:
    return Decimal(0) if _is_missing(value) else _number(value, label)


def _allocate_cents(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Allocate exact cents by largest remainder; tie-break by input order."""
    if not weights or amount < 0 or any(weight < 0 for weight in weights):
        raise ValueError("Invalid order-discount allocation inputs.")
    total = sum(weights, Decimal(0))
    if total == 0:
        if amount:
            raise ValueError("Cannot allocate order discounts to zero-value items.")
        return [_ZERO for _ in weights]
    if amount > total:
        raise ValueError("Order discount cannot exceed eligible order value.")
    cents = int(amount * 100)
    fractions = [Decimal(cents) * weight / total for weight in weights]
    bases = [int(frac) for frac in fractions]
    remainder = cents - sum(bases)
    winners = sorted(range(len(weights)), key=lambda i: (-(fractions[i] - bases[i]), i))
    for i in winners[:remainder]:
        bases[i] += 1
    return [Decimal(c) / 100 for c in bases]


def reconcile_pos_sales(
    df: pd.DataFrame,
    *,
    price_basis: str = "unknown",
    status_column: str | None = None,
    amount_column: str | None = None,
    line_discount_column: str | None = None,
    percent_column: str | None = None,
    per_unit_discount_column: str | None = None,
    order_id_column: str | None = None,
    order_discount_column: str | None = None,
    order_percent_column: str | None = None,
    stacking: str = "exclusive",
    verified_conventions: bool = False,
) -> pd.DataFrame:
    """Compute an auditable *eligible-sales* preview, never POS net revenue.

    Required columns: price, units_sold. The source price is a unit amount.
    Line discount is a *total for one line*, per-unit discount is multiplied by
    quantity, and percentage discount is expressed as 20 for 20 percent.

    `exclusive`: at most one nonzero line discount type per row.
    `sequential`: apply the percentage first, then subtract line + per-unit
    cash discounts; the order-level percent then cash discount apply last.

    An order-level amount can appear on a single line or be repeated at an
    identical value across all lines. Distinct positive amounts in an order
    are ambiguous and rejected. The amount is allocated *once per order*.

    No sales amount is claimed verified unless the caller explicitly confirms
    the export's price, status and discount conventions. Refund candidates and
    cancellations always require separate accounting review; no deductions
    for them are performed here.
    """
    validate_discount_price_basis(price_basis)
    if stacking not in {"exclusive", "sequential"}:
        raise ValueError("stacking must be 'exclusive' or 'sequential'.")
    if not df.index.is_unique:
        raise ValueError("Duplicate row indices are not supported for allocation.")
    if not df.columns.is_unique:
        raise ValueError("Duplicate source columns are not supported.")
    columns = {
        "price": "price", "units_sold": "units_sold",
        "status": status_column, "amount": amount_column,
        "line discount": line_discount_column, "percentage discount": percent_column,
        "per-unit discount": per_unit_discount_column,
        "order ID": order_id_column, "order discount": order_discount_column,
        "order percent": order_percent_column,
    }
    chosen = [v for v in columns.values() if v is not None]
    if len(chosen) != len(set(chosen)):
        raise ValueError("All POS field mappings must use distinct columns.")
    missing = set(chosen).difference(df.columns)
    if missing:
        raise ValueError("Missing mapped POS fields: " + ", ".join(sorted(missing)))
    if (order_discount_column or order_percent_column) and not order_id_column:
        raise ValueError("Order discounts require a mapped order ID.")
    if price_basis == "realized" and any((line_discount_column, percent_column, per_unit_discount_column, order_discount_column, order_percent_column)):
        # Users may map discounts to review, but these are never subtracted again.
        pass

    result = classify_pos_transactions(
        df, status_column=status_column, amount_column=amount_column,
    ).copy(deep=True)
    result["eligible_sale"] = result["transaction_class"].eq("sale") & result["units_sold"].map(lambda n: _number(n, "units_sold") > 0)
    result["accounting_status"] = "review_required"
    result.loc[result["eligible_sale"], "accounting_status"] = "unverified"
    result["gross_sales_amount"] = pd.Series(float("nan"), index=df.index)
    result["line_discount_applied"] = pd.Series(float("nan"), index=df.index)
    result["order_discount_allocated"] = pd.Series(float("nan"), index=df.index)
    result["eligible_sales_amount"] = pd.Series(float("nan"), index=df.index)
    if result.empty:
        return result

    # Validate ALL source amounts even when rows are excluded from sales.
    gross: dict[object, Decimal] = {}
    values: dict[object, Decimal] = {}
    line_discounts: dict[object, Decimal] = {}
    for key, row in result.iterrows():
        price = _money(row["price"], "price")
        quantity = _number(row["units_sold"], "units_sold")
        if price <= 0 or quantity != quantity.to_integral_value():
            raise ValueError("Price must be positive and quantities must be whole numbers.")
        if order_id_column and pd.isna(row[order_id_column]) and row["eligible_sale"]:
            raise ValueError("Eligible sales require nonmissing order IDs.")
        if not row["eligible_sale"]:
            continue
        line_gross = price * quantity
        gross[key] = line_gross
        result.at[key, "gross_sales_amount"] = float(line_gross)
        if price_basis == "unknown":
            continue
        if price_basis == "realized":
            values[key] = line_gross
            line_discounts[key] = _ZERO
            result.at[key, "line_discount_applied"] = 0.0
            continue
        percent = _optional_number(row[percent_column], "discount_percent") if percent_column else Decimal(0)
        cash = _optional_money(row[line_discount_column], "discount_amount") if line_discount_column else _ZERO
        per_unit = _optional_money(row[per_unit_discount_column], "per_unit_discount") if per_unit_discount_column else _ZERO
        if percent < 0 or percent > 100 or cash < 0 or per_unit < 0:
            raise ValueError("Discounts must be nonnegative and percentages between 0 and 100.")
        active = sum(x > 0 for x in (percent, cash, per_unit))
        if active > 1 and stacking == "exclusive":
            raise ValueError("Overlapping line discounts require explicit sequential stacking.")
        percent_amount = (line_gross * percent / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
        discount = percent_amount + cash + per_unit * quantity
        if discount > line_gross:
            raise ValueError("Line discount cannot exceed gross sales.")
        line_discounts[key] = discount
        values[key] = line_gross - discount
        result.at[key, "line_discount_applied"] = float(discount)

    if price_basis == "unknown":
        return result

    allocations = {key: _ZERO for key in values}
    if (order_discount_column or order_percent_column) and price_basis == "listed":
        # Retain row occurrence ordering; groupby on the order ID itself would
        # otherwise merge missing IDs and make accounting conventions unclear.
        if order_id_column is None:
            raise ValueError("Order discounts require a mapped order ID.")

        orders: dict[str, list[object]] = {}

        for key, row in result.iterrows():
            if row["eligible_sale"]:
                order_id = str(row[order_id_column])
                orders.setdefault(order_id, []).append(key)
                
        for keys in orders.values():
            raw_amounts = (
                [_optional_money(result.at[k, order_discount_column], "order_discount") for k in keys]
                if order_discount_column else [_ZERO for _ in keys]
            )
            raw_percentages = (
                [_optional_number(result.at[k, order_percent_column], "order_percent") for k in keys]
                if order_percent_column else [Decimal(0) for _ in keys]
            )
            if any(amount < 0 for amount in raw_amounts):
                raise ValueError("Order discounts cannot be negative.")
            
            if any(p < 0 or p > 100 for p in raw_percentages):
                raise ValueError("Order percentages must be between 0 and 100.")
            
            positive = {amount for amount in raw_amounts if amount > 0}
            positive_pct = {p for p in raw_percentages if p > 0}
            
            if len(positive) > 1 or len(positive_pct) > 1:
                raise ValueError("Conflicting order discount totals in the same order.")
            
            fixed = next(iter(positive), _ZERO)
            
            pct = next(iter(positive_pct), Decimal(0))
            
            if fixed > 0 and pct > 0 and stacking == "exclusive":
                raise ValueError("Overlapping order discounts require sequential stacking.")
            
            weights = [values[k] for k in keys]
            total = sum(weights, Decimal(0))
            percentage_amount = (total * pct / 100).quantize(_CENT, rounding=ROUND_HALF_UP)
            percent_shares = _allocate_cents(percentage_amount, weights)
            amounts_after_pct = [w - share for w, share in zip(weights, percent_shares, strict=True)]
            fixed_shares = _allocate_cents(fixed, amounts_after_pct)
            
            for key, pshare, fshare in zip(keys, percent_shares, fixed_shares, strict=True):
                allocations[key] = pshare + fshare

    for key, value in values.items():
        result.at[key, "order_discount_allocated"] = float(allocations[key])
        result.at[key, "eligible_sales_amount"] = float(value - allocations[key])
        if verified_conventions:
            result.at[key, "accounting_status"] = "verified_sale_conventions"
    return result


def summarize_reconciled_sales(result: pd.DataFrame) -> dict[str, object]:
    """Summarize only eligible rows; never claim refunds were reconciled."""
    eligible = result[result["eligible_sale"]]
    is_verified = not eligible.empty and bool(
        eligible["accounting_status"].eq("verified_sale_conventions").all()
    )
    values = eligible["eligible_sales_amount"]
    return {
        "eligible_sale_rows": len(eligible),
        "refund_candidates": int(result["transaction_class"].eq("refund_candidate").sum()),
        "cancelled_rows": int(result["transaction_class"].eq("cancelled").sum()),
        "requires_review": int(result["requires_accounting_review"].sum()),
        "eligible_sales_revenue": float(values.sum()) if values.notna().all() and not eligible.empty else None,
        "conventions_verified": is_verified,
        "net_revenue_verified": False,
    }
