"""User-friendly error messages for AI memo generation."""

from __future__ import annotations

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)


def friendly_ai_error(exc: Exception) -> str:
    """Return a safe user-facing message for a Claude API failure.

    Never include raw exception details, requests, or API secrets.
    """
    if isinstance(exc, AuthenticationError):
        return (
            "Anthropic authentication failed. "
            "Check that your ANTHROPIC_API_KEY is valid."
        )

    if isinstance(exc, RateLimitError):
        return (
            "Claude is temporarily rate-limited. "
            "Please wait and try again later."
        )

    if isinstance(exc, APITimeoutError):
        return (
            "The Claude request timed out. "
            "Please try generating the memo again."
        )

    if isinstance(exc, APIConnectionError):
        return (
            "Could not connect to Claude. "
            "Check your internet connection and try again."
        )

    if isinstance(exc, APIStatusError):
        return (
            "Claude returned an API error. "
            "Please try again later."
        )

    if isinstance(exc, RuntimeError):
        if "empty decision memo" in str(exc).lower():
            return (
                "Claude returned an empty decision memo. "
                "Please try generating it again."
            )

        if "ANTHROPIC_API_KEY environment variable not set" in str(exc):
            return (
                "No Anthropic API key is configured. "
                "Memo generation is unavailable."
            )

    return (
        "The AI decision memo could not be generated. "
        "Please try again later."
    )
