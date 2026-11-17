"""Presentation-only regression tests for Part 7.4."""

from ui.part7_polish import PART7_CSS, apply_part7_polish


def test_css_is_theme_aware_and_responsive():
    assert "@media (max-width: 850px)" in PART7_CSS
    assert "prefers-reduced-motion" in PART7_CSS
    assert "color-mix" in PART7_CSS
    assert "[data-testid=\"stMain\"]" in PART7_CSS


def test_polish_renders_css(monkeypatch):
    import ui.part7_polish as module

    calls = []
    monkeypatch.setattr(module.st, "markdown", lambda *a, **k: calls.append((a, k)))
    apply_part7_polish()
    assert len(calls) == 1
    assert calls[0][0] == (PART7_CSS,)
    assert calls[0][1]["unsafe_allow_html"] is True
