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
        font={
            "family": "Arial, sans-serif",
            "size": 18,
        },
        colorway=[
            FINTECH_COLORS["blue"],
            FINTECH_COLORS["cyan"],
            FINTECH_COLORS["purple"],
            FINTECH_COLORS["green"],
        ],
        margin={
            "l": 20,
            "r": 20,
            "t": 65,
            "b": 30,
        },
        hoverlabel={
            "bgcolor": "#111C30",
            "font_color": "#F8FAFC",
            "bordercolor": "#334155",
        },
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
        selector={"type": "scatter"},
        line={"width": 3},
        marker={"size": 7},
    )

    # Preserve an existing chart title unless a new one is supplied.
    if title is not None:
        fig.update_layout(
            title={
                "text": title,
                "font": {"size": 18},
                "x": 0,
            }
        )

    fig.update_xaxes(
        tickfont={"size": 13},
        title_font={"size": 15},
    )

    fig.update_yaxes(
        tickfont={"size": 13},
        title_font={"size": 15},
    )

    title_info = fig.to_plotly_json().get(
        "layout", {}
    ).get("title", {})

    if isinstance(title_info, dict) and title_info.get("text"):
        fig.update_layout(
            title_font={"size": 19},
        )

    return fig
