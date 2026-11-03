"""
generate_data.py

Generates a synthetic but realistic cafe sales dataset.

This is SIMULATED data, modeled on plausible cafe economics (drink/food costs,
seasonal demand, day-of-week effects, and a built-in price elasticity per
item). It's meant to demonstrate the analysis pipeline end-to-end and to be
swapped out for a real cafe's POS export.

Output: data/cafe_sales.csv with columns:
    date, item, category, price, unit_cost, units_sold, day_of_week
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)

# (item, category, base_price, unit_cost, base_daily_units, elasticity)
# elasticity: % change in demand per 1% change in price (negative = normal good)
MENU = [
    ("Drip Coffee",        "Coffee",      3.25, 0.55, 85, -0.6),
    ("Latte",               "Coffee",      4.75, 1.10, 70, -0.9),
    ("Cappuccino",          "Coffee",      4.50, 1.05, 40, -0.9),
    ("Cold Brew",            "Coffee",      4.95, 1.20, 55, -1.1),
    ("Espresso Shot",        "Coffee",      2.75, 0.45, 25, -0.5),
    ("Matcha Latte",         "Tea",         5.25, 1.60, 30, -1.3),
    ("Chai Latte",           "Tea",         4.95, 1.15, 28, -1.0),
    ("Iced Tea",             "Tea",         3.50, 0.50, 20, -0.8),
    ("Croissant",            "Pastry",      3.75, 1.10, 35, -1.2),
    ("Blueberry Muffin",     "Pastry",      3.95, 1.00, 30, -1.4),
    ("Avocado Toast",        "Food",        8.50, 2.60, 22, -1.6),
    ("Breakfast Sandwich",   "Food",        7.25, 2.40, 38, -1.1),
    ("Bagel & Cream Cheese", "Food",        4.50, 1.30, 26, -1.3),
    ("Granola Bowl",         "Food",        6.75, 1.90, 14, -1.7),
    ("Bottled Water",        "Other",       2.25, 0.35, 18, -0.4),
]

START_DATE = date(2025, 1, 1)
NUM_DAYS = 180  # ~6 months of data

DOW_MULTIPLIER = {
    0: 0.95,  # Mon
    1: 0.95,  # Tue
    2: 1.00,  # Wed
    3: 1.05,  # Thu
    4: 1.15,  # Fri
    5: 1.30,  # Sat
    6: 1.10,  # Sun
}


def simulate_daily_units(base_units: float, dow: int) -> int:
    """Apply day-of-week seasonality and random noise to base demand."""
    mult = DOW_MULTIPLIER[dow]
    noise = random.gauss(1.0, 0.12)  # ~12% day-to-day noise
    units = max(0, round(base_units * mult * noise))
    return units


def main():
    rows = []
    for day_offset in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)
        dow = current_date.weekday()

        for item, category, price, cost, base_units, elasticity in MENU:
            units = simulate_daily_units(base_units, dow)
            rows.append({
                "date": current_date.isoformat(),
                "item": item,
                "category": category,
                "price": round(price, 2),
                "unit_cost": round(cost, 2),
                "units_sold": units,
                "day_of_week": current_date.strftime("%A"),
            })

    out_path = "data/cafe_sales.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "item", "category", "price", "unit_cost", "units_sold", "day_of_week"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")

    # Also write a small "menu reference" file with elasticity, useful for
    # the analysis step and for transparency about what's simulated.
    ref_path = "data/menu_reference.csv"
    with open(ref_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "category", "price", "unit_cost", "elasticity"])
        writer.writeheader()
        for item, category, price, cost, base_units, elasticity in MENU:
            writer.writerow({
                "item": item,
                "category": category,
                "price": round(price, 2),
                "unit_cost": round(cost, 2),
                "elasticity": elasticity,
            })
    print(f"Wrote menu reference (with true elasticity) to {ref_path}")


if __name__ == "__main__":
    main()
