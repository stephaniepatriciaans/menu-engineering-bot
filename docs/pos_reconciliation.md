# POS sales reconciliation (conservative workflow)

This feature is intentionally separate from the existing sales-only dashboard,
pricing simulations, elasticity model, and AI reports. It does not claim to
reconcile cash collected, tax, tips, fees, or processed refunds.

## Available inputs

Map `price` (unit), `units_sold`, and optionally status, signed transaction
amount, line monetary discount, line percentage discount, per-unit monetary
discount, order ID, order monetary coupon and order percentage coupon.

The **listed** price basis applies discounts; **realized** price basis never
subtracts them again. An **unknown** basis yields no eligible-sales revenue.

## Discount conventions

* Monetary line discount is a total for one row.
* Per-unit monetary discount is multiplied by the row's quantity.
* Line percentage is a value 0–100, applied to gross line price.
* Order percentage applies to the sum of eligible lines after line discounts.
* Order monetary coupon applies last. It can be specified on one line or
  repeated at an identical total across the order; it is allocated **once**.
* Allocation uses largest remainder in cents, with deterministic row-order
  tie-breaking, ensuring that allocations sum exactly to the coupon total.
* `exclusive` (default) rejects multiple nonzero line discount types on a row
  or overlapping order percent + monetary coupons.
* `sequential` explicitly combines percentage, then monetary line and
  per-unit discounts, then percentage order and monetary order discounts.
  Discount totals exceeding the sales amount are rejected.

## Refund safeguards

Negative quantity, negative signed amount, and refund status create **refund
candidates** only. Cancelled status creates a **cancellation candidate**.
Contradictions are flagged; the original rows are never edited. Refunded
statuses can describe original sales, so this feature *never subtracts*
refund candidates to produce a purported net revenue.

Eligible-sales revenue is computed for **sale-classified** positive-quantity
rows only. It excludes review rows and is distinct from net revenue after
refunds. The operator can attest that the export's price/discount conventions
are confirmed, but that does **not** certify the underlying ledger.

## Dashboard integration

Data Quality includes **Advanced POS discount & sales reconciliation** under
an expander. Analytics shows the eligible-sales preview separately from
existing historical sales-only KPIs and predictive analytics. No existing
model, profit, pricing recommendation or report is automatically rewritten.
This avoids silently mixing unreconciled refunds with adjusted sale prices.

## Verification

Run `python3 -m ruff check src tests scripts` and
`PYTHONPATH=src python3 -m pytest -q` on your Mac before committing.
