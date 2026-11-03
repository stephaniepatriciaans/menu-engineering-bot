# Architecture

`src/app.py` is the Streamlit entry point. `src/ui/pages/` separates Data Setup, Data Quality, Analytics, and Reports into render functions. `src/ui/sections/` contains reusable visual components.

- `src/data_pipeline/`: POS CSV ingestion, canonical mapping, synthetic generation
- `src/core/`: validation and common analytical helpers
- `src/pos/`: refund candidate classification and discount normalization
- `src/analytics/`: menu engineering, price simulation, model evaluation
- `src/ai/`: AI memo preparation, safety and errors
- `src/reporting/`: memo and PDF output

All four Streamlit tabs execute on each rerun. Tabs organize the visible interface; they do not defer computation or isolate the setup state.

Tests are arranged under matching responsibility folders (`tests/analytics`, `tests/ai`, etc.) without package markers that could shadow `src/` imports. Run with `PYTHONPATH=src python3 -m pytest -q`.

**Financial scope:** Status-based refunds and cancellations are preview-only; quantity-based refund candidates are excluded from sales-only analysis. Discounts are not yet integrated into main dashboard revenue and profit. Do not label gross revenue as confirmed net revenue.

The included `scripts/finalize_layout.py` safely removes original root-level test files only when their new copies match, and moves local screenshots into `assets/screenshots/` while updating README links. The script does not move/delete excluded CSV datasets.
