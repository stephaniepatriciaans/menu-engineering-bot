"""Deterministic menu-engineering analytics over the canonical dataframe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from config import (
    CATEGORY_ELASTICITY_PRIORS,
    DEFAULT_ELASTICITY_PRIOR,
    DEFAULT_PRICE_CHANGES,
    ELASTICITY_CLIP,
    MIN_ELASTICITY_OBSERVATIONS,
    MIN_ELASTICITY_PRICE_POINTS,
    MIN_RELATIVE_PRICE_RANGE,
    category_prior,
)


def load_sales(path: str) -> pd.DataFrame:
    """Load an already-canonical CSV, used by the bundled synthetic demo."""
    return pd.read_csv(path, parse_dates=["date"])


def _fallback_elasticity(category: object, priors: Mapping[str, float] | None) -> dict[str, object]:
    prior, source = category_prior(category, priors or CATEGORY_ELASTICITY_PRIORS)
    return {
        "elasticity": prior,
        "elasticity_source": source,
        "elasticity_confidence": "Prior",
    }


def estimate_elasticity(
    item_df: pd.DataFrame,
    category: str,
    category_priors: Mapping[str, float] | None = None,
    default_prior: float = DEFAULT_ELASTICITY_PRIOR,
) -> dict[str, object]:
    """Estimate item elasticity when evidence is sufficient; otherwise use a labeled prior.

    Historical estimates use OLS on daily log(quantity) vs log(price). Reliability
    metadata is always returned so a weak estimate is never presented as equivalent
    to a well-supported one.
    """
    work = item_df[["date", "price", "units_sold"]].copy()
    work["price"] = pd.to_numeric(work["price"], errors="coerce")
    work["units_sold"] = pd.to_numeric(work["units_sold"], errors="coerce")
    work = work.dropna(subset=["date", "price", "units_sold"])
    work = work[(work["price"] > 0) & (work["units_sold"] > 0)]

    # Aggregate transaction-level exports to daily item demand at each observed price.
    daily = work.groupby(["date", "price"], as_index=False)["units_sold"].sum()
    observations = int(len(daily))
    price_points = int(daily["price"].nunique())
    if daily.empty:
        fallback = _fallback_elasticity(category, category_priors)
        if fallback["elasticity_source"] == "default_prior":
            fallback["elasticity"] = float(default_prior)
        return {**fallback, "price_points": 0, "observations": 0, "price_variation_pct": 0.0}

    min_price = float(daily["price"].min())
    max_price = float(daily["price"].max())
    rel_range = (max_price - min_price) / min_price if min_price > 0 else 0.0

    sufficient = (
        price_points >= MIN_ELASTICITY_PRICE_POINTS
        and observations >= MIN_ELASTICITY_OBSERVATIONS
        and rel_range >= MIN_RELATIVE_PRICE_RANGE
    )
    if not sufficient:
        fallback = _fallback_elasticity(category, category_priors)
        if fallback["elasticity_source"] == "default_prior":
            fallback["elasticity"] = float(default_prior)
        return {
            **fallback,
            "price_points": price_points,
            "observations": observations,
            "price_variation_pct": round(rel_range * 100, 1),
        }

    try:
        log_p = np.log(daily["price"].to_numpy(dtype=float))
        log_q = np.log(daily["units_sold"].to_numpy(dtype=float))
        slope, _intercept = np.polyfit(log_p, log_q, 1)
        raw_slope = float(slope)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        fallback = _fallback_elasticity(category, category_priors)
        if fallback["elasticity_source"] == "default_prior":
            fallback["elasticity"] = float(default_prior)
        return {
            **fallback,
            "price_points": price_points,
            "observations": observations,
            "price_variation_pct": round(rel_range * 100, 1),
        }

    clipped = float(np.clip(raw_slope, ELASTICITY_CLIP[0], ELASTICITY_CLIP[1]))
    was_clipped = not np.isclose(raw_slope, clipped)
    if was_clipped:
        confidence = "Low"
    elif observations >= 30 and price_points >= 4 and rel_range >= 0.10:
        confidence = "High"
    elif observations >= 15 and price_points >= 3 and rel_range >= 0.05:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "elasticity": clipped,
        "elasticity_source": "estimated",
        "elasticity_confidence": confidence,
        "price_points": price_points,
        "observations": observations,
        "price_variation_pct": round(rel_range * 100, 1),
    }


def build_item_summary(
    df: pd.DataFrame,
    category_priors: Mapping[str, float] | None = None,
    default_prior: float = DEFAULT_ELASTICITY_PRIOR,
) -> pd.DataFrame:
    """Build one deterministic summary row per menu item.

    Revenue/popularity outputs are always computed. Margin/profit/quadrants are
    populated only when complete cost data is available for the dataset.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    n_days = max(1, int(df["date"].nunique()))
    full_cost_available = "unit_cost" in df.columns and bool(df["unit_cost"].notna().all())

    for item, item_df in df.groupby("item", sort=False):
        item_df = item_df.sort_values("date")
        category = str(item_df["category"].iloc[-1]) if "category" in item_df else "Uncategorized"
        current_price = float(item_df["price"].iloc[-1])
        total_units = float(item_df["units_sold"].sum())
        avg_daily_units = total_units / n_days
        revenue = float((item_df["price"] * item_df["units_sold"]).sum())
        elasticity_info = estimate_elasticity(item_df, category, category_priors, default_prior)

        record: dict[str, object] = {
            "item": item,
            "category": category,
            "price": round(current_price, 2),
            "avg_daily_units": round(avg_daily_units, 1),
            "total_units_sold": round(total_units, 2),
            "total_revenue": round(revenue, 2),
            "unit_cost": np.nan,
            "contribution_margin_amount": np.nan,
            "contribution_margin_%": np.nan,
            "total_profit": np.nan,
            "quadrant": None,
            "elasticity": round(float(elasticity_info["elasticity"]), 2),
            "elasticity_source": elasticity_info["elasticity_source"],
            "elasticity_confidence": elasticity_info["elasticity_confidence"],
            "price_points": int(elasticity_info["price_points"]),
            "observations": int(elasticity_info["observations"]),
            "price_variation_%": float(elasticity_info["price_variation_pct"]),
        }

        if full_cost_available:
            current_cost = float(item_df["unit_cost"].iloc[-1])
            total_cost = float((item_df["unit_cost"] * item_df["units_sold"]).sum())
            margin_dollars = current_price - current_cost
            margin_pct = margin_dollars / current_price if current_price > 0 else np.nan
            record.update({
                "unit_cost": round(current_cost, 2),
                "contribution_margin_amount": round(margin_dollars, 2),
                "contribution_margin_%": round(float(margin_pct) * 100, 1),
                "total_profit": round(revenue - total_cost, 2),
            })
        records.append(record)

    summary = pd.DataFrame(records)

    if full_cost_available and not summary.empty:
        margin_median = float(summary["contribution_margin_%"].median())
        popularity_median = float(summary["avg_daily_units"].median())

        def classify(row: pd.Series) -> str:
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

    return summary.sort_values("total_revenue", ascending=False).reset_index(drop=True)


def simulate_price_change(row: pd.Series, pct_change: float) -> dict[str, object]:
    """Estimate a price scenario using precomputed elasticity; requires unit cost."""
    if pd.isna(row.get("unit_cost")):
        raise ValueError("Price/profit simulation requires unit cost data.")
    if pct_change <= -1.0:
        raise ValueError("Price changes must keep the selling price above zero.")

    new_price = float(row["price"]) * (1 + float(pct_change))
    if new_price <= 0:
        raise ValueError("Simulated price must be positive.")

    pct_qty_change = float(row["elasticity"]) * float(pct_change)
    new_daily_units = max(0.0, float(row["avg_daily_units"]) * (1 + pct_qty_change))
    old_daily_profit = float(row["avg_daily_units"]) * (float(row["price"]) - float(row["unit_cost"]))
    new_daily_profit = new_daily_units * (new_price - float(row["unit_cost"]))

    return {
        "item": row["item"],
        "old_price": round(float(row["price"]), 2),
        "new_price": round(new_price, 2),
        "old_daily_units_est": round(float(row["avg_daily_units"]), 1),
        "new_daily_units_est": round(new_daily_units, 1),
        "old_daily_profit_est": round(old_daily_profit, 2),
        "new_daily_profit_est": round(new_daily_profit, 2),
        "daily_profit_delta": round(new_daily_profit - old_daily_profit, 2),
    }


def recommend_price_moves(
    summary: pd.DataFrame,
    price_changes: Sequence[float] | None = None,
) -> pd.DataFrame:
    """Choose the best deterministic profit scenario from configured candidate changes."""
    if summary is None or summary.empty:
        return pd.DataFrame()
    if "unit_cost" not in summary.columns or summary["unit_cost"].isna().any():
        return pd.DataFrame()

    candidates = [float(x) for x in (price_changes or DEFAULT_PRICE_CHANGES) if float(x) > -1.0]
    if 0.0 not in candidates:
        candidates.append(0.0)
    candidates = sorted(set(candidates))

    best_moves: list[dict[str, object]] = []
    for _, row in summary.iterrows():
        sims = [simulate_price_change(row, pct) for pct in candidates]
        best = max(sims, key=lambda s: float(s["daily_profit_delta"]))
        old_price = float(best["old_price"])
        best["pct_change_recommended"] = round((float(best["new_price"]) - old_price) / old_price * 100, 1)
        best["quadrant"] = row.get("quadrant")
        best["elasticity"] = row["elasticity"]
        best["elasticity_source"] = row["elasticity_source"]
        best["elasticity_confidence"] = row["elasticity_confidence"]
        best_moves.append(best)

    return pd.DataFrame(best_moves).sort_values("daily_profit_delta", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    frame = load_sales("data/cafe_sales.csv")
    summary_frame = build_item_summary(frame)
    print(summary_frame.to_string(index=False))
    print("\n--- Recommended price moves (numeric, pre-LLM) ---\n")
    print(recommend_price_moves(summary_frame).to_string(index=False))
