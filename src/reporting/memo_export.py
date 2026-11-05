"""Prepare AI decision memos for safe export."""

from __future__ import annotations

from typing import Any


def build_memo_export(
    memo: str,
    audit: dict[str, Any] | None,
    refund_candidate_count: int = 0,
) -> str:
    """Append financial audit context to an AI-generated memo.

    The original memo is preserved.
    Audit findings are diagnostic, not definitive proof of errors.
    """
    sections = []

    if refund_candidate_count < 0:
        raise ValueError("Refund candidate count cannot be negative.")

    if refund_candidate_count > 0:
        sections.append(
            "\n---\n\n"
            "## POS Transaction Accounting Disclosure\n\n"
            f"{refund_candidate_count:,} negative-quantity "
            "transaction(s) were identified as refund candidates "
            "and excluded from sales-only analysis.\n\n"
            "Reported sales revenue, contribution profit, "
            "demand estimates, and pricing simulations do not "
            "include potential refund adjustments. "
            "These figures must not be interpreted as net "
            "revenue or refund-adjusted profit.\n\n"
            "Refund candidates require review against the "
            "original POS records before their accounting "
            "treatment can be confirmed."
        )

    sections.append(memo.rstrip())

    sections.append("\n---\n\n## Financial Audit & Review Status\n")

    if audit is None:
        sections.append(
            "**Audit status: Not available**\n\n"
            "No automated financial audit report was provided. "
            "All financial claims require independent review."
        )

        return "\n".join(sections).strip() + "\n"

    findings = audit.get("findings", [])
    requires_review = bool(audit.get("requires_review", False))

    if requires_review:
        sections.append(
            "**Audit status: Review required**\n\n"
            "The automated checks identified financial claims "
            "that should be compared with the deterministic "
            "analysis results before making business decisions."
        )

        if not findings:
            sections.append(
                "\nThe audit requested review but did not provide individual findings."
            )

        for index, finding in enumerate(findings, start=1):
            claim = str(finding.get("claim", "Unspecified claim"))
            reason = str(
                finding.get(
                    "reason",
                    "Financial claim requires review.",
                )
            )

            sections.append(f"\n{index}. **Claim:** {claim}\n   **Reason:** {reason}")

    else:
        sections.append(
            "**Memo-claim check status: No discrepancies found in the "
            "limited checks performed**\n\n"
            "These checks do not reconcile POS settlement totals "
            "or verify gross versus net revenue, refunds, discounts, "
            "charge classifications, or factual accuracy."
        )

    sections.append(
        "\n**Important limitation:** The financial audit "
        "uses limited, pattern-based checks and does not "
        "verify every numerical or qualitative claim. "
        "AI-generated recommendations require human review."
    )

    return "\n".join(sections).strip() + "\n"
