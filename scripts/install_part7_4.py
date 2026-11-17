"""Safely install Part 7.4 into an existing Menu Engineering Bot checkout.

Run at repository root: python3 scripts/install_part7_4.py
This installer is idempotent and creates .part7_4.bak files.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "src/ui/styles.py"
EVALUATION = ROOT / "src/ui/sections/model_evaluation.py"
POLISH = ROOT / "src/ui/part7_polish.py"

CHART_OLD = '''        st.line_chart(
            chart_df.set_index("Date"),
            height=350,
        )'''
CHART_NEW = '''        if len(chart_df) < 2:
            st.info(
                "Only one held-out recorded date is available for this item. "
                "A trend line needs at least two dates; the actual and "
                "predicted values are shown below instead."
            )
            st.dataframe(chart_df, hide_index=True, width="stretch")
        else:
            st.line_chart(
                chart_df.set_index("Date"),
                height=350,
            )'''


def _backup(path: Path) -> None:
    backup = path.with_name(path.name + ".part7_4.bak")
    if not backup.exists():
        shutil.copy2(path, backup)


def install_styles() -> str:
    source = STYLES.read_text(encoding="utf-8")
    if "apply_part7_polish()" in source:
        return "Already installed"
    tree = ast.parse(source)
    fn = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef)
         and node.name == "apply_dashboard_styles"),
        None,
    )
    if fn is None or fn.end_lineno is None:
        raise RuntimeError("Can't locate apply_dashboard_styles in styles.py")
    if not POLISH.is_file():
        raise RuntimeError("Missing src/ui/part7_polish.py")
    lines = source.splitlines(keepends=True)
    addition = (
        "\n    # Part 7.4: additive, theme-aware polish.\n"
        "    from ui.part7_polish import apply_part7_polish\n\n"
        "    apply_part7_polish()\n"
    )
    lines.insert(fn.end_lineno, addition)
    updated = "".join(lines)
    ast.parse(updated)
    _backup(STYLES)
    STYLES.write_text(updated, encoding="utf-8")
    return "Installed"


def install_chart() -> str:
    source = EVALUATION.read_text(encoding="utf-8")
    if "Only one held-out recorded date is available for this item" in source:
        return "Already installed"
    if source.count(CHART_OLD) != 1:
        return "Skipped: chart code differs from expected layout (no change made)"
    updated = source.replace(CHART_OLD, CHART_NEW, 1)
    ast.parse(updated)
    _backup(EVALUATION)
    EVALUATION.write_text(updated, encoding="utf-8")
    return "Installed"


if __name__ == "__main__":
    print("Styles:", install_styles())
    print("One-date chart:", install_chart())
    print("Next: python3 -m ruff check src tests scripts")
