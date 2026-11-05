"""Presentation-only chart for audited eligible sales grouped by calendar day."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def build_audited_daily_sales_chart(days: pd.DataFrame) -> go.Figure:
    """Use discrete calendar-day labels, never auto-generated hourly ticks.

    This changes only the axis presentation; financial totals remain untouched.
    The caller supplies already-aggregated eligible sale amounts (not net sales).
    """
    if days.empty:
        raise ValueError("Daily chart requires at least one date.")

    work = days[["date", "revenue"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="raise")
    work = work.sort_values("date", kind="stable")
    labels = work["date"].dt.strftime("%b %d, %Y").tolist()
    values = work["revenue"].map(float).tolist()

    fig = go.Figure(
        go.Scatter(
            x=labels,
            y=values,
            mode="lines+markers" if len(labels) > 1 else "markers",
            name="Eligible sales",
            hovertemplate="%{x}<br>Eligible sales: %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Eligible sales",
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        showlegend=False,
    )
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=labels,
        tickmode="array",
        tickvals=labels,
        ticktext=labels,
    )
    return fig
