"""Regression tests for the AI Decision Memo UI"""

import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memo_export import build_memo_export
from ui.sections import ai_decision_memo


class MockSessionState(dict):
    """Dictionary supporting Streamlit-style attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def make_inputs():
    """Create source data for memo generation."""

    summary = pd.DataFrame({
        "item": ["Latte"],
        "total_revenue": [500.0],
        "elasticity": [-1.2],
    })

    moves = pd.DataFrame({
        "item": ["Latte"],
        "new_price": [5.5],
        "daily_profit_delta": [12.5],
    })

    return summary, moves


def setup_mocks(monkeypatch, button_clicked=False):
    """Mock Streamlit output and session state."""

    widgets: dict[str, Any] = {
        "header": Mock(),
        "warning": Mock(),
        "button": Mock(return_value=button_clicked),
        "spinner": Mock(return_value=nullcontext()),
        "success": Mock(),
        "error": Mock(),
        "code": Mock(),
        "markdown": Mock(),
        "divider": Mock(),
        "subheader": Mock(),
        "columns": Mock(
            return_value=[
                nullcontext(),
                nullcontext(),
                nullcontext(),
            ]
        ),
        "download_button": Mock(),
        "caption": Mock(),
    }

    for name, mock in widgets.items():
        monkeypatch.setattr(
            ai_decision_memo.st,
            name,
            mock,
        )

    session = MockSessionState()

    monkeypatch.setattr(
        ai_decision_memo.st,
        "session_state",
        cast(Any, session),
    )

    widgets["session"] = session

    return widgets


def test_ai_memo_generation_and_downloads(monkeypatch):
    """Verify generation, caching, and all three downloads."""

    summary, moves = make_inputs()

    original_summary = summary.copy(deep=True)
    original_moves = moves.copy(deep=True)

    widgets = setup_mocks(
        monkeypatch,
        button_clicked=True,
    )

    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "test-key-not-real",
    )

    memo_text = "Increase Latte price to $5.50."

    generator_mock = Mock(
        return_value={
            "memo": memo_text,
            "audit": {
                "requires_review": False,
                "finding_count": 0,
                "findings": [],
            },
            "requires_review": False,
        }
    )

    monkeypatch.setattr(
        ai_decision_memo,
        "generate_menu_memo_with_audit",
        generator_mock,
    )

    pdf_mock = Mock(return_value=b"%PDF-test")

    ai_decision_memo.render_ai_decision_memo(
        summary=summary,
        moves=moves,
        business_name="My Coffee Shop",
        dataset_name="January Sales",
        currency="USD",
        cost_basis="actual",
        cost_is_assumption=False,
        capabilities={
            "price_optimization": True,
        },
        generate_memo_pdf=pdf_mock,
    )

    # The LLM receives the original analysis results.
    generator_mock.assert_called_once()

    generation_call = generator_mock.call_args

    assert generation_call.args[0] is summary
    assert generation_call.args[1] is moves

    assert generation_call.kwargs["metadata"]["business_name"] == (
        "My Coffee Shop"
    )

    assert generation_call.kwargs["capabilities"] == {
        "price_optimization": True,
    }

    # The memo is stored with its current fingerprint.
    session = widgets["session"]

    assert session.generated_memo == memo_text
    assert session.generated_memo_audit == {
        "requires_review": False,
        "finding_count": 0,
        "findings": [],
    }

    expected_export = build_memo_export(
        memo_text,
        session.generated_memo_audit,
    )

    assert "Financial Audit & Review Status" in expected_export
    assert "No issues detected by automated checks" in expected_export

    assert isinstance(session.generated_memo_context, str)
    assert len(session.generated_memo_context) == 64

    widgets["success"].assert_called_once_with(
        "AI decision memo generated. "
        "Review its financial claims before use."
    )

    # Streamlit display escapes dollar signs.
    assert widgets["markdown"].call_count == 2

    assert widgets["markdown"].call_args_list[0].args[0] == (
        "### Decision Memo"
    )

    assert widgets["markdown"].call_args_list[1].args[0] == (
        r"Increase Latte price to \$5.50."
    )

    # PDF generator receives original, unmodified memo.
    pdf_mock.assert_called_once_with(
        memo=expected_export,
        business_name="My Coffee Shop",
        dataset_name="January Sales",
    )

    # Verify all three download formats.
    assert widgets["download_button"].call_count == 3

    downloads = [
        call.kwargs
        for call in widgets["download_button"].call_args_list
    ]

    assert [download["file_name"] for download in downloads] == [
        "My_Coffee_Shop_decision_memo.md",
        "My_Coffee_Shop_decision_memo.txt",
        "My_Coffee_Shop_decision_memo.pdf",
    ]

    assert downloads[0]["data"] == expected_export.encode("utf-8")
    assert downloads[1]["data"] == expected_export.encode("utf-8")
    assert downloads[2]["data"] == b"%PDF-test"

    widgets["warning"].assert_not_called()
    widgets["error"].assert_not_called()

    # Rendering must not modify analysis results.
    assert_frame_equal(summary, original_summary)
    assert_frame_equal(moves, original_moves)


def test_ai_memo_missing_api_key_and_stale_cache(monkeypatch):
    """Verify missing configuration and old memo invalidation."""

    summary, moves = make_inputs()

    widgets = setup_mocks(monkeypatch)

    monkeypatch.delenv(
        "ANTHROPIC_API_KEY",
        raising=False,
    )

    # Simulate a memo from a previous dataset or settings.
    widgets["session"]["generated_memo"] = (
        "Old recommendation."
    )
    widgets["session"]["generated_memo_context"] = (
        "outdated-context-id"
    )

    pdf_mock = Mock()

    ai_decision_memo.render_ai_decision_memo(
        summary=summary,
        moves=moves,
        business_name="My Coffee Shop",
        dataset_name="January Sales",
        currency="USD",
        cost_basis="actual",
        cost_is_assumption=False,
        capabilities={
            "price_optimization": True,
        },
        generate_memo_pdf=pdf_mock,
    )

    widgets["header"].assert_called_once_with(
        "AI Decision Memo"
    )

    widgets["warning"].assert_called_once_with(
        "No ANTHROPIC_API_KEY is configured. "
        "All deterministic analytics still work; "
        "only memo generation is disabled."
    )

    # Stale recommendations must be cleared.
    session = widgets["session"]

    assert session.generated_memo is None
    assert session.generated_memo_context is None

    # No generation UI or memo downloads without the key.
    widgets["button"].assert_not_called()
    widgets["download_button"].assert_not_called()
    widgets["markdown"].assert_not_called()

    pdf_mock.assert_not_called()
    widgets["success"].assert_not_called()
    widgets["error"].assert_not_called()


# Test 1 — Audit warnings appear in the dashboard
def test_ai_memo_displays_financial_audit_warning(monkeypatch):
    """The dashboard must warn about flagged AI financial claims."""
    summary, moves = make_inputs()

    widgets = setup_mocks(
        monkeypatch,
        button_clicked=True,
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    generator_mock = Mock(
        return_value={
            "memo": "Increase Latte to $7.00.",
            "audit": {
                "requires_review": True,
                "finding_count": 1,
                "findings": [{
                    "claim": "Increase Latte to $7.00",
                    "reason": "Recommended price mismatch",
                    "expected_price": 5.50,
                    "requires_review": True,
                }],
            },
            "requires_review": True,
        }
    )

    monkeypatch.setattr(
        ai_decision_memo,
        "generate_menu_memo_with_audit",
        generator_mock,
    )

    pdf_mock = Mock(return_value=b"%PDF-test")

    ai_decision_memo.render_ai_decision_memo(
        summary=summary,
        moves=moves,
        business_name="My Coffee Shop",
        dataset_name="January Sales",
        currency="USD",
        cost_basis="actual",
        cost_is_assumption=False,
        capabilities={"price_optimization": True},
        generate_memo_pdf=pdf_mock,
    )

    assert widgets["session"].generated_memo_audit[
        "requires_review"
    ] is True

    widgets["warning"].assert_called()
    warning_texts = [
        str(call.args[0])
        for call in widgets["warning"].call_args_list
    ]
    assert any(
        "Financial claims require review" in text
        for text in warning_texts
    )


# Test 2 — Changing the dataset clears outdated audit results
def test_ai_memo_clears_stale_audit(monkeypatch):
    """A changed dataset must invalidate both the memo and its audit."""
    summary, moves = make_inputs()

    widgets = setup_mocks(
        monkeypatch,
        button_clicked=True,
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    generator_mock = Mock(
        return_value={
            "memo": "Increase Latte to $7.00.",
            "audit": {
                "requires_review": True,
                "finding_count": 1,
                "findings": [{
                    "claim": "Increase Latte to $7.00",
                    "reason": "Recommended price mismatch",
                    "requires_review": True,
                }],
            },
            "requires_review": True,
        }
    )

    monkeypatch.setattr(
        ai_decision_memo,
        "generate_menu_memo_with_audit",
        generator_mock,
    )

    kwargs = {
        "business_name": "My Coffee Shop",
        "dataset_name": "January Sales",
        "currency": "USD",
        "cost_basis": "actual",
        "cost_is_assumption": False,
        "capabilities": {"price_optimization": True},
        "generate_memo_pdf": Mock(return_value=b"%PDF-test"),
    }

    ai_decision_memo.render_ai_decision_memo(
        summary=summary,
        moves=moves,
        **kwargs,
    )

    session = widgets["session"]
    assert session.generated_memo is not None
    assert session.generated_memo_audit is not None

    # Simulate a dataset change without generating another memo.
    changed_summary = summary.copy(deep=True)
    changed_summary["item"] = "Different Menu Item"

    # The mocked button now behaves as unclicked.
    widgets["button"].return_value = False

    ai_decision_memo.render_ai_decision_memo(
        summary=changed_summary,
        moves=moves,
        **kwargs,
    )

    assert session.generated_memo is None
    assert session.generated_memo_audit is None
    assert session.generated_memo_context is None

    generator_mock.assert_called_once()


def test_failed_regeneration_clears_previous_memo(monkeypatch):
    """Failed regeneration must not leave a previous memo displayed."""

    summary, moves = make_inputs()

    widgets = setup_mocks(
        monkeypatch,
        button_clicked=True,
    )

    monkeypatch.setenv(
        "ANTHROPIC_API_KEY",
        "test-key-not-real",
    )

    generator_mock = Mock(
        side_effect=[
            {
                "memo": "Old memo: Increase Latte to $5.50.",
                "audit": {
                    "requires_review": False,
                    "finding_count": 0,
                    "findings": [],
                },
                "requires_review": False,
            },
            RuntimeError("Claude temporarily unavailable"),
        ]
    )

    monkeypatch.setattr(
        ai_decision_memo,
        "generate_menu_memo_with_audit",
        generator_mock,
    )

    kwargs = {
        "summary": summary,
        "moves": moves,
        "business_name": "My Coffee Shop",
        "dataset_name": "January Sales",
        "currency": "USD",
        "cost_basis": "actual",
        "cost_is_assumption": False,
        "capabilities": {"price_optimization": True},
        "generate_memo_pdf": Mock(return_value=b"%PDF-test"),
    }

    # First generation succeeds.
    ai_decision_memo.render_ai_decision_memo(**kwargs)

    session = widgets["session"]

    assert session.generated_memo is not None
    assert session.generated_memo_audit is not None

    # Second generation fails.
    ai_decision_memo.render_ai_decision_memo(**kwargs)

    assert generator_mock.call_count == 2

    assert session.generated_memo is None
    assert session.generated_memo_audit is None
    assert session.generated_memo_context is None

    widgets["error"].assert_called()
