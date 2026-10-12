"""Sales Trends section of the Menu Engineering Bot dashboard."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_utils import aggregate_sales_by_period
from ui.charts import style_chart
from ui.components import render_chart_header
from ui.table_formatters import safe_format_currency


def render_sales_trends(
    df: pd.DataFrame,
    currency: str,
) -> None:
    """Render sales trends with existing controls and styling."""

    # Sales Trends card
    with st.container(border=True):

        render_chart_header(
            "Sales Performance Over Time",
            "Explore revenue and sales volume across different time periods.",
        )

        # Dashboard controls
        control_col1, control_col2 = st.columns(
            [3, 1],
            gap="medium",
            vertical_alignment="bottom",
        )

        with control_col1:
            time_grouping = st.radio(
                "Group sales by",
                options=[
                    "Daily",
                    "Weekly",
                    "Monthly",
                    "Yearly",
                ],
                index=2,
                horizontal=True,
                key="sales_time_grouping",
            )

        with control_col2:
            metric_choice = st.selectbox(
                "Metric",
                options=["Revenue", "Units Sold"],
                key="sales_trend_metric",
            )

        # Preserve existing aggregation.
        grouped_sales = aggregate_sales_by_period(
            df,
            time_grouping,
        )

        # Select the metric.
        if metric_choice == "Revenue":
            y_column = "revenue"
            y_label = f"Revenue ({currency})"
        else:
            y_column = "units_sold"
            y_label = "Units Sold"

        # Create the time-series chart.
        fig = px.line(
            grouped_sales,
            x="period",
            y=y_column,
            markers=True,
            title=f"{time_grouping} {metric_choice} Trend",
            labels={
                "period": "Period Starting",
                y_column: y_label,
            },
        )

        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Date",
            yaxis_title=y_label,
        )

        # Apply styling once.
        fig = style_chart(
            fig,
            title=f"{time_grouping} {metric_choice} Trend",
        )

        with st.container(border=True):
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

        # Display the aggregated data.
        with st.expander("View sales data by period"):
            display_sales = grouped_sales.copy()

            display_sales["period"] = (
                display_sales["period"].dt.strftime("%Y-%m-%d")
            )

            display_sales["revenue"] = display_sales[
                "revenue"
            ].map(lambda x: safe_format_currency(x, currency))

            st.dataframe(
                display_sales,
                width="stretch",
                hide_index=True,
            )
