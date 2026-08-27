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
- Distinguish historical elasticity estimates from category/default priors. Mention low-confidence or prior-based demand response when it materially affects a recommendation.
- Translate technical fields into plain business language. Avoid statistics jargon unless needed to explain uncertainty.
- Keep recommendations practical and prioritized; do not mechanically list every item.
- Respect the supplied currency and business/dataset metadata.
- Keep the memo under 450 words.
- Do not use footnotes. Put important caveats inline.
"""


def _safe_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    present = [column for column in columns if column in df.columns]
    if not present:
        return []
    clean = df[present].copy()
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


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

    sections = [
        "BUSINESS / DATASET METADATA:\n" + json.dumps(metadata, indent=2),
        "AVAILABLE ANALYSIS CAPABILITIES:\n" + json.dumps(capabilities, indent=2),
        "ITEM SUMMARY (deterministic calculations):\n" + json.dumps(summary_records, indent=2),
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
    return "".join(block.text for block in response.content if block.type == "text")


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
