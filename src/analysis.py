"""Deterministic menu-engineering analytics over the canonical dataframe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, ROUND_HALF_UP

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



def simulate_price_change(
    row: pd.Series,
    pct_change: float,
) -> dict[str, object]:
    """
    Simulate a candidate price change using the actual
    rounded selling price.

    The displayed price, percentage change, demand estimate,
    and profit calculations are kept consistent.

    Requires available unit cost data.
    """

    if pd.isna(row.get("unit_cost")):
        raise ValueError(
            "Price/profit simulation requires unit cost data."
        )

    if not -1.0 < pct_change:
        raise ValueError(
            "Price changes must keep the selling price above zero."
        )

    # Convert financial inputs to decimal values.
    old_price_dec = Decimal(str(row["price"]))

    cost_dec = Decimal(str(row["unit_cost"]))

    requested_change_dec = Decimal(str(pct_change))

    cent = Decimal("0.01")

    # Selling prices must be valid and representable in cents.
    if not old_price_dec.is_finite() or old_price_dec <= 0:
        raise ValueError("Original price must be positive and finite.")

    if not cost_dec.is_finite() or cost_dec < 0:
        raise ValueError("Unit cost must be nonnegative and finite.")

    old_price_dec = old_price_dec.quantize(
        cent,
        rounding=ROUND_HALF_UP,
    )

    new_price_dec = (
        old_price_dec * (Decimal("1") + requested_change_dec)
    ).quantize(
        cent,
        rounding=ROUND_HALF_UP,
    )

    if new_price_dec <= 0:
        raise ValueError(
            "Simulated rounded price must be positive."
        )

    # Actual percentage change after rounding.
    actual_pct_change = float(
        (new_price_dec - old_price_dec) / old_price_dec
    )

    old_price = float(old_price_dec)
    new_price = float(new_price_dec)
    unit_cost = float(cost_dec)

    old_daily_units = float(row["avg_daily_units"])
    elasticity = float(row["elasticity"])

    # Calculate demand response using the actual change.
    pct_qty_change = elasticity * actual_pct_change

    new_daily_units = max(
        0.0,
        old_daily_units * (1.0 + pct_qty_change),
    )

    # Calculate profits from the rounded selling prices.
    old_daily_profit = (
        old_daily_units * (old_price - unit_cost)
    )

    new_daily_profit = (
        new_daily_units * (new_price - unit_cost)
    )

    daily_profit_delta = (
        new_daily_profit - old_daily_profit
    )

    return {
        "item": row["item"],
        "old_price": old_price,
        "new_price": new_price,
        "pct_change_recommended": round(
            actual_pct_change * 100, 1
        ),
        "old_daily_units_est": round(
            old_daily_units, 1
        ),
        "new_daily_units_est": round(
            new_daily_units, 1
        ),
        "old_daily_profit_est": round(
            old_daily_profit, 2
        ),
        "new_daily_profit_est": round(
            new_daily_profit, 2
        ),
        "daily_profit_delta": round(
            daily_profit_delta, 2
        ),
    }


def assess_pricing_reliability(
    elasticity_source: str,
    elasticity_confidence: str,
) -> tuple[str, str]:
    """
    Classify how pricing simulation results should be interpreted.

    This does not change the numerical calculations.
    All simulated price changes require business validation.
    """
    source = str(elasticity_source).strip().lower()
    confidence = str(elasticity_confidence).strip().lower()

    if source == "estimated":
        if confidence == "high":
            return (
                "Historical estimate — review required",
                "Historical estimate with higher model confidence. "
                "Validate against promotions, seasonality, and "
                "store differences before changing prices.",
            )

        return (
            "Exploratory — low-confidence estimate",
            "Historical elasticity is low or uncertain confidence. "
            "Do not implement the suggested price change "
            "without additional validation.",
        )

    if source == "category_prior":
        return (
            "Exploratory — category assumption",
            "Elasticity is assumed from the product category, "
            "not estimated from this item's price history.",
        )

    if source == "default_prior":
        return (
            "Exploratory — default assumption",
            "Elasticity is a general assumption. "
            "No reliable item-specific elasticity estimate "
            "is available.",
        )

    return (
        "Exploratory — unknown reliability",
        "Elasticity reliability is unknown. "
        "Review the source data before using this result.",
    )



def recommend_price_moves(
    summary: pd.DataFrame,
    price_changes: Sequence[float] | None = None,
) -> pd.DataFrame:
    """
    Select the highest-profit simulated price scenario.

    Uses rounded prices from simulate_price_change() and
    clearly labels uncertainty in elasticity estimates.

    These are scenarios, not automatically approved price changes.
    """

    if summary is None or summary.empty:
        return pd.DataFrame()

    # Complete cost data is required.
    if (
        "unit_cost" not in summary.columns
        or summary["unit_cost"].isna().any()
    ):
        return pd.DataFrame()

    configured_changes = (
        DEFAULT_PRICE_CHANGES
        if price_changes is None
        else price_changes
    )

    candidates = [
        float(x)
        for x in configured_changes
        if float(x) > -1.0
    ]

    # Always include no price change.
    if 0.0 not in candidates:
        candidates.append(0.0)

    candidates = sorted(set(candidates))

    best_moves: list[dict[str, object]] = []

    for _, row in summary.iterrows():

        # Preserve your existing rounded-price simulation.
        sims = [
            simulate_price_change(row, pct)
            for pct in candidates
        ]

        if not sims:
            continue

        best = max(
            sims,
            key=lambda s: float(s["daily_profit_delta"])
        )

        # Retrieve elasticity information.
        source = str(
            row.get("elasticity_source", "unknown")
        )

        confidence = str(
            row.get("elasticity_confidence", "unknown")
        )

        # Determine how cautiously to interpret the result.
        reliability, reliability_reason = (
            assess_pricing_reliability(
                source,
                confidence,
            )
        )

        # Preserve original analysis information.
        best["quadrant"] = row.get("quadrant")
        best["elasticity"] = row["elasticity"]
        best["elasticity_source"] = source
        best["elasticity_confidence"] = confidence

        # New reliability fields.
        best["pricing_reliability"] = reliability
        best["reliability_reason"] = reliability_reason

        # All simulations require review.
        best["requires_review"] = True

        best_moves.append(best)

    if not best_moves:
        return pd.DataFrame()

    return (
        pd.DataFrame(best_moves)
        .sort_values(
            "daily_profit_delta",
            ascending=False,
        )
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    frame = load_sales("data/cafe_sales.csv")
    summary_frame = build_item_summary(frame)
    print(summary_frame.to_string(index=False))
    print("\n--- Recommended price moves (numeric, pre-LLM) ---\n")
    print(recommend_price_moves(summary_frame).to_string(index=False))
