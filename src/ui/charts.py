
"""Reusable Plotly chart styling for the dashboard."""

import plotly.graph_objects as go


FINTECH_COLORS = {
    "blue": "#60A5FA",
    "accent": "#3B82F6",
    "cyan": "#22D3EE",
    "purple": "#A78BFA",
    "green": "#34D399",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "grid": "rgba(148, 163, 184, 0.12)",
}


def style_chart(
    fig: go.Figure,
    title: str | None = None,
) -> go.Figure:
    """Apply consistent Modern Fintech styling to a Plotly chart."""

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial, sans-serif",
            size=18,
        ),
        colorway=[
            FINTECH_COLORS["blue"],
            FINTECH_COLORS["cyan"],
            FINTECH_COLORS["purple"],
            FINTECH_COLORS["green"],
        ],
        margin=dict(l=20, r=20, t=65, b=30),
        hoverlabel=dict(
            bgcolor="#111C30",
            font_color="#F8FAFC",
            bordercolor="#334155",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=FINTECH_COLORS["grid"],
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=FINTECH_COLORS["grid"],
        zeroline=False,
    )

    fig.update_traces(
        selector=dict(type="scatter"),
        line=dict(width=3),
        marker=dict(size=7),
    )

    # Only change the title when a new one is provided.
    # Otherwise, preserve the chart's existing title.
    if title is not None:
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18),
                x=0,
            )
        )

    # Improve readability across all Plotly charts.
    fig.update_xaxes(
        tickfont=dict(size=13),
        title_font=dict(size=15),
    )

    fig.update_yaxes(
        tickfont=dict(size=13),
        title_font=dict(size=15),
    )

    if fig.layout.title.text:
        fig.update_layout(
            title_font=dict(size=19),
        )

    return fig
