"""Regression tests for POS quarantine and financial data isolation."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_QUALITY = ROOT / "src/ui/pages/data_quality.py"


def test_quarantine_preserves_raw_financial_preview_inputs():
    """Quarantine must not replace the original POS accounting source."""
    source = DATA_QUALITY.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Eligible sales must come from the quarantine result.
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
    ]

    assert any(
        any(
            isinstance(target, ast.Name)
            and target.id == "analysis_raw_df"
            for target in node.targets
        )
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pos_review"
        and node.value.attr == "analysis_rows"
        for node in assignments
    )

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]

    def has_call_with_first_arg(function_name: str, arg_name: str) -> bool:
        return any(
            isinstance(call.func, ast.Name)
            and call.func.id == function_name
            and bool(call.args)
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == arg_name
            for call in calls
        )

    # Sales-only analytics must use eligible rows.
    assert has_call_with_first_arg(
        "adapt_to_canonical",
        "analysis_raw_df",
    )

    # Financial reconciliation must retain the original source.
    assert has_call_with_first_arg(
        "render_pos_reconciliation",
        "raw_df",
    )

    # Refund candidates must be recoverable from original rows.
    assert any(
        isinstance(call.func, ast.Name)
        and call.func.id == "adapt_to_canonical"
        and bool(call.args)
        and isinstance(call.args[0], ast.Subscript)
        and isinstance(call.args[0].value, ast.Attribute)
        and isinstance(call.args[0].value.value, ast.Name)
        and call.args[0].value.value.id == "raw_df"
        and call.args[0].value.attr == "loc"
        for call in calls
    )
