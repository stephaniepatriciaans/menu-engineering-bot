
"""Correct identifiable memo inconsistencies using deterministic data.

Only the display/export narrative is changed. Original source data
and financial calculations remain untouched.
"""

from __future__ import annotations

import re

import pandas as pd

from config import format_currency

_NUMBER_WORDS = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|[\d,]+"
)

_CHARGE_CLAIMS = (
    # Example: Three items require classification review...
    re.compile(
        rf"^(?:{_NUMBER_WORDS})\s+items?\s+require "
        r"classification review before any pricing action "
        r"is taken:.*?(?=\n\s*\n|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ),
    # Example: Three items - POSTAGE, Manual, and ...
    # have been flagged as possible operational charges.
    re.compile(
        rf"^(?:{_NUMBER_WORDS})\s+items?\s*[-–—]\s*"
        r".*?have been flagged as possible operational charges"
        r".*?(?=\n\s*\n|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ),
    # Example: Five items are flagged as possible
    # operational charges, followed by a bullet list.
    re.compile(
        rf"^(?:{_NUMBER_WORDS})\s+items?\s+are flagged "
        r"as possible operational charges"
        r".*?(?=\n\s*\n|\Z)"
        r"(?:\n\s*\n\s*[•*-][^\n]*)?",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ),
)

_CONFIDENCE_COUNTS = re.compile(
    r"\((?P<high>[\d,]+) rated high-confidence, "
    r"(?P<low>[\d,]+) low-confidence\)"
)


def reconcile_memo_consistency(
    memo: str,
    item_summary: pd.DataFrame,
    currency: str,
) -> str:
    """Correct recognizable count mismatches using item-level facts."""
    result = str(memo)

    if item_summary is None or item_summary.empty:
        return result

    summary = item_summary

    # Correct operational-charge review claims.
    if {"item", "possible_operational_charge"}.issubset(
        summary.columns
    ):
        flagged = summary.loc[
            summary["possible_operational_charge"]
            .fillna(False)
            .astype(bool)
        ]

        if not flagged.empty:
            entries = []

            for _, row in flagged.iterrows():
                name = str(row["item"])
                revenue = row.get("total_revenue")

                if pd.notna(revenue):
                    name += (
                        f" ({format_currency(revenue, currency)})"
                    )

                entries.append(name)

            replacement = (
                f"**{len(flagged):,} charge-like item labels require "
                "classification review before merchandise pricing "
                "decisions:** "
                + ", ".join(entries)
                + ". These are review candidates, not verified "
                "operational charges. Their sales-only gross "
                "revenue remains included."
            )

            for pattern in _CHARGE_CLAIMS:
                result = pattern.sub(
                    lambda _: replacement,
                    result,
                    count=1,
                )

    # Explain historical elasticity confidence counts.
    required = {
        "elasticity_source",
        "elasticity_confidence",
    }

    if required.issubset(summary.columns):
        source = (
            summary["elasticity_source"]
            .fillna("")
            .astype(str)
        )
        confidence = (
            summary["elasticity_confidence"]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        estimated = source.eq("estimated")

        high = int(
            (estimated & confidence.eq("high")).sum()
        )
        low = int(
            (estimated & confidence.eq("low")).sum()
        )
        other = int(
            (
                estimated
                & ~confidence.isin(("high", "low"))
            ).sum()
        )

        def fix_count(match: re.Match[str]) -> str:
            old_high = int(
                match.group("high").replace(",", "")
            )
            old_low = int(
                match.group("low").replace(",", "")
            )

            if (
                old_high != high
                or old_low != low
                or other == 0
            ):
                return match.group(0)

            return (
                f"({high:,} rated high-confidence, "
                f"{low:,} low-confidence, "
                f"and {other:,} with other or missing "
                "confidence labels)"
            )

        result = _CONFIDENCE_COUNTS.sub(
            fix_count,
            result,
            count=1,
        )

    return result
