"""Installer should be deterministic and reject unknown source layouts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "scripts" / "install_part7_1_3.py"
spec = importlib.util.spec_from_file_location("part7_installer", INSTALLER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_model_ui_installer_rejects_unknown_layout():
    with pytest.raises(RuntimeError, match="model UI import"):
        module.patch_model_ui("# unexpected source")


def test_upload_installer_idempotent():
    first = module.patch_upload("def load_uploaded_sales(\n    uploaded\n):\n    return uploaded\n")
    second = module.patch_upload(first)
    assert first == second
    assert first.count("def load_uploaded_sales(") == 1
    assert "def _load_uploaded_sales_uncached(" in first
