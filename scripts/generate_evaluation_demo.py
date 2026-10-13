"""Generate synthetic data for demonstrating demand model evaluation

All prices, transactions, and demand relationships are simulated.
This dataset is not evidence of real-world pricing performance.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_PATH = Path("data/evaluation_ready_cafe.csv")
RANDOM_SEED = 42
N_DAYS = 240

MENU = [
    ("Latte", "Coffee", 4.75, 1.55, 80, -1.4),
    ("Cappuccino", "Coffee", 4.50, 1.40, 65, -1.2),
    ("Cold Brew", "Coffee", 5.25, 1.65, 70, -1.6),
    ("Drip Coffee", "Coffee", 3.25, 0.90, 95, -0.9),
    ("Matcha Latte", "Tea", 5.75, 1.90, 55, -1.5),
    ("Chai Latte", "Tea", 4.95, 1.60, 60, -1.3),
    ("Croissant", "Bakery", 3.95, 1.35, 75, -1.1),
    ("Blueberry Muffin", "Bakery", 3.75, 1.20, 65, -1.0),
]

# Simulated historical pricing experiments:
# six different prices, repeated across the date range.
PRICE_MULTIPLIERS = np.array(
    [0.85, 0.92, 1.00, 1.08, 1.15, 1.25],
    dtype=float,
)


def generate_dataset() -> pd.DataFrame:
    """Create reproducible daily item sales with changing prices."""
    rng = np.random.default_rng(RANDOM_SEED)
    dates = pd.date_range("2025-01-01", periods=N_DAYS)

    records = []

    for item, category, base_price, unit_cost, demand, elasticity in MENU:
        for day_index, date in enumerate(dates):
            price_index = (day_index // 14) % len(PRICE_MULTIPLIERS)
            multiplier = PRICE_MULTIPLIERS[price_index]

            price = round(base_price * multiplier, 2)

            # This demand relationship is intentionally simulated.
            expected_units = demand * (
                price / base_price
            ) ** elasticity

            # Small weekday and weekend differences.
            day_factor = 1.12 if date.dayofweek >= 5 else 1.0

            # Random sales variation around expected demand.
            expected_units *= day_factor
            units = max(
                1,
                int(rng.poisson(expected_units)),
            )

            records.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "item": item,
                    "category_group": category,
                    "category": category,
                    "price": price,
                    "units_sold": units,
                    "unit_cost": unit_cost,
                }
            )

    return pd.DataFrame.from_records(records)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = generate_dataset()

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Sales rows: {len(df):,}")
    print(f"Menu items: {df['item'].nunique()}")
    print(f"Unique dates: {df['date'].nunique()}")
    print("Dataset: SYNTHETIC — for testing only")


if __name__ == "__main__":
    main()
