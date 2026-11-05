# POS export accounting validation

This optional audit is **separate** from the existing Financial Review and
Analytics metrics. It does not update dashboard revenue or automatically
verify refund and discount conventions for other POS systems.

## Validation contract

Use a transaction-level export and an **independently produced** summary for
exactly the same merchant, time period, currency, product scope and pre-tax
sales basis. The signed amount column must represent realized, discounted
item-sales amounts **excluding sales tax, tips, tender movements, fees and
shipping**; tax and tip columns may exist in the export but are not used to
compute this metric. If the POS summary includes those amounts, do not compare
it directly with this calculation.

Only select `separate_signed_events` if you have confirmed that each refund is
an additional row with a negative signed amount, not an original sale relabeled
`refunded`. Unique event IDs must identify individual events, not just orders.
A positive source row marked `refunded` is ambiguous and blocks verification.
Cancellations are excluded from sales unless the provider's export convention
requires a different treatment, in which case the audit is not applicable.

An audit returns **matched** only when all requirements are satisfied, the
signed sale amounts equal the recalculated post-discount eligible sales, and
the independently supplied pre-tax net-sales total agrees to the cent.
**Matched is evidence for this exact export only, not a guarantee**.

## Example

Assuming an anonymized export at `data/private/transactions.csv` with source
fields `event_id,price,units_sold,status,signed_amount`, and a separately
verified net item-sales summary of **15.00**:

```bash
PYTHONPATH=src python3 scripts/validate_pos_export.py \
  --csv data/private/transactions.csv \
  --expected-net 15.00 \
  --event-id event_id --status status --amount signed_amount \
  --price-basis listed \
  --refund-convention separate_signed_events \
  --amount-basis pre_tax_sales \
  --confirm-conventions
```

For per-unit or order-level discounts, use `--per-unit-discount`,
`--order-id`, `--order-discount`, `--order-percent`, and `--stacking sequential`
only when the export semantics have been confirmed. Negative refund amounts
must reflect their actual refunded item-sales value (including any applicable
discount reversal), not their undiscounted list price.

Exit code `0` means matched, `2` means mismatch/review required, `1` means
invalid input. Do **not** commit actual POS exports or merchant identifiers.

## Important limitations

- Payment processor settlement, cash deposit, POS gross sales, and pre-tax
  item-sales are different quantities; do not compare them indiscriminately.
- One matched sample does not establish rules for every provider or export.
- Chargebacks, exchanges, gift cards, mixed tax jurisdictions, store credit,
  multi-currency transactions, historical price changes and settlement delays
  need specific provider-level verification before financial integration.
- The audit is intentionally read-only and does not connect its output to
  pricing recommendations, AI memos or dashboard KPIs.
