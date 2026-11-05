# Part 5 — Universal menu data quality

This module performs **read-only** menu data-quality diagnostics on original uploaded rows.

- Normalizes Unicode (NFKC), whitespace and casing into comparison keys without rewriting product names.
- Shows spelling variants; a reviewed `alias,canonical` CSV can adjust the downloadable *suggested* name column, but **not** the Analytics pipeline.
- Reports distinct cent-rounded observed prices per item. A changed price may be legitimate and is **not** automatically an anomaly or an error.
- Flags identical complete source rows as duplicate **candidates**, never removes them.
- Optionally checks a *unique line ID*. An order ID is not a unique line ID.
- Reports missing and invalid mapped fields, plus nonpositive prices/quantities and unparsable dates. Negative quantity can mean a return.

No entity resolution, deduplication, discount correction, or item merging is performed automatically; these would change revenue and require provider-specific evidence.

## Install

Unzip this patch at the project root and run `python3 scripts/install_part5.py`. It modifies only `src/ui/pages/data_quality.py` using a checked anchor and is idempotent. Keep a clean commit or backup before installation.

## Test

```sh
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m streamlit run src/app.py
```

Open **2. Data Quality → Menu names, duplicate candidates and price consistency**.

## Demo data

`data/synthetic/part5_menu_quality_demo.csv` is synthetic and contains several intentionally repeated spellings/prices and a repeated line ID/row to demonstrate warnings. Upload `data/synthetic/part5_aliases_demo.csv` in the optional alias uploader to see suggestions; these are not automatically applied downstream.
