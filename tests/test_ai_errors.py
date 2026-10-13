"""Tests for safe user-facing AI error messages."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_errors import friendly_ai_error


def test_friendly_ai_error_hides_sensitive_exception_details():
    """Unexpected failures must not expose internal error content."""

    secret = "sk-ant-example-secret-do-not-display"

    error = RuntimeError(
        f"Internal API failure involving key {secret}"
    )

    message = friendly_ai_error(error)

    assert secret not in message
    assert "Internal API failure" not in message
    assert "could not be generated" in message


def test_friendly_ai_error_recognizes_empty_response():
    """Known empty-response failures should be actionable."""

    error = RuntimeError(
        "Claude returned an empty decision memo. "
        "Please try generating it again."
    )

    message = friendly_ai_error(error)

    assert "empty decision memo" in message
    assert "try" in message.lower()
