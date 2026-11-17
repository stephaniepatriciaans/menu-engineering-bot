# Part 7.4 — UI polish (safe incremental patch)

This patch provides a responsive, theme-aware visual layer and improves the historical-demand chart for items with just one held-out date. It is **presentation only**. It does not touch accounting, forecasting, mapping, or data files.

## Install

Extract the ZIP into the **root** of your existing `menu-engineering-bot` repository. Then:

```bash
python3 scripts/install_part7_4.py
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q tests/ui/test_part7_polish.py
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
```

The installer checks that `apply_dashboard_styles` exists and inserts one additive call into it. It also checks for an exact historical line-chart block before replacing it. If the chart differs from the published repository, **the installer skips the change** rather than guessing. It prints the result of each action.

Backups of modified files are created as `src/ui/styles.py.part7_4.bak` and `src/ui/sections/model_evaluation.py.part7_4.bak`. These backups should not be committed. Review the diff before deleting the backups. The installer is safe to run again; it does not double-apply changes.

## Verify in Streamlit

Run `PYTHONPATH=src python3 -m streamlit run src/app.py`. Check desktop and narrow-width layouts, Data Setup, Data Quality, and Model Evaluation. For the one-date chart, a numeric table should appear instead of a blank-looking line chart. With two or more held-out dates, the usual line chart should still appear.

## Scope and limitation

This is a safe, complete **initial** Part 7.4 implementation based on the published structure plus the screenshots. It does not restructure the full mapping form, because your local code is newer than the published repository and should be inspected before changing functional widgets. It does not claim to finish all UI-polish acceptance criteria without local verification.
