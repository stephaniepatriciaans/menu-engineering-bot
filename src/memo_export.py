"""Prepare AI decision memos for safe export."""

from __future__ import annotations

from typing import Any


def build_memo_export(
    memo: str,
    audit: dict[str, Any] | None,
) -> str:
    """Append financial audit context to an AI-generated memo.

    The original memo is preserved.
    Audit findings are diagnostic, not definitive proof of errors.
    """
    sections = [memo.rstrip()]

    sections.append(
        "\n---\n\n"
        "## Financial Audit & Review Status\n"
    )

    if audit is None:
        sections.append(
            "**Audit status: Not available**\n\n"
            "No automated financial audit report was provided. "
            "All financial claims require independent review."
        )

        return "\n".join(sections).strip() + "\n"

    findings = audit.get("findings", [])
    requires_review = bool(
        audit.get("requires_review", False)
    )

    if requires_review:
        sections.append(
            "**Audit status: Review required**\n\n"
            "The automated checks identified financial claims "
            "that should be compared with the deterministic "
            "analysis results before making business decisions."
        )

        if not findings:
            sections.append(
                "\nThe audit requested review but did not "
                "provide individual findings."
            )

        for index, finding in enumerate(findings, start=1):
            claim = str(
                finding.get("claim", "Unspecified claim")
            )
            reason = str(
                finding.get(
                    "reason",
                    "Financial claim requires review.",
                )
            )

            sections.append(
                f"\n{index}. **Claim:** {claim}\n"
                f"   **Reason:** {reason}"
            )

    else:
        sections.append(
            "**Audit status: No issues detected by "
            "automated checks**\n\n"
            "No issues were identified by the limited "
            "financial audit. This does not guarantee "
            "that the memo is factually accurate."
        )

    sections.append(
        "\n**Important limitation:** The financial audit "
        "uses limited, pattern-based checks and does not "
        "verify every numerical or qualitative claim. "
        "AI-generated recommendations require human review."
    )

    return "\n".join(sections).strip() + "\n"
