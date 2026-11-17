# Part 7.5 — CI and release checklist

This is a portfolio-quality validation gate, not a certification of financial reconciliation or a production-hosting configuration.

## What CI does

On every push and pull request, GitHub Actions checks out the repository on an Ubuntu runner, installs Python 3.12 and `requirements-dev.txt`, runs Ruff, compiles the application source, and runs the entire pytest suite with `PYTHONPATH=src`.

No secrets or external datasets are required by the workflow. Do not add real POS exports or API keys to the repository.

## One-time local installation

1. Extract the patch into the repository root.
2. Run `python3 scripts/install_part7_5.py`.
3. Run the commands below before staging changes.

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
git status --short
```

## Privacy and staged-file review

Check the local dataset is ignored:

```bash
git check-ignore -v data/Indo_CoffeeShop/
git check-ignore -v data/Online\ Retail.xlsx
```

If you are going to commit, stage only intentional changes, not `git add .`:

```bash
git add .github/workflows/ci.yml requirements-dev.txt .gitignore \
  docs/PART7_5_PRODUCTION_CHECKLIST.md scripts/install_part7_5.py \
  PART7_2_README.md PART7_4_README.md \
  src/pos/toast_style_validation.py src/ui/part7_polish.py \
  src/ui/styles.py src/ui/sections/model_evaluation.py \
  tests/pos/test_toast_style_validation.py tests/ui/test_part7_polish.py \
  data/examples/
git diff --cached --name-only
git diff --cached --check
```

Review the staged list carefully. Do not commit until local checks pass and every staged file is expected. Check `.env`, POS exports, financial customer information, installer `.bak` files, and workbook contents before publishing.

## Push and verify

After reviewing staged changes, commit in GitHub Desktop or via git. Push main and open GitHub -> Actions -> CI to verify that the workflow passes on GitHub. Local tests cannot guarantee the hosted CI passes until that run completes.

## Deployment considerations

- This workflow is CI, not deployment. Streamlit hosting and secrets require separate setup.
- Pin and review dependencies deliberately; the current runtime dependencies are version-pinned except openpyxl.
- Keep `.env` and `.streamlit/secrets.toml` out of Git, and configure service secrets only in your deployment platform.
- Retain conservative labels for sales-only metrics, refunds and discount assumptions; nothing in CI independently verifies net revenue.
- Verify both synthetic cafe and Toast-style demo workflows after any deployment.
