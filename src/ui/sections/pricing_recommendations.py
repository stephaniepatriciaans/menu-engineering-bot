"""Pricing Recommendations dashboard section."""

import altair as alt
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
    """Render pricing simulations and return the original moves."""

    st.header("Pricing Recommendations")
    selected_item: str | None = None

    # --------------------------------------------------
    # 1. Simulation controls
    # --------------------------------------------------
    st.markdown("### Simulation Settings")

    control_col1, control_col2 = st.columns(2)

    with control_col1:
        selection_label = st.selectbox(
            "Optimization strategy",
            options=["Base case", "Conservative"],
            index=0,
            help=(
                "Base case maximizes simulated contribution "
                "profit under the central elasticity estimate. "
                "Conservative maximizes the worst-case "
                "simulated result among tested candidates."
            ),
        )

    with control_col2:
        uncertainty_pct = st.slider(
            "Elasticity uncertainty (%)",
            min_value=0,
            max_value=100,
            value=25,
            step=5,
            help=(
                "Adjusts sensitivity to elasticity assumptions. "
                "This is not a statistical confidence interval."
            ),
        )

    selection_mode = (
        "conservative"
        if selection_label == "Conservative"
        else "base_case"
    )

    elasticity_uncertainty = uncertainty_pct / 100.0

    # --------------------------------------------------
    # 2. Candidate price changes
    # --------------------------------------------------
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
        recommend_price_moves(
            summary,
            price_changes,
            elasticity_uncertainty=elasticity_uncertainty,
            selection_mode=selection_mode,
        )
        if capabilities["price_optimization"]
        else pd.DataFrame()
    )

    # --------------------------------------------------
    # 3. Pricing results
    # --------------------------------------------------
    if moves.empty:
        st.info(
            "Profit-based price recommendations are disabled "
            "because complete unit cost data is unavailable. "
            "The app will not fabricate cost or profit figures."
        )

    else:
        st.caption(
            "All simulated outcomes depend on elasticity "
            "assumptions and should be reviewed before making "
            "business pricing decisions."
        )

        st.caption(
            f"Candidate moves are tested from -{max_decrease}% "
            f"to +{max_increase}% in 5% steps."
        )

        if cost_is_assumption:
            st.warning(
                "These price/profit recommendations are scenario "
                "results based on your estimated cost percentage."
            )

        st.warning(
            "Pricing results are exploratory simulations, "
            "not validated pricing decisions. "
            "Low-confidence estimates and assumed "
            "elasticities require additional review."
        )

        # --------------------------------------------------
        # 4. Main recommendations table
        # --------------------------------------------------

        # --------------------------------------------------
        # Pricing risk overview
        # --------------------------------------------------
        st.markdown("### Pricing Risk Overview")

        items_assessed = len(moves)

        if "worst_case_loss" in moves.columns:
            loss_flags = moves["worst_case_loss"].eq(True)
            negative_worst_case = int(loss_flags.sum())
            non_negative_worst_case = int(
                moves["worst_case_loss"].eq(False).sum()
            )
            unclassified = (
                items_assessed
                - negative_worst_case
                - non_negative_worst_case
            )
        else:
            negative_worst_case = 0
            non_negative_worst_case = 0
            unclassified = items_assessed


        risk_col1, risk_col2, risk_col3 = st.columns(3)

        with risk_col1, st.container(key="pricing_risk_assessed"):
            st.metric(
                "Menu Items Assessed",
                f"{items_assessed:,}",
            )
            st.caption("Pricing scenarios analyzed")

        with risk_col2, st.container(key="pricing_risk_negative"):
            st.metric(
                "Negative Worst-Case",
                (
                    f"{negative_worst_case:,}"
                    if unclassified == 0
                    else "Incomplete"
                ),
            )
            st.caption("Potential downside in simulation")

        with risk_col3, st.container(key="pricing_risk_nonnegative"):
            st.metric(
                "No Simulated Downside Loss",
                (
                    f"{non_negative_worst_case:,}"
                    if unclassified == 0
                    else "Incomplete"
                ),
            )
            st.caption("Nonnegative in tested scenarios")


        st.caption(
            "Counts describe the tested scenarios, not "
            "probabilities or guarantees. A nonnegative "
            "worst-case estimate does not establish that "
            "a price change is safe."
        )

        st.markdown("### Recommended Price Moves")

        recommendation_columns = [
            "item",
            "old_price",
            "new_price",
            "pct_change_recommended",
            "daily_profit_delta",
            "pricing_reliability",
        ]

        recommendation_columns = [
            col
            for col in recommendation_columns
            if col in moves.columns
        ]

        recommendation_table = display_moves_table(
            moves[recommendation_columns],
            currency,
        )

        recommendation_table = recommendation_table.rename(
            columns={
                "item": "Menu Item",
                "old_price": "Current Price",
                "new_price": "Recommended Price",
                "pct_change_recommended": "Price Change",
                "daily_profit_delta": (
                    "Estimated Daily Contribution Impact"
                ),
                "pricing_reliability": "Pricing Reliability",
            }
        )

        st.dataframe(
            recommendation_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Pricing Reliability": st.column_config.TextColumn(
                    "Pricing Reliability",
                    width="large",
                ),
            },
        )

        # --------------------------------------------------
        # 5. Interactive scenario chart
        # --------------------------------------------------
        scenario_value_columns = [
            "worst_case_daily_profit_delta",
            "base_case_daily_profit_delta",
            "best_case_daily_profit_delta",
        ]

        has_scenario_data = (
            "item" in moves.columns
            and all(
                col in moves.columns
                for col in scenario_value_columns
            )
        )

        if has_scenario_data:
            available_items = (
                moves["item"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if available_items:
                st.subheader("Scenario Comparison")

                st.caption(
                    "Select an item to compare simulated "
                    "daily contribution-profit changes. "
                    "Negative values indicate a possible "
                    "decline under that scenario."
                )

                selected_item = st.selectbox(
                    "Menu item to compare",
                    options=available_items,
                    key="pricing_scenario_item",
                )

                selected_rows = moves.loc[
                    moves["item"].astype(str) == selected_item
                ]

                if not selected_rows.empty:
                    selected_row = selected_rows.iloc[0]

                    scenario_values = {
                        "Worst case": pd.to_numeric(
                            selected_row[
                                "worst_case_daily_profit_delta"
                            ],
                            errors="coerce",
                        ),
                        "Base case": pd.to_numeric(
                            selected_row[
                                "base_case_daily_profit_delta"
                            ],
                            errors="coerce",
                        ),
                        "Best case": pd.to_numeric(
                            selected_row[
                                "best_case_daily_profit_delta"
                            ],
                            errors="coerce",
                        ),
                    }

                    chart_data = pd.DataFrame({
                        "Scenario": list(scenario_values.keys()),
                        "Daily contribution impact": list(
                            scenario_values.values()
                        ),
                    })

                    chart_data = chart_data.dropna(
                        subset=["Daily contribution impact"]
                    )

                    if not chart_data.empty:
                        # Distinguish positive and negative downside.
                        worst_value = scenario_values["Worst case"]

                        downside_color = (
                            "#FB7185"
                            if worst_value < 0
                            else "#FBBF24"
                        )

                        scenario_colors = alt.Scale(
                            domain=[
                                "Worst case",
                                "Base case",
                                "Best case",
                            ],
                            range=[
                                downside_color,
                                "#60A5FA",
                                "#34D399",
                            ],
                        )

                        chart = (
                            alt.Chart(chart_data)
                            .mark_bar(
                                cornerRadiusEnd=5,
                                size=28,
                            )
                            .encode(
                                x=alt.X(
                                    "Daily contribution impact:Q",
                                    title=(
                                        "Estimated daily contribution "
                                        f"impact ({currency})"
                                    ),
                                    axis=alt.Axis(
                                        format=",.2f",
                                    ),
                                ),
                                y=alt.Y(
                                    "Scenario:N",
                                    sort=[
                                        "Worst case",
                                        "Base case",
                                        "Best case",
                                    ],
                                    title=None,
                                ),
                                color=alt.Color(
                                    "Scenario:N",
                                    scale=scenario_colors,
                                    legend=None,
                                ),
                                tooltip=[
                                    alt.Tooltip(
                                        "Scenario:N",
                                        title="Scenario",
                                    ),
                                    alt.Tooltip(
                                        "Daily contribution impact:Q",
                                        title=(
                                            "Daily contribution impact "
                                            f"({currency})"
                                        ),
                                        format="+,.2f",
                                    ),
                                ],
                            )
                            .properties(height=185)
                        )

                        zero_line = (
                            alt.Chart(pd.DataFrame({"zero": [0]}))
                            .mark_rule(
                                color="#94A3B8",
                                strokeWidth=1,
                            )
                            .encode(x="zero:Q")
                        )

                        st.altair_chart(
                            chart + zero_line,
                            width="stretch",
                        )

                        st.caption(
                            "Values are simulated daily "
                            "contribution-profit changes "
                            f"in {currency}, not guaranteed "
                            "financial outcomes."
                        )

        # --------------------------------------------------
        # 6. Detailed scenario table
        # --------------------------------------------------
        with st.expander("View detailed scenario analysis"):
            scenario_columns = [
                "item",
                "base_case_daily_profit_delta",
                "best_case_daily_profit_delta",
                "worst_case_daily_profit_delta",
                "worst_case_loss",
                "selection_mode",
                "quadrant",
                "elasticity_source",
                "elasticity_confidence",
            ]

            scenario_columns = [
                col
                for col in scenario_columns
                if col in moves.columns
            ]

            scenario_table = display_moves_table(
                moves[scenario_columns],
                currency,
            )

            scenario_table = scenario_table.rename(
                columns={
                    "item": "Menu Item",
                    "base_case_daily_profit_delta": (
                        "Base Case / Day"
                    ),
                    "best_case_daily_profit_delta": (
                        "Best Case / Day"
                    ),
                    "worst_case_daily_profit_delta": (
                        "Worst Case / Day"
                    ),
                    "worst_case_loss": "Worst-Case Loss",
                    "selection_mode": "Strategy",
                    "quadrant": "Quadrant",
                    "elasticity_source": "Elasticity Source",
                    "elasticity_confidence": "Confidence",
                }
            )

            st.dataframe(
                scenario_table,
                width="stretch",
                hide_index=True,
            )

        # --------------------------------------------------
        # 7. Downside risk warning
        # --------------------------------------------------
        if "worst_case_loss" in moves.columns:
            loss_count = int(
                moves["worst_case_loss"]
                .fillna(False)
                .astype(bool)
                .sum()
            )

            if loss_count > 0:
                st.warning(
                    f"{loss_count} recommended price move(s) "
                    "have a negative pessimistic daily "
                    "contribution-profit scenario."
                )


    # --------------------------------------------------
    # 8. Reliability explanation for selected item
    # --------------------------------------------------
    with st.expander("View pricing reliability explanations"):
        if moves.empty:
            st.write("No pricing recommendations are available.")

        else:
            # Use the same item selected in Scenario Comparison.
            if selected_item is not None:
                selected_rows = moves.loc[
                    moves["item"].astype(str) == selected_item
                ]
            else:
                selected_rows = moves.iloc[:1]

            if not selected_rows.empty:
                selected_row = selected_rows.iloc[0]

                item_name = str(selected_row["item"])

                reliability = str(
                    selected_row.get(
                        "pricing_reliability",
                        "Not classified",
                    )
                )

                reason = str(
                    selected_row.get(
                        "reliability_reason",
                        "No reliability explanation available.",
                    )
                )

                st.markdown(f"**{item_name}**")
                st.caption(f"Pricing reliability: {reliability}")
                st.write(reason)

                st.caption(
                    "Reliability describes the evidence behind "
                    "the simulation, not a guarantee of "
                    "future demand or profit."
                )

    # Return the untouched engine results to the AI memo.
    return moves
