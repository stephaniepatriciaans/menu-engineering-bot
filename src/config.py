"""Configuration shared across the universal menu-engineering pipeline."""

from __future__ import annotations

import re
from typing import Mapping

CANONICAL_FIELDS = ["date", "item", "category", "price", "unit_cost", "units_sold"]
CORE_FIELDS = ["date", "item", "price", "units_sold"]
OPTIONAL_FIELDS = ["category", "unit_cost"]

COLUMN_ALIASES: dict[str, list[str]] = {
    "date": [
        "date", "transaction_date", "order_date", "sale_date", "sales_date",
        "business_date", "datetime", "date_time", "timestamp", "transaction_time",
        "order_datetime", "created_at",
    ],
    "item": [
        "item", "product", "product_name", "product_detail", "product_description",
        "menu_item", "menu_item_name", "item_name", "item_description", "description",
        "sku_name", "article_name",
    ],
    "category": [
        "category", "product_category", "item_category", "type", "menu_category",
        "department", "product_group", "item_group", "food_category",
    ],
    "price": [
        "price", "unit_price", "selling_price", "sales_price", "retail_price",
        "item_price", "menu_price", "price_each", "unit_sales_price", "amount_each",
    ],
    "unit_cost": [
        "unit_cost", "cost", "cogs", "cost_of_goods", "cost_of_goods_sold",
        "item_cost", "food_cost", "ingredient_cost", "unit_cogs", "cost_each",
    ],
    "units_sold": [
        "units_sold", "quantity", "qty", "units", "items_sold", "transaction_qty",
        "transaction_quantity", "order_quantity", "quantity_sold", "sold_qty",
        "item_quantity", "count",
    ],
}

# These are scenario priors, not measured demand curves. Unknown categories fall
# back to DEFAULT_ELASTICITY_PRIOR and never cause analysis to fail.
CATEGORY_ELASTICITY_PRIORS: dict[str, float] = {
    "Coffee": -0.8,
    "Tea": -1.0,
    "Cold Beverage": -1.0,
    "Food": -1.3,
    "Bakery": -1.2,
    "Pastry": -1.2,
    "Dessert": -1.3,
    "Snack": -1.1,
    "Alcohol": -1.1,
    "Other": -1.0,
    "Uncategorized": -1.0,
}
DEFAULT_ELASTICITY_PRIOR = -1.0

DEFAULT_PRICE_CHANGES = [-0.10, -0.05, 0.00, 0.05, 0.10, 0.15]

# Reliability thresholds for historical log(quantity) ~ log(price) estimates.
MIN_ELASTICITY_OBSERVATIONS = 8
MIN_ELASTICITY_PRICE_POINTS = 2
MIN_RELATIVE_PRICE_RANGE = 0.02
ELASTICITY_CLIP = (-3.0, 0.5)

CURRENCY_CONFIG = {
    "USD": {"symbol": "$", "decimals": 2, "position": "prefix"},
    "IDR": {"symbol": "Rp", "decimals": 0, "position": "prefix_space"},
    "EUR": {"symbol": "€", "decimals": 2, "position": "prefix"},
    "GBP": {"symbol": "£", "decimals": 2, "position": "prefix"},
}


def normalize_column_name(value: object) -> str:
    """Normalize a column label for case/punctuation-insensitive matching."""
    text = str(value).strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def category_prior(category: object, priors: Mapping[str, float] | None = None) -> tuple[float, str]:
    """Return the configured prior and whether it came from a category or default."""
    source = priors or CATEGORY_ELASTICITY_PRIORS
    normalized = str(category).strip().casefold()
    for name, value in source.items():
        if name.casefold() == normalized:
            return float(value), "category_prior"
    return float(DEFAULT_ELASTICITY_PRIOR), "default_prior"


def format_currency(value: float | int | None, currency: str = "USD") -> str:
    """Format money without hardcoding a single currency symbol in the UI."""
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    cfg = CURRENCY_CONFIG.get(currency, {"symbol": currency, "decimals": 2, "position": "prefix_space"})
    decimals = int(cfg["decimals"])
    amount = f"{number:,.{decimals}f}"
    if cfg["position"] == "prefix":
        return f"{cfg['symbol']}{amount}"
    if cfg["position"] == "prefix_space":
        return f"{cfg['symbol']} {amount}"
    return f"{amount} {cfg['symbol']}"
