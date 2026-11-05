"""Installer should modify the existing Data Quality page once, without replacing it."""

from __future__ import annotations

import runpy
from pathlib import Path


def test_idempotent_installer(tmp_path, monkeypatch):
    target = tmp_path / "src/ui/pages/data_quality.py"
    target.parent.mkdir(parents=True)
    original = (
        "from ui.pages.data_setup import SetupData\n\n"
        "def render_data_quality(setup: SetupData):\n"
        "    # ================================================================\n"
        "    # POS transaction accounting preview\n"
        "    return 1\n"
    )
    target.write_text(original)
    installer = Path(__file__).resolve().parents[2] / "scripts/install_part5.py"
    namespace = runpy.run_path(str(installer), run_name="part5_installer_test")
    monkeypatch.setitem(namespace["main"].__globals__, "ROOT", tmp_path)
    monkeypatch.setitem(namespace["main"].__globals__, "TARGET", target)
    namespace["main"]()
    first = target.read_text()
    assert "render_menu_quality(raw_df, mapping)" in first
    namespace["main"]()
    assert first == target.read_text()
