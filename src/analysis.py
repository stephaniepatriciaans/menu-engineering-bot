"""
analysis.py

Core menu engineering analysis:
- Estimates per-item elasticity from historical price/quantity data
  (falls back to a category-level prior if a single price was used the
  whole period, since elasticity can't be estimated from one price point).
- Computes contribution margin and sales velocity per item.
- Classifies each item into a menu-engineering quadrant:
      Star      = high margin, high popularity
      Plowhorse = low margin,  high popularity
      Puzzle    = high margin, low popularity
      Dog       = low margin,  low popularity
- Simulates revenue/profit impact of a candidate price change using the
  estimated (or prior) elasticity.

This module has NO dependency on the LLM step -- it's pure numeric analysis,
which keeps the recommendations grounded in real math rather than letting
the LLM invent numbers.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


# Category-level elasticity priors, used as a fallback when an item's price
# never varied in the historical data (so true elasticity can't be fit).
# Negative values: demand falls as price rises. Magnitude reflects how
# substitutable / discretionary the category typically is.
CATEGORY_ELASTICITY_PRIOR = {
    "Coffee": -0.8,
    "Tea": -1.0,
    "Pastry": -1.3,
    "Food": -1.4,
    "Other": -0.5,
}


def load_sales(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return df


def estimate_elasticity(item_df: pd.DataFrame, category: str) -> tuple[float, str]:
    """
    Try to estimate price elasticity of demand from observed (price, units)
    variation. Returns (elasticity, source) where source is 'estimated' or
    'category_prior'.

    Elasticity here is computed as the OLS slope of log(units) on log(price)
    across whatever price variation exists in the data.
    """
    prices = item_df["price"].values
    if np.unique(prices).size < 2:
        # No price variation observed -> can't estimate, fall back to prior
        return CATEGORY_ELASTICITY_PRIOR.get(category, -1.0), "category_prior"

    daily = item_df.groupby("price")["units_sold"].mean().reset_index()
    log_p = np.log(daily["price"])
    log_q = np.log(daily["units_sold"].clip(lower=0.5))

    # simple OLS slope
    slope, _intercept = np.polyfit(log_p, log_q, 1)
    # sanity clip: elasticity rarely exceeds these bounds for typical retail goods
    slope = float(np.clip(slope, -3.0, 0.5))
    return slope, "estimated"


def build_item_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per item: revenue, cost, margin, velocity, elasticity, quadrant."""
    records = []
    n_days = df["date"].nunique()

    for item, item_df in df.groupby("item"):
        category = item_df["category"].iloc[0]
        price = item_df["price"].iloc[-1]  # most recent price
        unit_cost = item_df["unit_cost"].iloc[-1]
        total_units = item_df["units_sold"].sum()
        avg_daily_units = total_units / n_days
        revenue = (item_df["price"] * item_df["units_sold"]).sum()
        cost = (item_df["unit_cost"] * item_df["units_sold"]).sum()
        contribution_margin_pct = (price - unit_cost) / price if price > 0 else 0
        elasticity, elasticity_source = estimate_elasticity(item_df, category)

        records.append({
            "item": item,
            "category": category,
            "price": round(price, 2),
            "unit_cost": round(unit_cost, 2),
            "contribution_margin_$": round(price - unit_cost, 2),
            "contribution_margin_%": round(contribution_margin_pct * 100, 1),
            "avg_daily_units": round(avg_daily_units, 1),
            "total_units_sold": int(total_units),
            "total_revenue": round(revenue, 2),
            "total_profit": round(revenue - cost, 2),
            "elasticity": round(elasticity, 2),
            "elasticity_source": elasticity_source,
        })

    summary = pd.DataFrame(records)

    # Quadrant classification: split on median margin% and median popularity
    margin_median = summary["contribution_margin_%"].median()
    popularity_median = summary["avg_daily_units"].median()

    def classify(row):
        high_margin = row["contribution_margin_%"] >= margin_median
        high_pop = row["avg_daily_units"] >= popularity_median
        if high_margin and high_pop:
            return "Star"
        if not high_margin and high_pop:
            return "Plowhorse"
        if high_margin and not high_pop:
            return "Puzzle"
        return "Dog"

    summary["quadrant"] = summary.apply(classify, axis=1)
    return summary.sort_values("total_profit", ascending=False).reset_index(drop=True)


def simulate_price_change(row: pd.Series, pct_change: float) -> dict:
    """
    Estimate the effect of changing an item's price by pct_change (e.g. 0.10
    for +10%) using its elasticity, holding unit cost fixed.

    %change in quantity ≈ elasticity * %change in price  (log-linear approx)
    """
    new_price = row["price"] * (1 + pct_change)
    pct_qty_change = row["elasticity"] * pct_change
    new_daily_units = max(0, row["avg_daily_units"] * (1 + pct_qty_change))

    old_daily_profit = row["avg_daily_units"] * (row["price"] - row["unit_cost"])
    new_daily_profit = new_daily_units * (new_price - row["unit_cost"])

    return {
        "item": row["item"],
        "old_price": round(row["price"], 2),
        "new_price": round(new_price, 2),
        "old_daily_units_est": round(row["avg_daily_units"], 1),
        "new_daily_units_est": round(new_daily_units, 1),
        "old_daily_profit_est": round(old_daily_profit, 2),
        "new_daily_profit_est": round(new_daily_profit, 2),
        "daily_profit_delta": round(new_daily_profit - old_daily_profit, 2),
    }


def recommend_price_moves(summary: pd.DataFrame) -> pd.DataFrame:
    """
    For each item, test a small set of candidate price changes and pick the
    one with the best estimated daily profit delta. This is the numeric
    backbone the LLM will narrate -- it does NOT invent these numbers.
    """
    candidates = [-0.10, -0.05, 0.0, 0.05, 0.10, 0.15]
    best_moves = []

    for _, row in summary.iterrows():
        sims = [simulate_price_change(row, pct) for pct in candidates]
        best = max(sims, key=lambda s: s["daily_profit_delta"])
        best["pct_change_recommended"] = round(
            (best["new_price"] - best["old_price"]) / best["old_price"] * 100, 1
        )
        best["quadrant"] = row["quadrant"]
        best["elasticity"] = row["elasticity"]
        best_moves.append(best)

    return pd.DataFrame(best_moves).sort_values("daily_profit_delta", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    df = load_sales("data/cafe_sales.csv")
    summary = build_item_summary(df)
    print(summary.to_string(index=False))
    print("\n--- Recommended price moves (numeric, pre-LLM) ---\n")
    moves = recommend_price_moves(summary)
    print(moves.to_string(index=False))
