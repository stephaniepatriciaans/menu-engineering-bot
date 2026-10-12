"""Menu Item Explorer dashboard section"""

import pandas as pd
import streamlit as st

from dashboard_utils import (
    SORTING_OPTIONS,
    sort_menu_items,
)
from ui.components import render_chart_header
from ui.table_formatters import display_item_table


def render_menu_item_explorer(
    summary: pd.DataFrame,
    capabilities: dict,
    currency: str,
) -> None:
    """Render the sortable menu item exploration table"""

    with st.container(border=True):

        render_chart_header(
            "Menu Item Explorer",
            "Explore menu items by revenue, sales volume, or name. "
            "Category filters are applied automatically.",
        )

        # Sorting options from dashboard_utils.py
        selected_sort = st.selectbox(
            "Sort menu items by",
            options=list(SORTING_OPTIONS.keys()),
            index=0,
            key="menu_item_sort",
        )

        # Preserve the tested sorting function
        sorted_summary = sort_menu_items(
            summary,
            selected_sort,
        )

        has_cost = capabilities["profit_analysis"]

        columns = [
            "item",
            "category",
            "price",
            "avg_daily_units",
            "total_units_sold",
            "total_revenue",
        ]

        if has_cost:
            columns += [
                "unit_cost",
                "contribution_margin_amount",
                "contribution_margin_%",
                "total_profit",
                "quadrant",
            ]

        columns += [
            "elasticity",
            "elasticity_source",
            "elasticity_confidence",
        ]

        # Inner table card
        with st.container(border=True):

            st.dataframe(
                display_item_table(
                    sorted_summary[columns],
                    currency,
                    has_cost,
                ),
                width="stretch",
                hide_index=True,
            )

        st.caption(
            f"Displaying {len(sorted_summary):,} menu items. "
            f"Sorted by: {selected_sort}."
        )
