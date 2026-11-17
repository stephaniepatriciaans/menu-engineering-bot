# Menu Engineering Bot — Part 7.5 CI Patch

Adds:
- `.github/workflows/ci.yml` — push/PR checks on Python 3.12 (Ruff, compileall, pytest).
- `scripts/install_part7_5.py` — idempotently adds Ruff to development dependencies and ignores local dataset/installer backups.
- `docs/PART7_5_PRODUCTION_CHECKLIST.md` — validation, selective staging, and GitHub Actions verification.

Installation from project root:

```bash
unzip -o menu-engineering-part7_5-ci.zip -d .
python3 scripts/install_part7_5.py
python3 -m pip install -r requirements-dev.txt
python3 -m ruff check src tests scripts
PYTHONPATH=src python3 -m pytest -q
python3 -m compileall -q src
git diff --check
```

Review untracked files before staging. Do not commit private datasets. The workflow does not deploy the application or validate net-sales accounting.
