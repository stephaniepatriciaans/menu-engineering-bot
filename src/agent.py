"""LLM explanation layer for deterministic menu-engineering results."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from config import format_currency

load_dotenv()

SYSTEM_PROMPT = """You are a menu-engineering consultant writing a short, practical decision memo for a restaurant, cafe, or food-service manager.

You receive only deterministic outputs already calculated by the application. Your job is to explain and prioritize them.

Rules:
- Do NOT invent, alter, recompute, or extrapolate numbers.
- Use only analyses and fields supplied in the prompt.
- Never imply unit cost, margin, profit, or profit optimization exists when profit analysis is unavailable.
- If cost data is an explicit scenario assumption, call it an assumption rather than actual cost.
- "estimated" means an elasticity estimate calculated from historical
  price and quantity observations. It does not prove causality.
- "category_prior" means an assumed elasticity based on the product
  category, not an estimate from that item's historical price changes.
- "default_prior" means a general assumed elasticity.
- Never describe a prior as a historical estimate.
- Never claim that no historical estimates exist if the supplied
  elasticity summary reports one or more.
- Distinguish low-confidence estimates from high-confidence estimates.
- Low-confidence estimates are exploratory and should not support
  definitive pricing decisions.
- Use the supplied elasticity counts when describing overall reliability.
- Translate technical fields into plain business language. Avoid statistics jargon unless needed to explain uncertainty.
- Keep recommendations practical and prioritized; do not mechanically list every item.
- Respect the supplied currency and business/dataset metadata.
- Keep the memo under 450 words.
- Do not use footnotes. Put important caveats inline.
- Use clean Markdown with short paragraphs and clear headings.
- Put spaces around bold text and between product names and numbers.
- Never concatenate item names, currency amounts, or Markdown markers.
- Avoid unnecessary bold formatting for individual numbers.
- Use numbered recommendations only when they improve readability.

Formatting rules:
- Write clean, valid Markdown.
- Use descriptive headings with ## or ###.
- Separate paragraphs with blank lines.
- Use bold only for important product names or conclusions.
- Always include spaces between product names, numbers, and punctuation.
- Never put Markdown formatting characters inside product names.
- Never join two product names or numerical values together.
- Format revenue and price values using the supplied currency.
- Prefer short paragraphs and concise numbered recommendations.
- Do not use HTML, code blocks, tables, or footnotes.
- Before responding, check that all Markdown markers are balanced.
"""


def _safe_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    present = [column for column in columns if column in df.columns]
    if not present:
        return []
    clean = df[present].copy()
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def clean_memo_markdown(memo: str) -> str:
    """
    Perform conservative cleanup of generated Markdown.

    Preserve product names, financial values, numerical
    findings, and existing valid Markdown formatting.
    """
    import re

    if not memo:
        return ""

    # Normalize line endings.
    memo = memo.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing whitespace from lines.
    memo = "\n".join(
        line.rstrip()
        for line in memo.split("\n")
    )

    # Limit excessive blank lines to two.
    memo = re.sub(r"\n{3,}", "\n\n", memo)

    # Remove spaces before punctuation,
    # except where doing so might affect Markdown syntax.
    memo = re.sub(
        r"(?<=\w) +([,;:!?])",
        r"\1",
        memo,
    )

    return memo.strip()


def build_elasticity_summary(
    summary_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Summarize elasticity reliability using deterministic counts.

    No calculations are delegated to the language model.
    """

    if summary_df is None or summary_df.empty:
        return {
            "total_items": 0,
            "historically_estimated_items": 0,
            "category_prior_items": 0,
            "default_prior_items": 0,
            "low_confidence_estimates": 0,
            "high_confidence_estimates": 0,
        }

    sources = (
        summary_df["elasticity_source"]
        if "elasticity_source" in summary_df.columns
        else pd.Series("", index=summary_df.index)
    )

    confidence = (
        summary_df["elasticity_confidence"]
        if "elasticity_confidence" in summary_df.columns
        else pd.Series("", index=summary_df.index)
    )

    sources = sources.fillna("").astype(str)
    confidence = confidence.fillna("").astype(str).str.lower()

    estimated = sources.eq("estimated")

    return {
        "total_items": int(len(summary_df)),

        "historically_estimated_items": int(
            estimated.sum()
        ),

        "category_prior_items": int(
            sources.eq("category_prior").sum()
        ),

        "default_prior_items": int(
            sources.eq("default_prior").sum()
        ),

        "low_confidence_estimates": int(
            (estimated & confidence.eq("low")).sum()
        ),

        "high_confidence_estimates": int(
            (estimated & confidence.eq("high")).sum()
        ),
    }


def build_user_prompt(
    summary_df: pd.DataFrame,
    moves_df: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
    capabilities: dict[str, bool] | None = None,
) -> str:
    """Serialize only computed results that actually exist into the LLM prompt."""
    metadata = dict(metadata or {})
    capabilities = dict(capabilities or {})
    currency = str(metadata.get("currency", "USD"))

    summary_records = _safe_records(
        summary_df,
        [
            "item", "category", "price", "avg_daily_units", "total_units_sold",
            "total_revenue", "unit_cost", "contribution_margin_%", "total_profit",
            "quadrant", "elasticity", "elasticity_source", "elasticity_confidence",
            "price_points", "observations", "price_variation_%",
        ],
    )
    for record in summary_records:
        if record.get("price") is not None:
            record["price_display"] = format_currency(record["price"], currency)
        if record.get("total_revenue") is not None:
            record["total_revenue_display"] = format_currency(record["total_revenue"], currency)
        if record.get("unit_cost") is not None:
            record["unit_cost_display"] = format_currency(record["unit_cost"], currency)
        if record.get("total_profit") is not None:
            record["total_profit_display"] = format_currency(record["total_profit"], currency)

    moves_records: list[dict[str, Any]] = []
    if moves_df is not None and not moves_df.empty:
        moves_records = _safe_records(
            moves_df,
            [
                "item", "old_price", "new_price", "pct_change_recommended",
                "daily_profit_delta", "quadrant", "elasticity",
                "elasticity_source", "elasticity_confidence",
            ],
        )
        for record in moves_records:
            for field in ["old_price", "new_price", "daily_profit_delta"]:
                if record.get(field) is not None:
                    record[f"{field}_display"] = format_currency(record[field], currency)

    elasticity_summary = build_elasticity_summary(summary_df)
    sections = [
        "BUSINESS / DATASET METADATA:\n"
        + json.dumps(metadata, indent=2),

        "AVAILABLE ANALYSIS CAPABILITIES:\n"
        + json.dumps(capabilities, indent=2),

        "ELASTICITY RELIABILITY SUMMARY:\n"
        + json.dumps(elasticity_summary, indent=2),

        "ITEM SUMMARY (deterministic calculations):\n"
        + json.dumps(summary_records, indent=2),
    ]
    if moves_records:
        sections.append(
            "PRICE RECOMMENDATIONS (deterministic simulation results):\n"
            + json.dumps(moves_records, indent=2)
        )
    else:
        sections.append(
            "PRICE RECOMMENDATIONS: unavailable. Do not make profit-impact claims. "
            "Use revenue, volume, price variation, and reliability fields only."
        )

    return "\n\n".join(sections) + "\n\nWrite the decision memo now."


def generate_menu_memo(
    summary_df: pd.DataFrame,
    moves_df: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
    capabilities: dict[str, bool] | None = None,
    model: str = "claude-sonnet-4-6",
) -> str:
    """Ask Claude to explain deterministic outputs; Claude never performs the calculations."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Set a valid key before generating the AI memo."
        )

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": build_user_prompt(summary_df, moves_df, metadata, capabilities),
        }],
    )
    memo = "".join(
        block.text
        for block in response.content
        if block.type == "text"
    )

    return clean_memo_markdown(memo)


if __name__ == "__main__":
    from analysis import build_item_summary, load_sales, recommend_price_moves
    from validation import determine_capabilities, validate_sales_df

    raw = load_sales("data/cafe_sales.csv")
    validated, errors, _warnings = validate_sales_df(raw)
    if errors or validated is None:
        raise RuntimeError(errors)
    summary = build_item_summary(validated)
    moves = recommend_price_moves(summary)
    print(generate_menu_memo(
        summary,
        moves,
        metadata={"business_name": "Synthetic Cafe", "dataset_name": "Full Demo Dataset", "currency": "USD"},
        capabilities=determine_capabilities(validated),
    ))
