"""Conservative checks for numerical claims in AI-generated memos"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


def _financial_values(
    summary_df: pd.DataFrame,
    moves_df: pd.DataFrame | None,
) -> set[Decimal]:
    """Collect explicitly supplied financial amounts."""
    allowed: set[Decimal] = set()

    columns = {
        "price",
        "unit_cost",
        "total_revenue",
        "total_profit",
        "old_price",
        "new_price",
        "daily_profit_delta",
        "best_case_daily_profit_delta",
        "base_case_daily_profit_delta",
        "worst_case_daily_profit_delta",
    }

    for frame in (summary_df, moves_df):
        if frame is None or frame.empty:
            continue

        for column in columns.intersection(frame.columns):
            for value in frame[column].dropna():
                try:
                    number = Decimal(str(value))
                except (InvalidOperation, ValueError):
                    continue

                if number.is_finite():
                    allowed.add(number.quantize(Decimal("0.01")))
                    allowed.add(abs(number).quantize(Decimal("0.01")))

    return allowed


def audit_memo_financial_claims(
    memo: str,
    summary_df: pd.DataFrame,
    moves_df: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """Flag unfamiliar dollar-denominated claims for human review.

    This is a heuristic audit, not proof of factual accuracy.
    It currently recognizes USD-style dollar amounts only.
    """
    allowed = _financial_values(summary_df, moves_df)

    pattern = re.compile(
        r"(?<!\w)\$\s*(-?\d[\d,]*(?:\.\d{1,2})?)"
    )

    findings: list[dict[str, Any]] = []

    for match in pattern.finditer(memo):
        raw = match.group(1).replace(",", "")

        try:
            amount = Decimal(raw).quantize(Decimal("0.01"))
        except InvalidOperation:
            continue

        if amount not in allowed and abs(amount) not in allowed:
            findings.append({
                "claim": match.group(0),
                "amount": float(amount),
                "reason": (
                    "This monetary amount was not found among "
                    "the supplied deterministic financial values."
                ),
                "requires_review": True,
            })

    return findings


def audit_item_price_claims(
    memo: str,
    summary_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Flag incorrect item-price statements for review.

    Recognizes simple '<item> costs/is priced at $X' statements.
    This is intentionally limited to explicit price claims.
    """
    if summary_df is None or summary_df.empty:
        return []

    if not {"item", "price"}.issubset(summary_df.columns):
        return []

    findings: list[dict[str, Any]] = []

    for _, row in summary_df.iterrows():
        item = str(row["item"])

        try:
            expected = Decimal(str(row["price"])).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, ValueError):
            continue

        if not expected.is_finite():
            continue

        pattern = re.compile(
            rf"(?<!\w){re.escape(item)}\s+"
            r"(?:costs|is priced at)\s+"
            r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(memo):
            try:
                claimed = Decimal(
                    match.group(1).replace(",", "")
                ).quantize(Decimal("0.01"))
            except InvalidOperation:
                continue

            if claimed != expected:
                findings.append({
                    "item": item,
                    "claim": match.group(0),
                    "claimed_price": float(claimed),
                    "expected_price": float(expected),
                    "reason": (
                        "The stated item price differs from "
                        "the deterministic item summary."
                    ),
                    "requires_review": True,
                })

    return findings


def audit_recommended_price_claims(
    memo: str,
    moves_df: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    """Flag incorrect explicit recommended-price claims.

    Recognizes simple phrases such as:
    'Increase Latte to $X' and 'Set Latte price to $X'.

    This is a limited deterministic check, not a complete
    natural-language factual verification system.
    """
    if moves_df is None or moves_df.empty:
        return []

    if not {"item", "new_price"}.issubset(moves_df.columns):
        return []

    findings: list[dict[str, Any]] = []

    for _, row in moves_df.iterrows():
        item = str(row["item"])

        try:
            expected = Decimal(str(row["new_price"])).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, ValueError):
            continue

        if not expected.is_finite():
            continue

        pattern = re.compile(
            rf"(?:increase|raise|decrease|lower|set)\s+"
            rf"{re.escape(item)}(?:\s+price)?\s+to\s+"
            r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(memo):
            try:
                claimed = Decimal(
                    match.group(1).replace(",", "")
                ).quantize(Decimal("0.01"))
            except InvalidOperation:
                continue

            if claimed != expected:
                findings.append({
                    "item": item,
                    "claim": match.group(0),
                    "claimed_price": float(claimed),
                    "expected_price": float(expected),
                    "reason": (
                        "The stated recommended price differs "
                        "from the deterministic pricing result."
                    ),
                    "requires_review": True,
                })

    return findings


def audit_item_profit_impact_claims(
    memo: str,
    moves_df: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    """Flag incorrect item-specific daily contribution-profit claims.

    Recognizes explicit phrases such as:
    'Latte adds $0.80 per day'
    'Tea increases daily profit by $1.50'

    This is a limited text-pattern audit, not complete
    natural-language fact verification.
    """
    if moves_df is None or moves_df.empty:
        return []

    required = {"item", "daily_profit_delta"}

    if not required.issubset(moves_df.columns):
        return []

    findings: list[dict[str, Any]] = []

    for _, row in moves_df.iterrows():
        item = str(row["item"])

        try:
            expected = Decimal(
                str(row["daily_profit_delta"])
            ).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            continue

        if not expected.is_finite():
            continue

        escaped_item = re.escape(item)

        patterns = [
            re.compile(
                rf"(?<!\w){escaped_item}\s+"
                r"(?:adds|generates)\s+"
                r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)"
                r"\s+per\s+day",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?<!\w){escaped_item}\s+"
                r"(?:increases|improves)\s+daily\s+"
                r"(?:contribution\s+)?profit\s+by\s+"
                r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)",
                re.IGNORECASE,
            ),
        ]

        for pattern in patterns:
            for match in pattern.finditer(memo):
                try:
                    claimed = Decimal(
                        match.group(1).replace(",", "")
                    ).quantize(Decimal("0.01"))
                except InvalidOperation:
                    continue

                if claimed != expected:
                    findings.append({
                        "item": item,
                        "claim": match.group(0),
                        "claimed_daily_profit_delta": float(claimed),
                        "expected_daily_profit_delta": float(expected),
                        "reason": (
                            "The stated daily contribution-profit "
                            "change differs from the deterministic "
                            "pricing recommendation."
                        ),
                        "requires_review": True,
                    })

    return findings


def audit_generated_memo(
    memo: str,
    summary_df: pd.DataFrame,
    moves_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Combine all deterministic AI memo checks into one report.

    Findings are review flags, not definitive hallucination labels.
    An empty findings list does not guarantee a factually correct memo.
    """
    scenario_findings = audit_item_scenario_claims(
        memo,
        moves_df,
    )
    
    financial_findings = audit_memo_financial_claims(
        memo,
        summary_df,
        moves_df,
    )

    current_price_findings = audit_item_price_claims(
        memo,
        summary_df,
    )

    recommended_price_findings = audit_recommended_price_claims(
        memo,
        moves_df,
    )

    profit_impact_findings = audit_item_profit_impact_claims(
        memo,
        moves_df,
    )

    findings = (
        financial_findings
        + scenario_findings
        + current_price_findings
        + recommended_price_findings
        + profit_impact_findings
    )

    return {
        "requires_review": bool(findings),
        "finding_count": len(findings),
        "findings_by_type": {
            "unfamiliar_amount": len(financial_findings),
            "scenario_mismatch": len(scenario_findings),
            "current_price_mismatch": len(current_price_findings),
            "recommended_price_mismatch": len(
                recommended_price_findings
            ),
            "profit_impact_mismatch": len(profit_impact_findings),
        },
        "findings": findings,
        "audit_limitations": (
            "This is a limited, pattern-based financial audit. "
            "It does not verify all numerical or qualitative claims."
        ),
    }


def audit_item_scenario_claims(
    memo: str,
    moves_df: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    """Check explicit item-specific base/worst-case profit claims.

    Supports common single-line phrasing such as:
    'Latte — base-case $14.03 (worst case $4.34)'
    'Matcha Latte — base-case gain of $3.90'

    Checks monetary values against deterministic scenario
    results. This is a limited pattern-based audit.
    """
    if moves_df is None or moves_df.empty:
        return []

    required = {
        "item",
        "base_case_daily_profit_delta",
        "worst_case_daily_profit_delta",
    }

    if not required.issubset(moves_df.columns):
        return []

    findings: list[dict[str, Any]] = []

    # Normalize common Markdown formatting for matching.
    normalized = re.sub(r"(?<!\\)\\\$", "$", memo)
    normalized = normalized.replace("**", "").replace("__", "")

    scenario_columns = {
        "base_case": "base_case_daily_profit_delta",
        "worst_case": "worst_case_daily_profit_delta",
    }

    amount_pattern = (
        r"(?<!\w)(?:-\s*\$\s*|\$\s*-?\s*)"
        r"\d[\d,]*(?:\.\d{1,2})?"
    )

    for line in normalized.splitlines():
        for _, row in moves_df.iterrows():
            item = str(row["item"])

            item_match = re.search(
                rf"(?<!\w){re.escape(item)}(?!\w)",
                line,
                re.IGNORECASE,
            )

            if item_match is None:
                continue

            # Only audit a line if it names exactly one
            # known item, preventing cross-item matching.
            named_items = [
                str(name)
                for name in moves_df["item"].dropna().unique()
                if re.search(
                    rf"(?<!\w){re.escape(str(name))}(?!\w)",
                    line,
                    re.IGNORECASE,
                )
            ]

            if len(named_items) != 1:
                continue

            item_text = line[item_match.end():]

            for scenario, column in scenario_columns.items():
                try:
                    expected = Decimal(
                        str(row[column])
                    ).quantize(Decimal("0.01"))
                except (InvalidOperation, ValueError):
                    continue

                if not expected.is_finite():
                    continue

                scenario_label = scenario.replace("_", r"[\s-]+")

                pattern = re.compile(
                    rf"\b{scenario_label}\b"
                    rf"[^\n$]{{0,90}}?"
                    rf"({amount_pattern})",
                    re.IGNORECASE,
                )

                match = pattern.search(item_text)

                if match is None:
                    continue

                raw_amount = match.group(1)
                negative = "-" in raw_amount
                digits = re.sub(r"[^\d.]", "", raw_amount)

                try:
                    claimed = Decimal(digits)
                    if negative:
                        claimed = -claimed
                    claimed = claimed.quantize(
                        Decimal("0.01")
                    )
                except InvalidOperation:
                    continue

                if claimed != expected:
                    findings.append({
                        "item": item,
                        "scenario": scenario,
                        "claim": match.group(0),
                        "claimed_daily_profit_delta": float(
                            claimed
                        ),
                        "expected_daily_profit_delta": float(
                            expected
                        ),
                        "reason": (
                            f"The {scenario.replace('_', '-')} "
                            "profit claim differs from the "
                            "deterministic scenario result."
                        ),
                        "requires_review": True,
                    })

    return findings
