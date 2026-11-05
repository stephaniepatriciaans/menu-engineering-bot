"""Installer integration preserves accounting audit source data."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/install_pos_quarantine.py"


def test_installer_does_not_replace_raw_financial_preview_inputs():
    spec = importlib.util.spec_from_file_location("quarantine_install_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = (Path(__file__).resolve().parents[2] / "src/ui/pages/data_quality.py").read_text()
    changed = module.install(original)
    assert "analysis_raw_df = pos_review.analysis_rows" in changed
    assert "adapt_to_canonical(\n            analysis_raw_df," in changed
    assert "render_pos_reconciliation(\n            raw_df," in changed
    assert "raw_df.loc[original_negative], mapping" in changed
    assert module.install(changed) == changed
