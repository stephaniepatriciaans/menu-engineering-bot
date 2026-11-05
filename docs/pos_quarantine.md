# POS source review & sales-only quarantine (Part 6)

* Works with CSV and Excel uploads through the existing column mapper.
* Original source DataFrame remains unmodified; no financial values are adjusted.
* Negative-quantity or negative-signed-amount refund candidates and cancellation
  statuses are excluded **only from sales-only analytics** and included in the
  download of records needing review. Their net-sales accounting is NOT assumed.
* Rows with missing item names, invalid dates, nonpositive/invalid selling
  prices, invalid/zero quantities, or invalid nonblank costs cannot be used
  in the sales analytics pipeline. They are marked and downloadable rather than
  deleted. This is a **readiness screen**, not evidence of completed revenue.
* The source and review tables retain the original input values. The review
  CSV adds `__pos_source_row` and `__pos_review_reasons` for reconciliation.
* InvoiceNo values beginning with `C` are shown as evidence. **Only for UCI
  Online Retail**, an opt-in checkbox excludes C-prefixed invoices from
  sales-only analytics. Do not apply this convention to arbitrary POS exports.
* Financial previews still receive all original source rows. The financial
  integration is disabled if rows are quarantined for invalid fields; a
  settlement match cannot certify missing item allocations or malformed costs.
* Price basis, discounts, refund allocations, taxes, and tips are not inferred.
* Review overlap is expected: a row can have both an invalid item name and a
  refund signal. Counters should not be added as if disjoint.

To install after backing up your working tree:

```bash
unzip -o menu-engineering-pos-quarantine-patch.zip -d .
python3 scripts/install_pos_quarantine.py
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
```
