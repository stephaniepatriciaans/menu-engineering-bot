"""
agent.py

Takes the NUMERIC outputs from analysis.py (item summary + recommended price
moves) and asks Claude to write a plain-English "menu memo": a short,
prioritized set of recommendations a cafe owner could actually act on.

Design principle: the LLM never invents numbers. Every figure in the prompt
comes from analysis.py's deterministic calculations. The LLM's job is purely
to explain, prioritize, and write in plain language -- the same separation
of "model does the math, LLM explains the math" used in the IDX Exchange
decision-brief and GAF dashboard work this project is modeled on.

Requires: ANTHROPIC_API_KEY environment variable.
"""

import os
import json
import pandas as pd
from anthropic import Anthropic


SYSTEM_PROMPT = """You are a menu engineering consultant writing a short, \
practical memo for an independent cafe owner. You will be given:
1. A summary table of each menu item's margin, popularity, and quadrant \
classification (Star / Plowhorse / Puzzle / Dog).
2. A table of recommended price moves with their estimated daily profit impact, \
already computed from a price-elasticity model.

Rules:
- Do NOT invent or alter any numbers. Only use the numbers given to you.
- Write for a busy, non-technical cafe owner: short paragraphs, no jargon, \
no model/statistics talk (no "elasticity," "OLS," "quadrant" -- translate \
those into plain language like "popular but low-margin item").
- Prioritize the 3-5 highest-impact recommendations, not all 15 items.
- For each recommendation, state the action, the expected daily profit impact \
in dollars, and a one-sentence plain-English reason.
- Include one short "watch list" of items that may need a menu redesign or \
removal (the Dogs), described gently and constructively.
- End with a 2-sentence summary of total estimated daily profit upside if \
all top recommendations were adopted.
- Keep the whole memo under 400 words.
"""


def build_user_prompt(summary_df: pd.DataFrame, moves_df: pd.DataFrame) -> str:
    summary_records = summary_df[
        ["item", "category", "price", "contribution_margin_%", "avg_daily_units", "quadrant"]
    ].to_dict(orient="records")

    moves_records = moves_df[
        ["item", "old_price", "new_price", "pct_change_recommended", "daily_profit_delta", "quadrant"]
    ].to_dict(orient="records")

    return (
        "MENU ITEM SUMMARY (one row per item):\n"
        f"{json.dumps(summary_records, indent=2)}\n\n"
        "RECOMMENDED PRICE MOVES (numerically optimal price change per item, "
        "with estimated daily profit impact):\n"
        f"{json.dumps(moves_records, indent=2)}\n\n"
        "Write the menu memo now."
    )


def generate_menu_memo(summary_df: pd.DataFrame, moves_df: pd.DataFrame, model: str = "claude-sonnet-4-6") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Get a key at https://console.anthropic.com and set it before running."
        )

    client = Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(summary_df, moves_df)

    response = client.messages.create(
        model=model,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return "".join(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    from analysis import load_sales, build_item_summary, recommend_price_moves

    df = load_sales("data/cafe_sales.csv")
    summary = build_item_summary(df)
    moves = recommend_price_moves(summary)

    memo = generate_menu_memo(summary, moves)
    print(memo)
