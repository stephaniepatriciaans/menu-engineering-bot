"""Menu Engineering Quadrants dashboard section"""

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.charts import style_chart
from ui.components import render_chart_header


def render_menu_quadrants(
    summary: pd.DataFrame,
    capabilities: dict,
    cost_is_assumption: bool,
) -> None:
    """Render menu engineering quadrants and cost warnings"""

    with st.container(border=True):

        render_chart_header(
            "Menu Engineering Quadrants",
            "Evaluate menu performance using popularity "
            "and contribution margin.",
        )

        if capabilities["menu_engineering_quadrants"]:

            quadrant_chart = px.scatter(
                summary,
                x="avg_daily_units",
                y="contribution_margin_%",
                color="quadrant",
                size="total_profit",
                hover_name="item",
                hover_data=[
                    "category",
                    "price",
                    "elasticity_source",
                    "elasticity_confidence",
                ],
                labels={
                    "avg_daily_units": "Avg Daily Units Sold",
                    "contribution_margin_%": (
                        "Contribution Margin %"
                    ),
                },
            )

            quadrant_chart.add_vline(
                x=summary["avg_daily_units"].median(),
                line_dash="dash",
                line_color="gray",
            )

            quadrant_chart.add_hline(
                y=summary["contribution_margin_%"].median(),
                line_dash="dash",
                line_color="gray",
            )

            quadrant_chart = style_chart(
                quadrant_chart,
                title="Menu Engineering Quadrants",
            )

            # Inner chart card
            with st.container(border=True):

                st.plotly_chart(
                    quadrant_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            if cost_is_assumption:
                st.warning(
                    "Quadrants use the estimated cost-percentage "
                    "scenario, not actual unit costs."
                )

        else:
            st.info(
                "Menu quadrants require complete unit cost data "
                "because margin is one axis of the classification."
            )
