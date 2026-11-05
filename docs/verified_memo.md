# Deterministic memo facts (Part 6)

The Reports tab now presents two separate layers:

1. **Data-backed findings** are produced exclusively from the computed item summary and used in Markdown, TXT, and PDF exports. Review-flag counts, associated item names, historical elasticity confidence labels, distinct price points, observations, and available revenue figures are calculated directly from the same source data used by the dashboard.
2. **AI commentary — unverified** remains visible in the application for human review, but is intentionally **not** included in the default downloads. A limited audit cannot reliably certify arbitrary AI-written numeric claims.

This is a change to report presentation, not to source rows, revenue calculations, quarantine decisions, or model estimation. The existing refund and settlement limitations in `build_memo_export` continue to appear in downloaded reports. A High label is heuristic, not a calibrated confidence interval.

Install: `python3 scripts/install_verified_memo.py` from the repo root after unzipping the patch.
