"""Popular Items dashboard section."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.charts import style_chart
from ui.components import render_chart_header


def render_popular_items(summary: pd.DataFrame) -> None:
    """Display the 15 best-selling menu items by units sold."""

    # Outer card — entire Popular Items section
    with st.container(border=True):

        render_chart_header(
            "Top Selling Menu Items",
            "Discover which menu items sell the most units.",
        )

        # Preserve existing top-selling item calculations.
        top_volume = summary.nlargest(
            min(15, len(summary)),
            "total_units_sold",
        )

        popular_items_chart = px.bar(
            top_volume,
            x="total_units_sold",
            y="item",
            orientation="h",
            title="Top Items by Units Sold",
            labels={
                "total_units_sold": "Units Sold",
                "item": "Menu Item",
            },
        )

        # Apply reusable chart styling
        popular_items_chart = style_chart(
            popular_items_chart,
            title="Top Items by Units Sold",
        )

        # Inner card — chart only
        with st.container(border=True):
            st.plotly_chart(
                popular_items_chart,
                width="stretch",
                config={"displayModeBar": False},
            )
