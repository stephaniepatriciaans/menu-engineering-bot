"""Format analytics tables for Streamlit display.

These helpers return formatted copies of DataFrames.
Financial calculations remain in analysis.py.
"""

import pandas as pd

from config import format_currency


def display_item_table(
    summary: pd.DataFrame,
    currency: str,
    has_cost: bool,
) -> pd.DataFrame:
    """Format menu item financial values for display."""
    table = summary.copy()

    table["price"] = table["price"].map(
        lambda x: format_currency(x, currency)
    )
    table["total_revenue"] = table["total_revenue"].map(
        lambda x: format_currency(x, currency)
    )

    if has_cost:
        table["unit_cost"] = table["unit_cost"].map(
            lambda x: format_currency(x, currency)
        )
        table["contribution_margin_amount"] = (
            table["contribution_margin_amount"].map(
                lambda x: format_currency(x, currency)
            )
        )
        table["total_profit"] = table["total_profit"].map(
            lambda x: format_currency(x, currency)
        )

    return table


def display_moves_table(
    moves: pd.DataFrame,
    currency: str,
) -> pd.DataFrame:
    """Format pricing recommendation values for display."""
    table = moves.copy()

    currency_columns = [
        "old_price",
        "new_price",
        "old_daily_profit_est",
        "new_daily_profit_est",
        "daily_profit_delta",
    ]

    for col in currency_columns:
        if col in table:
            table[col] = table[col].map(
                lambda x: format_currency(x, currency)
            )

    return table
