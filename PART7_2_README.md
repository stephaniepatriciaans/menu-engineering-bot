# Part 7.2 — Universal POS / Toast-style validation pack

This additive patch introduces `src/pos/toast_style_validation.py`, a synthetic line-item CSV in `data/examples/`, and an extensive test suite.

**Important:** The CSV is deliberately *Toast-style*, not an official Toast export. Column names and financial conventions vary by product, configuration, and report. No provider-specific refund behavior is assumed.

## Install

Copy the three files into matching paths in your existing repo (or unzip this archive into the repo root). Existing application files are not overwritten.

## Run

```bash
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q tests/pos/test_toast_style_validation.py
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
```

Expected: 18 new tests, so **570 tests** if your original baseline remains 552. Your installed versions may surface compatibility issues; report the output before committing.

## Inspect sample manually in Streamlit

Upload `data/examples/toast_style_sample.csv`. It contains 2 eligible sales, 1 refund candidate, and 1 cancelled row. Map Date → Business Date, Item → Menu Item, Price → Unit Price, Units → Qty, Status → Order Status, Signed Amount → Signed Pre-tax Amount, Discount Amount → Line Discount. Set the unit price basis to *listed* only when known for a source file.

The fixture's example cent-accurate amounts: eligible sales $24.00, signed refund event -$10.00, pre-tax net $14.00 **only under explicitly confirmed sample conventions and an independent $14.00 summary**. The application should not claim this independently verified from the fixture alone.

For actual restaurant exports, confirm whether amounts include taxes, tips, service charges, tenders, and whether 'refunded' indicates a separate negative event or merely annotates the original positive sale. Never silently net ambiguous records.

## Integration boundary

This pack exercises existing `pos.export_validation.audit_pos_export` and `pos.reconciliation.reconcile_pos_sales`, but does **not** modify the Streamlit UI or mapping presets. UI auto-detection of arbitrary field labels is not guaranteed, and source fields can be selected manually. Adding a dedicated Toast preset or a sidebar validation report should follow after local tests confirm compatibility.
