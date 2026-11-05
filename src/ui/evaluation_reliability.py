"""Show paired forecast evidence without altering existing model calculations."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.evaluation_reliability import audit_paired_models


def render_paired_model_reliability(item_results: pd.DataFrame) -> None:
    """Present holdout comparison diagnostics and clear interpretation limits."""
    audit = audit_paired_models(item_results)
    st.subheader("Paired Forecast Reliability Review")
    st.caption(
        "Only items with valid errors from *both* models are compared. "
        "Baseline-only and insufficient-evidence items are excluded from "
        "this paired comparison, not from baseline coverage."
    )
    if audit.compared == 0:
        st.info(audit.message)
        return
    first, second, third = st.columns(3)
    first.metric("Comparable items", f"{audit.compared:,}")
    second.metric("Baseline wins (MAE)", f"{audit.baseline_wins:,}")
    third.metric("Elasticity wins (MAE)", f"{audit.elasticity_wins:,}")
    st.caption(f"Ties: {audit.ties:,}. An item-level win is not a forecast-accuracy guarantee.")
    st.write(
        f"**Paired mean MAE (units/day):** historical average "
        f"{audit.mean_baseline_mae:.2f}; elasticity {audit.mean_elasticity_mae:.2f}. "
        f"**Paired median MAE:** {audit.median_baseline_mae:.2f} vs "
        f"{audit.median_elasticity_mae:.2f}."
    )
    if audit.extrapolated:
        st.warning(
            f"{audit.extrapolated:,} compared items used test prices "
            "outside their training price range. Interpret these "
            "comparisons cautiously."
        )
    if audit.high_error_ratio:
        st.warning(
            f"{audit.high_error_ratio:,} compared items have elasticity MAE "
            "over 10× baseline MAE. This is a review flag, not an "
            "automatic prediction adjustment."
        )
    st.info(audit.message)
