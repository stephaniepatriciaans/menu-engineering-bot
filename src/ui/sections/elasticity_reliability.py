"""Elasticity Reliability dashboard section."""

import pandas as pd
import streamlit as st

from ui.components import render_chart_header


def render_elasticity_reliability(
    summary: pd.DataFrame,
) -> None:
    """Display elasticity estimates and their reliability information."""

    with st.container(border=True):

        render_chart_header(
            "Elasticity Reliability",
            "Review how each item's demand elasticity was determined "
            "and assess the reliability of those estimates.",
        )

        st.info(
            "'estimated' means the item had enough historical "
            "price/quantity variation for an item-level log-log estimate. "
            "'category_prior' and 'default_prior' are labeled assumptions, "
            "not measured demand curves."
        )

        # Inner table card
        with st.container(border=True):

            st.dataframe(
                summary[
                    [
                        "item",
                        "category",
                        "elasticity",
                        "elasticity_source",
                        "elasticity_confidence",
                        "price_points",
                        "observations",
                        "price_variation_%",
                        *(["reliability_review_reason", "possible_operational_charge"]
                          if "reliability_review_reason" in summary.columns else []),  # part6-review-table
                    ]
                ],
                width="stretch",
                hide_index=True,
            )
