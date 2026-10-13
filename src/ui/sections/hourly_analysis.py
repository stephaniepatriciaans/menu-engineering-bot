"""Hourly Analysis dashboard section."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_utils import (
    analyze_hourly_revenue,
    analyze_peak_hours,
)
from ui.charts import style_chart
from ui.components import render_chart_header


def render_hourly_analysis(
    df: pd.DataFrame,
    currency: str,
) -> None:
    """Render peak-hour and hourly revenue analysis."""

    # ------------------------------------------------------------
    # CARD 1 — Peak-Hour Analysis
    # ------------------------------------------------------------
    with st.container(border=True):

        render_chart_header(
            "Peak-Hour Analysis",
            "Identify busy hours using transaction timestamps. "
            "Results reflect your selected date range and categories.",
        )

        if df["transaction_datetime"].notna().any():

            hourly_summary = analyze_peak_hours(df)

            hour_metric = st.selectbox(
                "Analyze peak hours by",
                options=[
                    "Revenue",
                    "Units Sold",
                    "Sales Records",
                ],
                key="peak_hour_metric",
            )

            hour_columns = {
                "Revenue": "total_revenue",
                "Units Sold": "total_units",
                "Sales Records": "sales_rows",
            }

            selected_hour_column = hour_columns[hour_metric]

            hourly_summary["hour_label"] = (
                hourly_summary["hour"]
                .map(lambda hour: f"{hour:02d}:00")
            )

            peak_chart = px.bar(
                hourly_summary,
                x="hour_label",
                y=selected_hour_column,
                labels={
                    "hour_label": "Hour of Day",
                    selected_hour_column: hour_metric,
                },
                title=f"{hour_metric} by Hour of Day",
            )

            peak_chart.update_layout(
                xaxis_title="Hour of Day",
                yaxis_title=(
                    f"Revenue ({currency})"
                    if hour_metric == "Revenue"
                    else hour_metric
                ),
            )

            peak_chart = style_chart(
                peak_chart,
                title=f"{hour_metric} by Hour of Day",
            )

            # Inner chart card
            with st.container(border=True):
                st.plotly_chart(
                    peak_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            if not hourly_summary.empty:
                busiest_hour = hourly_summary.iloc[
                    hourly_summary[selected_hour_column].argmax()
                ]

                st.metric(
                    f"Peak Hour by {hour_metric}",
                    busiest_hour["hour_label"],
                )

            with st.expander(
                "View Hourly Sales Data",
                expanded=False,
            ):
                display_hourly = hourly_summary[
                    [
                        "hour_label",
                        "total_revenue",
                        "total_units",
                        "sales_rows",
                    ]
                ].rename(
                    columns={
                        "hour_label": "Hour",
                        "total_revenue": "Revenue",
                        "total_units": "Units Sold",
                        "sales_rows": "Sales Records",
                    }
                )

                st.dataframe(
                    display_hourly,
                    width="stretch",
                    hide_index=True,
                )

        else:
            st.info(
                "Peak-hour analysis is unavailable because "
                "the dataset does not contain usable transaction times."
            )

    # ------------------------------------------------------------
    # CARD 2 — Hourly Revenue Analysis
    # ------------------------------------------------------------
    with st.container(border=True):

        render_chart_header(
            "Hourly Revenue Analysis",
            "Compare average hourly revenue across days with "
            "recorded sales in that hour. Days without recorded "
            "sales for an hour are excluded from that hour's average.",
        )

        if df["transaction_datetime"].notna().any():

            hourly_revenue = analyze_hourly_revenue(df)

            hourly_revenue["hour_label"] = (
                hourly_revenue["hour"]
                .map(lambda hour: f"{hour:02d}:00")
            )

            revenue_chart = px.line(
                hourly_revenue,
                x="hour_label",
                y="avg_daily_revenue",
                markers=True,
                labels={
                    "hour_label": "Hour of Day",
                    "avg_daily_revenue": (
                        f"Average Revenue ({currency})"
                    ),
                },
                title="Average Revenue by Hour",
            )

            revenue_chart.update_layout(
                xaxis_title="Hour of Day",
                yaxis_title=f"Average Revenue ({currency})",
            )

            revenue_chart = style_chart(
                revenue_chart,
                title="Average Revenue by Hour",
            )

            # Inner chart card
            with st.container(border=True):
                st.plotly_chart(
                    revenue_chart,
                    width="stretch",
                    config={"displayModeBar": False},
                )

            if not hourly_revenue.empty:
                highest_hour = hourly_revenue.iloc[
                    hourly_revenue["avg_daily_revenue"].argmax()
                ]

                st.metric(
                    "Highest Average Revenue Hour",
                    highest_hour["hour_label"],
                )

            with st.expander(
                "View Hourly Revenue Data",
                expanded=False,
            ):
                display_hourly_revenue = hourly_revenue[
                    [
                        "hour_label",
                        "total_revenue",
                        "days_with_sales",
                        "avg_daily_revenue",
                    ]
                ].rename(
                    columns={
                        "hour_label": "Hour",
                        "total_revenue": "Total Revenue",
                        "days_with_sales": "Days With Sales",
                        "avg_daily_revenue": (
                            "Avg. Revenue per Active Day"
                        ),
                    }
                )

                st.dataframe(
                    display_hourly_revenue,
                    width="stretch",
                    hide_index=True,
                )

        else:
            st.info(
                "Hourly revenue analysis is unavailable because "
                "the dataset does not contain usable transaction times"
            )