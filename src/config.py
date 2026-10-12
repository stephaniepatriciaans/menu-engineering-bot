"""Configuration shared across the universal menu-engineering pipeline."""

from __future__ import annotations

import re
from typing import Mapping

CANONICAL_FIELDS = ["date", "item", "category", "price", "unit_cost", "units_sold", "transaction_time"]
CORE_FIELDS = ["date", "item", "price", "units_sold"]
OPTIONAL_FIELDS = ["category", "unit_cost", "transaction_time"]

COLUMN_ALIASES: dict[str, list[str]] = {
    "date": [
        "date", "transaction_date", "order_date", "sale_date", "sales_date",
        "business_date", "datetime", "date_time", "timestamp",
        "order_datetime", "transaction_date", "created_at",
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
    "transaction_time": [
        "transaction_time", "order_time", "sale_time", "sales_time", "time",
        "time_of_sale", "purchase_time", "checkout_time",
    ],

}


# Broad category groups used for dashboard filtering.
CATEGORY_GROUPS = ["Savory", "Dessert", "Drinks", "Other"]

# Map restaurant-specific categories to broader groups.
# Add or change entries to support different restaurant datasets.
CATEGORY_GROUP_MAPPING: dict[str, str] = {
    # Drinks
    "coffee": "Drinks",
    "tea": "Drinks",
    "cold beverage": "Drinks",
    "hot beverage": "Drinks",
    "beverage": "Drinks",
    "drinks": "Drinks",
    "juice": "Drinks",
    "smoothie": "Drinks",
    "matcha": "Drinks",
    "alcohol": "Drinks",
    "drinking chocolate": "Drinks",

    # Desserts
    "bakery": "Dessert",
    "pastry": "Dessert",
    "dessert": "Dessert",
    "cake": "Dessert",
    "cookie": "Dessert",
    "ice cream": "Dessert",

    # Savory
    "food": "Savory",
    "savory": "Savory",
    "sandwich": "Savory",
    "sandwiches": "Savory",
    "pasta": "Savory",
    "salad": "Savory",
    "breakfast": "Savory",
    "main course": "Savory",

    # Unknown or mixed categories
    "other": "Other",
    "uncategorized": "Other",
    "flavours": "Other",
    "coffee beans": "Other",
    "loose tea": "Other",
    "branded": "Other",
    "packaged chocolate": "Other",
}


# Optional item-level overrides.
# These take priority over broad category mappings.
ITEM_CATEGORY_OVERRIDES: dict[str, str] = {
    "jumbo savory scone": "Savory",
}


def classify_menu_item(
    category: object,
    item: object,
    category_mapping: Mapping[str, str] | None = None,
    item_overrides: Mapping[str, str] | None = None,
) -> str:
    """Classify an item, prioritizing specific item overrides."""

    overrides = (
        ITEM_CATEGORY_OVERRIDES
        if item_overrides is None
        else item_overrides
    )

    normalized_item = str(item).strip().casefold()

    for item_name, group in overrides.items():
        if str(item_name).strip().casefold() == normalized_item:
            if group not in CATEGORY_GROUPS:
                raise ValueError(
                    f"Unsupported category group: {group}"
                )
            return group

    return category_group(category, mapping=category_mapping)


def category_group(
    category: object,
    mapping: Mapping[str, str] | None = None,
) -> str:
    """Map an original menu category to a broad category group."""

    source = (
        CATEGORY_GROUP_MAPPING
        if mapping is None
        else mapping
    )

    normalized = str(category).strip().casefold()

    if not normalized:
        return "Other"

    for original_category, group in source.items():
        if str(original_category).strip().casefold() == normalized:
            if group not in CATEGORY_GROUPS:
                raise ValueError(
                    f"Unsupported category group: {group}"
                )
            return group

    return "Other"

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
