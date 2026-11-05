"""Add the read-only Part 5 panel to an existing refactored application.

Run once from the repository root: python3 scripts/install_part5.py
Fails closed if the known integration anchor is absent; it never overwrites the page.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src/ui/pages/data_quality.py"
IMPORT_LINE = "from ui.menu_quality import render_menu_quality"
ANCHOR = '    # POS transaction accounting preview'


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "render_menu_quality(raw_df, mapping)" in text:
        print("Part 5 is already integrated; no changes made.")
        return
    if "def render_data_quality(setup: SetupData)" not in text:
        raise RuntimeError("Unexpected data-quality page: installation stopped without changes.")
    if text.count(ANCHOR) != 1:
        raise RuntimeError("Cannot find a unique integration anchor; no changes made.")
    if IMPORT_LINE not in text:
        import_anchor = "from ui.pages.data_setup import SetupData"
        if text.count(import_anchor) != 1:
            raise RuntimeError("Cannot find page import anchor; no changes made.")
        text = text.replace(import_anchor, import_anchor + "\n" + IMPORT_LINE, 1)
    marker = "    # ================================================================\n" + ANCHOR
    replacement = (
        "    # Read-only Part 5 menu data quality; never changes financial rows.\n"
        "    render_menu_quality(raw_df, mapping)\n\n"
        + marker
    )
    if text.count(marker) != 1:
        raise RuntimeError("Cannot find a unique section boundary; no changes made.")
    text = text.replace(marker, replacement, 1)
    import ast

    ast.parse(text, filename=str(TARGET))
    TARGET.write_text(text, encoding="utf-8")
    print("Installed Part 5 Menu Data Quality in src/ui/pages/data_quality.py")


if __name__ == "__main__":
    main()
