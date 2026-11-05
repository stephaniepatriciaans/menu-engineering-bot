"""Build a source-of-truth memo section from item-level analytics.

Only supplied computed columns become factual statements. The LLM's narrative
is deliberately excluded from export because arbitrary prose cannot be
reliably verified with a collection of regex replacements.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from config import format_currency


def _text(value: object) -> str:
    """Escape Markdown table separators and normalize labels."""
    return str(value).replace("|", r"\|").replace("\n", " ").strip()


def _number(value: object, decimals: int = 0) -> str:
    """Format a finite numeric observation, without fabricating missing data."""
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number) or not (-float("inf") < float(number) < float("inf")):
        return "Not available"
    return f"{float(number):,.{decimals}f}"


def _rows_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cells) + " |" for cells in rows)
    return "\n".join(output)


def build_verified_memo(
    summary: pd.DataFrame,
    currency: str,
    *,
    cost_basis: str | None = None,
    max_items: int = 8,
) -> str:
    """Produce deterministic item counts, classifications and evidence tables.

    No source records, summary records or monetary values are changed. Charge
    flags are provisional and do not imply exclusion from revenue totals.
    """
    if max_items < 1:
        raise ValueError("max_items must be at least 1")
    if "item" not in summary.columns:
        raise ValueError("Item summary must have an item column")


    df = summary.copy(deep=False)

    lines = [
        "# Data-backed Menu Review",
        "",
        (
            "This section is generated from the application's computed item summary, "
            "not from AI-written claims. The figures describe sales-only data and "
            "do not constitute verified net revenue or causal price effects."
        ),
        "",
        f"**Items in analysis:** {len(df):,}.",
    ]


    if "total_revenue" in df.columns:
        revenue = pd.to_numeric(df["total_revenue"], errors="coerce")
        if revenue.notna().all():
            lines.append(
                f"**Sum of item-level gross sales revenue:** "
                f"{format_currency(revenue.sum(), currency)} "
                "(before refund reconciliation)."
            )

    lines.extend(["", "## Possible Operational Charges — Manual Classification Required", ""])
    if "possible_operational_charge" not in df.columns:
        lines.append("Operational-charge review flags are not available for this dataset.")
    else:
        mask = df["possible_operational_charge"].fillna(False).eq(True)
        flagged = df.loc[mask]
        lines.append(f"**Charge-like item labels flagged:** {len(flagged):,}.")
        lines.append(
            "These are review candidates, **not verified operational charges**. "
            "They remain in the reported sales-only totals until independently classified."
        )
        if not flagged.empty:
            headers = ["Item"]
            if "total_revenue" in df.columns:
                headers.append("Sales-only revenue")
            headers.append("Review reason")
            entries = []
            for _, row in flagged.iterrows():
                entry = [_text(row["item"])]
                if "total_revenue" in df.columns:
                    amount = pd.to_numeric(pd.Series([row["total_revenue"]]), errors="coerce").iloc[0]
                    entry.append(format_currency(amount, currency) if pd.notna(amount) else "Not available")
                entry.append(_text(row.get("reliability_review_reason", "Review description")) or "Review description")
                entries.append(entry)
            lines.extend(["", _rows_table(headers, entries)])

    lines.extend(["", "## Historical Elasticity Evidence", ""])
    if {"elasticity_source", "elasticity_confidence"}.issubset(df.columns):
        source = df["elasticity_source"].fillna("").astype(str).str.casefold()
        conf = df["elasticity_confidence"].fillna("").astype(str).str.casefold()
        estimated = source.eq("estimated")
        high = int((estimated & conf.eq("high")).sum())
        low = int((estimated & conf.eq("low")).sum())
        other = int((estimated & ~conf.isin(["high", "low"])).sum())
        assumed = int((~estimated).sum())
        lines.append(f"**Historically estimated items:** {int(estimated.sum()):,}.")
        lines.append(f"**High / Low / Other estimated-confidence labels:** {high:,} / {low:,} / {other:,}.")
        lines.append(f"**Items without item-level historical estimates:** {assumed:,}.")
        if assumed:
            priors = df.loc[~estimated, "elasticity_source"].fillna("Unspecified").astype(str).value_counts()
            lines.append("**Non-estimated source labels:** " + "; ".join(f"{_text(label)}: {count:,}" for label, count in priors.items()) + ".")
        lines.append(
            "High/Low are heuristic reliability labels, **not** measured forecast "
            "accuracy, causal evidence, or statistical confidence intervals."
        )
    else:
        lines.append("Item-level elasticity evidence labels are unavailable.")

    if {"item", "elasticity", "elasticity_source", "elasticity_confidence"}.issubset(df.columns):
        lines.extend(["", "### Sample item-level elasticity evidence", ""])
        cols = ["Item", "Elasticity", "Evidence / label"]
        extras = [
            ("price_points", "Price points", 0),
            ("observations", "Obs.", 0),
            ("price_variation_%", "Price var. %", 1),
        ]
        active = [(key, label, dp) for key, label, dp in extras if key in df.columns]
        cols += [label for _, label, _ in active]
        candidates = df
        if "possible_operational_charge" in df.columns:
            candidates = df.loc[~df["possible_operational_charge"].fillna(False).eq(True)]
        if "total_revenue" in candidates.columns:
            candidates = candidates.assign(_sort_revenue=pd.to_numeric(candidates["total_revenue"], errors="coerce"))
            candidates = candidates.sort_values("_sort_revenue", ascending=False, kind="stable")
        entries = []
        for _, row in candidates.head(max_items).iterrows():
            entry = [
                _text(row["item"]), _number(row["elasticity"], 2),
                _text(row["elasticity_source"]) + " / " + _text(row["elasticity_confidence"]),
            ]
            entry.extend(_number(row[key], dp) for key, _, dp in active)
            entries.append(entry)
        if entries:
            lines.append(_rows_table(cols, entries))
            lines.append(
                "Price points count distinct prices; observations count recorded evidence. "
                "These are not interchangeable. An estimate's elasticity value "
                "must not be interpreted as a validated response to a price change."
            )

    lines.extend([
        "", "## Report Limitations", "",
        "- Source-level refunds, discounts and settlement totals are not reconciled here.",
        "- Potential operational charges require human classification; no lines are removed here.",
        "- Price-response estimates describe association, not a confirmed causal effect.",
        "- This data-backed summary excludes unverified numerical claims from AI commentary.",
    ])
    if cost_basis is not None and str(cost_basis).casefold() in {"missing", "unavailable", "none", "unknown"}:
        lines.append("- Verified unit costs are unavailable, so item margins and profits cannot be established.")
    return "\n".join(lines).rstrip() + "\n"
