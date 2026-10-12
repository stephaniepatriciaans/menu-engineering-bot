"""Format analytics tables for Streamlit display."""

from numbers import Real

import pandas as pd

from config import format_currency


def safe_format_currency(value: object, currency: str) -> str:
    """Format numeric values while handling missing data safely."""
    if value is None or value is pd.NA:
        return "—"

    if isinstance(value, bool):
        return "—"

    if not isinstance(value, (int, float, str)):
        return "—"

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "—"

    return format_currency(number, currency)


def display_item_table(
    summary: pd.DataFrame,
    currency: str,
    has_cost: bool,
) -> pd.DataFrame:
    """Format menu item financial values for display."""
    table = summary.copy()

    currency_columns = [
        "price",
        "total_revenue",
    ]

    if has_cost:
        currency_columns.extend([
            "unit_cost",
            "contribution_margin_amount",
            "total_profit",
        ])

    for col in currency_columns:
        table[col] = table[col].map(
            lambda value: safe_format_currency(value, currency)
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
        if col in table.columns:
            table[col] = table[col].map(
                lambda value: safe_format_currency(value, currency)
            )

    return table
