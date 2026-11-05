# Memo export consistency / PDF tables

Install from repository root:

```bash
unzip -o menu-engineering-memo-polish-patch.zip -d .
python3 scripts/install_memo_polish.py
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
```

All source financial calculations remain unchanged. The consistency helper
corrects only two identifiable forms of memo count errors, using item summary
flags and confidence counts; other AI statements still need human review.
Operational-charge classifications are candidates, not verified classifications.
The revised report disclaimer distinguishes narrow memo-claim checks from POS
reconciliation. PDF Markdown pipe tables are rendered with ReportLab Table.

Generate a **new** memo, download all three formats, and compare the displayed
count and audit limitation with the exports. Export verification does not imply
financial reconciliation. Tests require existing project dependencies; the new
PDF rendering test validates the ReportLab table structure without extra dependencies.
