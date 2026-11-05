"""Honest, paired holdout comparisons for forecast models.

This module never changes the underlying forecasts, eligibility, or pricing.
Mean MAE is calculated only over the same evaluated items for both models.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PairedModelAudit:
    compared: int
    baseline_wins: int
    elasticity_wins: int
    ties: int
    extrapolated: int
    mean_baseline_mae: float | None
    mean_elasticity_mae: float | None
    median_baseline_mae: float | None
    median_elasticity_mae: float | None
    high_error_ratio: int
    message: str


def audit_paired_models(items: pd.DataFrame) -> PairedModelAudit:
    """Compare only valid two-model holdouts; never infer causality or accuracy.

    A large elasticity/baseline MAE ratio is a *review signal*, not a
    statistically calibrated failure or an automatic model selector.
    """
    required = {"status", "baseline_mae", "elasticity_mae"}
    missing = required.difference(items.columns)
    if missing:
        raise ValueError("Missing evaluation columns: " + ", ".join(sorted(missing)))

    eligible = items.loc[items["status"].eq("evaluated")].copy()
    baseline = pd.to_numeric(eligible["baseline_mae"], errors="coerce")
    elasticity = pd.to_numeric(eligible["elasticity_mae"], errors="coerce")
    baseline_values = baseline.to_numpy(dtype=float, na_value=np.nan)
    elasticity_values = elasticity.to_numpy(dtype=float, na_value=np.nan)
    valid = (
        np.isfinite(baseline_values)
        & np.isfinite(elasticity_values)
        & (baseline_values >= 0)
        & (elasticity_values >= 0)
    )
    eligible = eligible.loc[valid]
    baseline = baseline.loc[valid]
    elasticity = elasticity.loc[valid]
    compared = len(eligible)

    if compared == 0:
        return PairedModelAudit(
            0, 0, 0, 0, 0, None, None, None, None, 0,
            "No valid paired holdouts are available. Keep baseline-only results "
            "separate; do not infer elasticity forecast accuracy.",
        )

    baseline_wins = int((baseline < elasticity).sum())
    elasticity_wins = int((elasticity < baseline).sum())
    ties = compared - baseline_wins - elasticity_wins
    if "price_extrapolation" in eligible.columns:
        extrapolated = int(eligible["price_extrapolation"].fillna(False).eq(True).sum())
    else:
        extrapolated = 0

    # Zero-error baselines with nonzero elasticity error count as large ratios.
    ratio = elasticity.to_numpy() / np.maximum(baseline.to_numpy(), 1e-12)
    high_error_ratio = int((ratio > 10.0).sum())
    mean_base = float(baseline.mean())
    mean_elast = float(elasticity.mean())
    if mean_elast < mean_base:
        verdict = "Elasticity has lower mean paired MAE"
    elif mean_elast > mean_base:
        verdict = "Historical average has lower mean paired MAE"
    else:
        verdict = "Both models have equal mean paired MAE"
    message = (
        f"{verdict} across {compared:,} comparable items. "
        "This is descriptive backtesting, not a validated pricing effect. "
        "Check extrapolation and outliers before making model decisions."
    )
    return PairedModelAudit(
        compared, baseline_wins, elasticity_wins, ties, extrapolated,
        mean_base, mean_elast, float(baseline.median()),
        float(elasticity.median()), high_error_ratio, message,
    )
