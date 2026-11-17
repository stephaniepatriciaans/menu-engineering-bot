# Part 9 - Business Insights with PDF export

This is a complete Part 9 drop-in update for the existing Menu Engineering Bot. It adds a **Download business insights (.pdf)** button next to the TXT download in **Monthly Sales Reports > Business Insights**, with English and Bahasa Indonesia support.

## Files

- `src/analytics/monthly_business_insights.py` - calculated bilingual insights
- `src/reporting/monthly_business_insights_pdf.py` - in-memory PDF report (ReportLab)
- `src/ui/monthly_report_dashboard.py` - existing monthly tabs plus insights and PDF button
- `tests/analytics/test_monthly_business_insights.py` - 8 calculation tests
- `tests/reporting/test_monthly_business_insights_pdf.py` - 5 PDF regression tests (incl. two language cases)

The original monthly importer, app entry point, transaction features, and private reports are **not** changed.

## Installation

Download this ZIP into the root of `menu-engineering-bot` and run:

```bash
cp src/ui/monthly_report_dashboard.py /tmp/monthly_report_dashboard_before_part9_pdf.py
unzip -o part9_business_insights_with_pdf.zip -d .
python3 -m pip install reportlab
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q tests/analytics/test_monthly_business_insights.py tests/reporting/test_monthly_business_insights_pdf.py
PYTHONPATH=src python3 -m pytest -q
python3 scripts/validate_monthly_reports.py
git diff --check
PYTHONPATH=src python3 -m streamlit run src/app.py
```

Add `reportlab` to `requirements.txt` if not already declared. **Do not commit or upload the private XLSX reports or generated validation CSVs.**

The PDF includes a summary, monthly comparison table, category-filtered revenue contributors, grounded observations and next checks, and interpretation limitations. The report is made in memory and downloaded through Streamlit, not saved on the server. It does not infer profit, unique orders, individual transaction dates, or the causes of sales changes.
