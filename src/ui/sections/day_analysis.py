"""Day Analysis dashboard section."""

import pandas as pd
import plotly.express as px
import streamlit as st

from config import format_currency
from dashboard_utils import (
    analyze_day_of_week,
    compare_weekday_weekend,
)
from ui.charts import style_chart
from ui.components import render_chart_header
from ui.table_formatters import safe_format_currency


def render_day_analysis(
    df: pd.DataFrame,
    currency: str,
) -> None:
    """Render weekday/weekend and Monday–Sunday sales analysis."""

    # =============================================================
    # CARD 1 — Weekday vs. Weekend Performance
    # =============================================================

    with st.container(border=True):

        render_chart_header(
            "Weekday vs. Weekend Performance",
            "Compare Monday–Friday with Saturday–Sunday. "
            "Averages use days with recorded sales.",
        )

        # Preserve the existing analysis calculation.
        day_type_summary = compare_weekday_weekend(df)

        # Display metrics for each day type.
        comparison_cols = st.columns(2, gap="medium")

        for index, day_type in enumerate(["Weekday", "Weekend"]):

            result = day_type_summary[
                day_type_summary["day_type"] == day_type
            ]

            with comparison_cols[index]:

                st.markdown(f"#### {day_type}s")

                if result.empty:
                    st.info(
                        "No sales recorded for this day type."
                    )
                    continue

                row = result.iloc[0]

                st.metric(
                    "Total Revenue",
                    format_currency(
                        row["total_revenue"],
                        currency,
                    ),
                )

                st.metric(
                    "Total Units Sold",
                    f"{row['total_units']:,.0f}",
                )

                st.metric(
                    "Average Revenue per Sales Day",
                    format_currency(
                        row["avg_daily_revenue"],
                        currency,
                    ),
                )

                st.caption(
                    "Days with recorded sales: "
                    f"{int(row['days_with_sales'])}"
                )

        # Weekday vs. weekend chart.
        fig_weekend = px.bar(
            day_type_summary,
            x="day_type",
            y="avg_daily_revenue",
            color="day_type",
            title="Average Revenue per Sales Day",
            labels={
                "day_type": "Day Type",
                "avg_daily_revenue": (
                    f"Average Revenue ({currency})"
                ),
            },
            category_orders={
                "day_type": ["Weekday", "Weekend"],
            },
        )

        fig_weekend.update_layout(
            showlegend=False,
        )

        fig_weekend = style_chart(
            fig_weekend,
            title="Average Revenue per Sales Day",
        )

        with st.container(border=True):
            st.plotly_chart(
                fig_weekend,
                width="stretch",
                config={"displayModeBar": False},
            )

        # Keep data table inside the card.
        with st.expander(
            "View weekday vs. weekend data",
            expanded=False,
        ):

            comparison_table = day_type_summary.copy()

            for column in [
                "total_revenue",
                "avg_daily_revenue",
            ]:
                comparison_table[column] = (
                    comparison_table[column].map(
                        lambda value: safe_format_currency(
                            value,
                            currency,
                        )
                    )
                )

            st.dataframe(
                comparison_table,
                width="stretch",
                hide_index=True,
            )

    # =============================================================
    # CARD 2 — Monday–Sunday Performance
    # =============================================================

    with st.container(border=True):

        render_chart_header(
            "Sales Performance by Day of Week",
            "Compare Monday through Sunday using your selected "
            "date range and menu categories. Averages use days "
            "with recorded sales.",
        )

        # Preserve the existing day-of-week calculation.
        day_summary = analyze_day_of_week(df)

        day_metric = st.selectbox(
            "Compare days by",
            options=[
                "Total Revenue",
                "Total Units Sold",
                "Average Daily Revenue",
                "Average Daily Units",
            ],
            key="day_of_week_metric",
        )

        day_metric_columns = {
            "Total Revenue": "total_revenue",
            "Total Units Sold": "total_units",
            "Average Daily Revenue": "avg_daily_revenue",
            "Average Daily Units": "avg_daily_units",
        }

        selected_column = day_metric_columns[day_metric]

        day_chart = px.bar(
            day_summary,
            x="day_name",
            y=selected_column,
            category_orders={
                "day_name": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ],
            },
            labels={
                "day_name": "Day of Week",
                selected_column: day_metric,
            },
            title=f"{day_metric} by Day of Week",
        )

        day_chart.update_layout(
            xaxis_title="Day of Week",
            yaxis_title=(
                f"{day_metric} ({currency})"
                if "Revenue" in day_metric
                else day_metric
            ),
        )

        day_chart = style_chart(
            day_chart,
            title=f"{day_metric} by Day of Week",
        )

        with st.container(border=True):
            st.plotly_chart(
                day_chart,
                width="stretch",
                config={"displayModeBar": False},
            )

        # Highlight strongest and weakest days using
        # average daily revenue, not total revenue.
        best_day = day_summary.iloc[
            day_summary["avg_daily_revenue"].argmax()
        ]

        slowest_day = day_summary.iloc[
            day_summary["avg_daily_revenue"].argmin()
        ]

        best_col, slowest_col = st.columns(
            2,
            gap="medium",
        )

        with best_col:
            st.metric(
                "Highest Avg. Revenue Day",
                best_day["day_name"],
                (
                    f"{currency}"
                    f"{best_day['avg_daily_revenue']:,.2f}/day"
                ),
            )

        with slowest_col:
            st.metric(
                "Lowest Avg. Revenue Day",
                slowest_day["day_name"],
                (
                    f"{currency}"
                    f"{slowest_day['avg_daily_revenue']:,.2f}/day"
                ),
            )

        # Keep the Monday–Sunday data table inside the card.
        with st.expander(
            "View Monday–Sunday Sales Data",
            expanded=False,
        ):

            display_days = day_summary[
                [
                    "day_name",
                    "total_revenue",
                    "total_units",
                    "days_with_sales",
                    "avg_daily_revenue",
                    "avg_daily_units",
                ]
            ].copy()

            display_days.columns = [
                "Day",
                "Total Revenue",
                "Total Units",
                "Days With Sales",
                "Avg. Daily Revenue",
                "Avg. Daily Units",
            ]

            st.dataframe(
                display_days,
                width="stretch",
                hide_index=True,
            )
