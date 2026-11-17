# Part 8 — Monthly aggregated menu-sales reports

This patch is **additive**. It does not replace your transaction-level loader, model evaluation, or existing dashboard.

## Included

- `src/data_pipeline/monthly_report.py`: fail-closed workbook parser with period and financial identity checks; original 19 report columns, source filename, and Excel row numbers preserved.
- `src/ui/monthly_report_dashboard.py`: standalone monthly-analysis Streamlit screen.
- `scripts/monthly_report_app.py`: entry point for the separate monthly report screen.
- `scripts/validate_monthly_reports.py`: command-line audit and CSV summaries stored in the gitignored `data/local/` directory.
- `tests/data_pipeline/test_monthly_report.py`: synthetic tests; **no private workbooks are bundled**.

## Install

Unzip this patch at the repository root. Verify that the existing `data/Indo_CoffeeShop/` and `data/local/` folders are ignored by Git.

## Local validation

```bash
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q tests/data_pipeline/test_monthly_report.py
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
python3 scripts/validate_monthly_reports.py
```

The validation script prints row-count and anomaly summaries. Monthly financial totals are written locally to `data/local/monthly_validation/` and should not be published.

## Open the separate monthly dashboard

```bash
PYTHONPATH=src python3 -m streamlit run scripts/monthly_report_app.py
```

Upload the three monthly `.xlsx` files from `data/Indo_CoffeeShop/`.

## Safeguards and limitations

1. Monthly summary rows are **not** individual transaction rows. No fake daily dates, daily-demand forecasts, hourly patterns, elasticity, or cost-based menu quadrant classifications.
2. Reported `Unit Price` is retained, but **never multiplied by Qty** to reconstruct revenue.
3. Item identity includes menu code, name, category, subcategory, and sales channel. Repeated source rows are never dropped.
4. Source-reported net sales and grand totals are kept as separate measures; arithmetic checks only validate internal consistency, not accuracy against the POS ledger.
5. The importer rejects unexpected headers, duplicate monthly periods, and financial identity mismatches instead of silently correcting them.
6. Synthetic tests cannot prove compatibility with private real reports. Validate `2,751` summary rows, the three period counts (`918`, `887`, `946`), and anomalies locally before treating results as verified.
7. Data remains local; do not commit proprietary sales information or exported summaries.
