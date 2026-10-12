"""Pricing Recommendations dashboard section"""

import pandas as pd
import streamlit as st

from analysis import recommend_price_moves
from ui.table_formatters import display_moves_table


def render_pricing_recommendations(
    summary: pd.DataFrame,
    capabilities: dict,
    currency: str,
    max_decrease: int,
    max_increase: int,
    cost_is_assumption: bool,
) -> pd.DataFrame:
    """Render pricing simulations and return the candidate moves"""

    st.header("Pricing Recommendations")

    price_changes = [
        value / 100
        for value in range(
            -max_decrease,
            max_increase + 1,
            5,
        )
    ]

    if 0.0 not in price_changes:
        price_changes.append(0.0)

    moves = (
        recommend_price_moves(summary, price_changes)
        if capabilities["price_optimization"]
        else pd.DataFrame()
    )

    if moves.empty:
        st.info(
            "Profit-based price recommendations are disabled "
            "because complete unit cost data is unavailable. "
            "The app will not fabricate cost or profit figures."
        )

    else:
        st.caption(
            f"Candidate moves are tested from -{max_decrease}% "
            f"to +{max_increase}% in 5% steps. "
            "Demand response uses historical estimates when "
            "reliable enough, otherwise a clearly labeled prior."
        )

        if cost_is_assumption:
            st.warning(
                "These price/profit recommendations are scenario "
                "results based on your estimated cost percentage."
            )

        move_columns = [
            "item",
            "old_price",
            "new_price",
            "pct_change_recommended",
            "daily_profit_delta",
            "quadrant",
            "elasticity_source",
            "elasticity_confidence",
            "pricing_reliability",
            "reliability_reason",
        ]

        st.warning(
            "Pricing results are exploratory simulations, "
            "not validated pricing decisions. "
            "Low-confidence historical estimates and assumed "
            "elasticities require additional review."
        )

        # Main pricing recommendations table
        display_columns = [
            col for col in move_columns
            if col != "reliability_reason"
        ]

        st.dataframe(
            display_moves_table(
                moves[display_columns],
                currency,
            ),
            width="stretch",
            hide_index=True,
            column_config={
                "pricing_reliability": st.column_config.TextColumn(
                    "Pricing Reliability",
                    width="large",
                ),
            },
        )

    # Detailed explanations shown separately
    # Preserve the original expander even when moves is empty
    with st.expander("View pricing reliability explanations"):
        for _, row in moves.iterrows():
            st.markdown(f"**{row['item']}**")
            st.write(row["reliability_reason"])
            st.divider()

    # Required by the downstream AI decision memo
    return moves
