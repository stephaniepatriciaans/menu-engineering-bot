# Part 6: reliability and charge-review patch

This patch adds review-only signals for unusually extreme historical item price ranges and likely operational charge descriptions, and updates report copy that could imply full accounting verification.

**Does not:** delete transactions, change gross sales, alter fitted elasticity coefficients, or verify charge classifications. A name is only a review hint. The >500% historic price-variation confidence downgrade is a cautious heuristic, not a statistically calibrated threshold. Non-merchandise items still contribute to existing sales totals unless a separate reviewed classification flow is added.

Install from repository root:

```bash
unzip -o menu-engineering-reliability-review-patch.zip -d .
python3 scripts/install_reliability_review.py
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
```

The patch adds one extra table column for reliability warnings and a review list to Reports. Regenerate an existing memo after installation to pick up revised AI prompt guidance. Existing manually generated memo text is not rewritten or silently replaced.
