# Part 9 — Monthly Business Insights

This patch adds a **Business Insights** tab to the existing Menu Engineering Bot (`src/app.py`). It does not add another Streamlit app and does not modify `src/data_pipeline/monthly_report.py`.

## Included files

- `src/analytics/monthly_business_insights.py` — deterministic, bilingual (English/Bahasa Indonesia) commentary.
- `src/ui/monthly_report_dashboard.py` — complete monthly dashboard replacement, retaining Overview, Most Ordered, Categories & Channels, Data Quality and CSV downloads; adds the Business Insights tab and TXT download.
- `tests/analytics/test_monthly_business_insights.py` — eight synthetic tests; no private workbooks bundled.

## Installation

From your `menu-engineering-bot` project root, copy or unzip the patch **into that root**, preserving `src/` and `tests/` paths. **Back up your current dashboard file first if you have made additional edits not shared in chat.**

```bash
cp src/ui/monthly_report_dashboard.py /tmp/monthly_report_dashboard_before_part9.py
unzip -o part9_business_insights.zip -d .
python3 -m ruff check src/analytics/monthly_business_insights.py src/ui/monthly_report_dashboard.py tests/analytics/test_monthly_business_insights.py --fix
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q tests/analytics/test_monthly_business_insights.py
PYTHONPATH=src python3 -m pytest -q
python3 scripts/validate_monthly_reports.py
git diff --check
PYTHONPATH=src python3 -m streamlit run src/app.py
```

In **Monthly Sales Reports**, select **Business Insights** and the desired language. This version reports revenue/volume observations and explicit next checks, never inferred profit, customer orders or reasons for sales changes.

The backup in `/tmp` is for local rollback and is outside Git. If you need long-term backup, store a copy elsewhere outside the project.
