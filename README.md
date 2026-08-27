# Menu Engineering Bot

A universal menu-engineering application for cafes, restaurants, coffee chains, and POS exports. It adapts different source schemas into one canonical dataframe, runs deterministic business/pricing analytics, and optionally uses Claude to explain those already-computed results in a management memo.

The core design is intentionally separated:

```text
Raw POS / menu data
        ↓
Schema Adapter + Column Mapping
        ↓
Canonical Dataset
        ↓
Validation + Capability Detection
        ↓
Deterministic Analytics Engine
        ↓
Decision / Price Recommendations
        ↓
LLM Explanation Layer
```

The LLM does **not** calculate margin, elasticity, profit, or recommended prices. Those numbers come from Python/pandas/NumPy first; the LLM only explains them.

## What the app supports

The same pipeline can work with:

- cafe datasets
- restaurant datasets
- coffee-chain/public datasets
- Square/Toast/other POS-style exports
- a user's own CSV
- the bundled full synthetic demo

Starbucks or Blue Bottle can be used as examples later, but neither brand is hardcoded into the analysis engine.

## Canonical internal schema

Internally, analysis uses:

```text
date
item
category
price
unit_cost
units_sold
```

Only these transactional fields are required to get started:

```text
date
item
price
units_sold
```

`category` and `unit_cost` are optional.

External datasets **do not** need to use the canonical column names. `src/data_adapter.py` automatically detects common aliases and the Streamlit UI lets the user correct mappings with dropdowns.

For example, this source:

```text
transaction_date,product_name,product_category,unit_price,cost,quantity
```

maps automatically to:

```text
date,item,category,price,unit_cost,units_sold
```

A source such as:

```text
Date,Menu Item,Type,Selling Price,COGS,Qty
```

can map to the same canonical dataframe without changing `analysis.py`.

## Missing cost is handled explicitly

Many public food/beverage datasets contain transactions and prices but not confidential internal unit costs. The app does **not** invent those costs.

If `unit_cost` is missing, the app can still run:

- revenue analysis
- popularity / volume analysis
- sales trends
- item rankings
- price variation analysis
- historical elasticity estimation when sufficient price variation exists

The app disables:

- contribution margin
- total profit
- traditional Star / Plowhorse / Puzzle / Dog classification
- profit-maximizing price recommendations

until complete cost information is available.

The user may optionally:

1. map a cost column already present in the sales file,
2. upload a separate menu-cost CSV and match it by item, or
3. deliberately run a scenario using an estimated cost percentage.

Option 3 is labeled as an **assumption** in the dashboard and AI prompt. It is never presented as actual Starbucks, Blue Bottle, restaurant, or cafe cost data.

## Elasticity reliability

For each item, the deterministic engine attempts to estimate:

```text
log(quantity) ~ log(price)
```

using daily observations when there is enough usable price variation. Each item includes:

```text
elasticity
elasticity_source
elasticity_confidence
price_points
observations
price_variation_%
```

`elasticity_source` can distinguish a historical estimate from a configured prior:

- `estimated`
- `category_prior`
- `default_prior`

Confidence is labeled `High`, `Medium`, `Low`, or `Prior`.

Category priors are configured in `src/config.py`. Unknown categories do not cause failures; they fall back to a generic configurable prior. A category such as `Refreshers`, for example, works without adding application code.

## Price simulation

Candidate price changes are configured centrally rather than hardcoded inside the analysis loop. The default is:

```python
[-0.10, -0.05, 0.00, 0.05, 0.10, 0.15]
```

The Streamlit sidebar also lets the user control the maximum tested decrease/increase. Simulations reject changes that would make prices non-positive.

Profit-based recommendations run only when full cost data exists (or when the user explicitly selected a cost scenario assumption).

## Currency and dataset settings

The dashboard accepts:

- business name
- dataset name
- currency

Built-in formatting supports:

- USD
- IDR
- EUR
- GBP

The implementation is easy to extend in `src/config.py`. The UI and AI memo do not assume dollars.

## Streamlit workflow

The dashboard follows this flow:

```text
1. Load Dataset
2. Detect / Map Columns
3. Validate Dataset
4. Show Dataset Overview
5. Show Available Analyses
6. Run Revenue / Popularity / Elasticity / Menu Engineering
7. View Price Recommendations (when cost permits)
8. Generate AI Decision Memo
```

The dataset overview includes row count, date range, unique items, categories, total units, revenue, and validation/data-quality warnings.

## Bundled synthetic demo

`data/cafe_sales.csv` remains the one-click **Full Demo Dataset — Synthetic Cafe**. It includes prices, unit costs, quantities, categories, and dates so the complete pipeline can be demonstrated end to end.

`src/generate_data.py` remains the generator for that synthetic dataset, and `data/menu_reference.csv` documents the synthetic assumptions used to create it.

## Loading a Starbucks-style dataset

Suppose a public CSV contains:

```text
transaction_date
product_detail
product_category
unit_price
transaction_qty
```

Upload it in Streamlit. Automatic mapping should preselect:

```text
transaction_date   → date
product_detail     → item
product_category   → category
unit_price         → price
transaction_qty    → units_sold
Not available      → unit_cost
```

No change to `analysis.py` is required.

If that public dataset has no unit-cost field, revenue/popularity/trend analysis still works, while profit-dependent features are disabled. You may add a real cost file or intentionally choose a scenario percentage, but the app will not fabricate Starbucks internal economics.

## Loading a Blue-Bottle-style dataset

The process is identical. Upload the CSV and let automatic detection map recognizable fields. If a source has unusual names, use the mapping dropdowns once; the analytics engine still receives the same canonical dataframe.

For example:

```text
Sale Date      → date
Menu Item      → item
Type           → category
Selling Price  → price
Qty            → units_sold
COGS           → unit_cost  # only if this field genuinely exists
```

There is no Blue Bottle-specific logic in the analysis code.

## Public-company data limitation

Public datasets may be useful for demonstrating transaction volume, product mix, prices, or category trends. They should **not** be described as containing confidential costs, true demand curves, store-level economics, or internal profit unless those fields genuinely exist in the dataset.

A prior-based elasticity is also not equivalent to elasticity estimated from historical price variation. The UI and memo expose that distinction.

## Project structure

```text
menu-engineering-bot/
├── assets/
│   ├── dashboard.png
│   ├── item_summary.png
│   ├── quadrant_chart.png
│   ├── price_moves.png
│   └── ai_memo.png
├── data/
│   ├── cafe_sales.csv
│   └── menu_reference.csv
├── src/
│   ├── app.py               # Streamlit workflow/UI
│   ├── data_adapter.py      # aliases, auto-detection, canonical mapping, cost merge
│   ├── validation.py        # canonical validation + capability detection
│   ├── analysis.py          # deterministic revenue/margin/elasticity/quadrants/pricing
│   ├── config.py            # aliases, priors, currency, price-change config
│   ├── agent.py             # Claude explanation layer only
│   └── generate_data.py     # bundled synthetic demo generator
├── tests/
│   └── test_universal_pipeline.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Tests

The lightweight `unittest` suite verifies:

- Dataset A: original canonical format runs full analysis
- Dataset B: alternate names automatically map to canonical fields
- Dataset C: missing unit cost still runs safely and disables profit features
- Dataset D: unknown category falls back to the generic elasticity prior
- explicit estimated-cost scenario enables scenario profit analysis

Run:

```bash
python -m unittest discover -s tests -v
```

## Running the app

```bash
git clone https://github.com/stephaniepatriciaans/menu-engineering-bot
cd menu-engineering-bot
pip install -r requirements.txt

# Optional: regenerate bundled synthetic demo
python src/generate_data.py

# Optional: only required for the AI memo
cp .env.example .env
# edit .env and add ANTHROPIC_API_KEY

streamlit run src/app.py
```

Without an Anthropic API key, the adapter, validation, dashboard, elasticity analysis, and deterministic recommendations continue to work. Only AI memo generation is unavailable.

## Main portfolio value

The project is designed to demonstrate the full chain rather than hide the math behind an LLM:

```text
DATA ENGINEERING
      ↓
DETERMINISTIC BUSINESS ANALYTICS
      ↓
PRICING / RECOMMENDATION NUMBERS
      ↓
AI EXPLANATION
```

That separation keeps the outputs inspectable, testable, and recruiter-friendly.

---

Built by [Stephanie Anshell](https://github.com/stephaniepatriciaans) — [portfolio](https://stephaniepatriciaans.github.io/portfolio)
