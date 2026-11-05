# Part 7.1 and 7.3 — Performance and model reliability

This patch is intentionally conservative: it does not alter canonical transaction
rows, gross revenue, cost accounting, refunds, forecasts, model eligibility, or
existing test outcomes.

## 7.1

- Bounded 30-minute Streamlit upload cache keyed on **file contents,
  filename, and encoding**, rather than an unreliable filename-only cache.
- A timing panel displays wall-clock durations per Streamlit workflow stage.
- Uploaded file parsing is cached, but Data Quality and the full analytics
  pipeline **are still computed on reruns**. Do not interpret this as full
  performance optimization or a benchmark result.
- The cache holds at most one upload. Large cached frames consume memory;
  reduce max_entries or disable caching if memory use grows too high.

## 7.3

- A paired forecast reliability review shows mean/median MAE on the **same
  evaluated items**, baseline-vs-elasticity win counts, extrapolation counts,
  and extreme relative errors.
- Warnings are descriptive. No prediction is clipped or implicitly promoted
  to an accurate/causal pricing model.
- Model comparisons never include baseline-only or insufficient-evidence items.

## Validation

Run `python3 -m ruff check src tests scripts`, `PYTHONPATH=src python3 -m pytest -q`,
`python3 -m compileall -q src`, and `git diff --check`.

After installing, test large Excel reruns, observe the diagnostics, and compare
all financial and model outputs before/after. The new paired summary should
match the already displayed two-model item population.
