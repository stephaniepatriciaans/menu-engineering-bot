"""Tests for AI memo generation resilience."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import agent


def test_generate_menu_memo_rejects_empty_response(monkeypatch):
    """An empty Claude response must not be accepted."""

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    fake_response = SimpleNamespace(content=[])

    fake_client = Mock()
    fake_client.messages.create.return_value = fake_response

    import anthropic

    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        Mock(return_value=fake_client),
    )

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    with pytest.raises(
        RuntimeError,
        match="empty decision memo",
    ):
        agent.generate_menu_memo(summary)


def test_generate_menu_memo_rejects_whitespace_response(monkeypatch):
    """Whitespace-only Claude responses must not be accepted."""

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="   \n   ")
        ]
    )

    fake_client = Mock()
    fake_client.messages.create.return_value = fake_response

    import anthropic

    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        Mock(return_value=fake_client),
    )

    summary = pd.DataFrame({
        "item": ["Latte"],
        "price": [5.0],
    })

    with pytest.raises(
        RuntimeError,
        match="empty decision memo",
    ):
        agent.generate_menu_memo(summary)
