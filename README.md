# Menu Engineering Bot

> A universal menu and POS analytics application that turns transaction data into menu-performance insights, pricing simulations, and an AI-assisted management memo.

Menu Engineering Bot combines **data engineering, deterministic business analytics, pricing analysis, and an LLM explanation layer** in one Streamlit application.

Instead of requiring one specific CSV format, the application can ingest datasets from different cafes, restaurants, coffee chains, or POS systems by automatically mapping external columns into a standardized internal schema.

![Menu Engineering Dashboard](assets/dashboard.png)

## Why I Built This

Restaurant and cafe sales data rarely arrives in one standardized format.

One dataset might contain:

```text
transaction_date
product_detail
product_category
unit_price
transaction_qty
```

while another may contain:

```text
Date
Menu Item
Type
Selling Price
COGS
Qty
```

The analytics engine should not have to be rewritten for every dataset.

Menu Engineering Bot solves this by separating **data adaptation** from **business analysis**:

```text
Raw POS / Menu Data
        ↓
Schema Detection + Column Mapping
        ↓
Canonical Dataset
        ↓
Validation + Capability Detection
        ↓
Deterministic Analytics Engine
        ↓
Pricing / Menu Recommendations
        ↓
AI Explanation Layer
```

The numerical analysis is always performed in Python. The LLM never invents or calculates financial metrics.

---

## Key Features

### Universal POS / CSV Adapter

External datasets do not need to use predefined column names.

The app automatically recognizes common fields and allows users to correct mappings through the Streamlit interface.

![Automatic Column Mapping](assets/column_mapping.png)

For example, an external POS dataset can automatically map:

```text
transaction_date   → date
product_detail     → item
product_category   → category
unit_price         → price
transaction_qty    → units_sold
```

The internal analytics engine always receives the same canonical structure:

```text
date
item
category
price
unit_cost
units_sold
```

This keeps dataset-specific logic out of `analysis.py`.

---

## Capability-Aware Analysis

Not every public dataset contains confidential cost information.

Menu Engineering Bot detects what information is available and enables only analyses supported by the data.

For a transaction dataset containing:

```text
date
item
price
units_sold
```

the application can still provide:

- revenue analysis
- sales volume and popularity
- item rankings
- product mix
- sales trends
- price variation analysis
- elasticity analysis when sufficient historical variation exists

Profit-dependent features require unit-cost information.

![Dataset Capabilities](assets/capabilities.png)

If cost is unavailable, the application does **not** fabricate it.

Users can either continue without cost data, upload a separate menu-cost file, or intentionally run a scenario using an estimated cost percentage.

Scenario costs are explicitly labeled as assumptions and are never presented as real company economics.

---

## Real-World Dataset Example

The universal adapter was tested with an external **Maven Roasters coffee-shop transaction dataset** containing fields such as:

```text
transaction_id
transaction_date
transaction_time
transaction_qty
store_id
store_location
product_id
unit_price
product_category
product_type
product_detail
```

The app detects the relevant analytical fields automatically:

```text
transaction_date   → date
product_detail     → item
product_category   → category
unit_price         → price
transaction_qty    → units_sold
```

Because this transaction dataset does not contain unit cost, Menu Engineering Bot correctly enables revenue and popularity analytics while disabling actual profit-based menu engineering.

No internal cost data is inferred or fabricated.

The same adapter architecture can support other cafe, restaurant, coffee-chain, or POS datasets without changing the deterministic analysis engine.

---

## Menu Engineering

When cost information is available, the application calculates:

- contribution margin
- total revenue
- total contribution profit
- average daily sales
- popularity
- Star / Plowhorse / Puzzle / Dog classification

![Menu Engineering Quadrants](assets/quadrant_chart.png)

The bundled **Full Demo Dataset — Synthetic Cafe** contains complete synthetic cost and sales information so the entire menu-engineering workflow can be demonstrated safely.

### Menu Engineering Quadrants

| Quadrant | Popularity | Margin | Interpretation |
|---|---|---|---|
| Star | High | High | Strong performers |
| Plowhorse | High | Low | Popular but margin constrained |
| Puzzle | Low | High | Profitable but under-selected |
| Dog | Low | Low | Candidates for review |

---

## Price Elasticity

For products with enough historical price variation, the application estimates item-level price elasticity using:

```text
log(quantity) ~ log(price)
```

Before accepting an estimate, the model checks factors including:

```text
number of observations
number of unique price points
amount of price variation
zero or invalid quantities
extreme elasticity estimates
```

Every result includes metadata such as:

```text
elasticity
elasticity_source
elasticity_confidence
price_points
observations
```

Possible sources include:

```text
estimated
category_prior
default_prior
```

and confidence levels include:

```text
High
Medium
Low
Prior
```

A category-based prior is therefore never presented as if it were a historical elasticity estimate.

Unknown categories automatically use a configurable generic fallback rather than causing the application to fail.

---

## Deterministic Price Simulation

Price recommendations are generated by Python—not by the LLM.

The engine evaluates configurable candidate price changes such as:

```python
[-0.10, -0.05, 0.00, 0.05, 0.10, 0.15]
```

For each candidate price, the deterministic model estimates the demand response and resulting contribution profit when the required cost data exists.

![Price Recommendations](assets/price_moves.png)

Recommendations expose their elasticity source and confidence so weak assumptions remain visible to the user.

---

## AI Decision Memo

After all numerical analysis is complete, Claude can convert the computed results into a short management memo.

![AI Decision Memo](assets/ai_memo.png)

The AI layer receives calculated outputs such as:

```text
revenue
sales volume
quadrant
recommended price
estimated impact
elasticity source
elasticity confidence
available analyses
business metadata
```

Claude is instructed to:

- explain only existing calculated results
- never create new financial numbers
- distinguish measured results from assumptions
- acknowledge low-confidence elasticity
- avoid profit claims when unit-cost data is unavailable
- provide practical recommendations for restaurant, cafe, or food-service managers

The separation is intentional:

```text
DATA
 ↓
DETERMINISTIC ANALYSIS
 ↓
BUSINESS RECOMMENDATION NUMBERS
 ↓
LLM EXPLANATION
```

---

## Currency Support

The dashboard currently supports:

```text
USD
IDR
EUR
GBP
```

Currency formatting is centralized and easy to extend.

The application does not assume `$` throughout the analytical engine or AI memo.

---

## Project Architecture

```text
menu-engineering-bot/
├── assets/
│   ├── dashboard.png
│   ├── column_mapping.png
│   ├── capabilities.png
│   ├── quadrant_chart.png
│   ├── price_moves.png
│   └── ai_memo.png
│
├── data/
│   ├── cafe_sales.csv
│   └── menu_reference.csv
│
├── src/
│   ├── app.py
│   ├── data_adapter.py
│   ├── validation.py
│   ├── analysis.py
│   ├── config.py
│   ├── agent.py
│   └── generate_data.py
│
├── tests/
│   └── test_universal_pipeline.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### Responsibilities

**`data_adapter.py`**  
Handles delimiter detection, automatic column recognition, manual schema mapping, cost-file merging, and conversion to the canonical dataframe.

**`validation.py`**  
Checks data quality and determines which analytical capabilities are available.

**`analysis.py`**  
Contains deterministic calculations for revenue, margins, menu classification, elasticity, and price simulations.

**`config.py`**  
Stores column aliases, elasticity priors, fallback assumptions, currency formatting, and pricing configuration.

**`agent.py`**  
Passes already-computed results to Claude and generates a management explanation.

**`app.py`**  
Provides the Streamlit user workflow and visualizations.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/stephaniepatriciaans/menu-engineering-bot.git
cd menu-engineering-bot
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run src/app.py
```

Then open:

```text
http://localhost:8501
```

---

## Optional Claude Integration

All deterministic analytics work without an API key.

To enable the AI decision memo:

```bash
cp .env.example .env
```

Add your Anthropic key to `.env`:

```text
ANTHROPIC_API_KEY=your_key_here
```

Then restart Streamlit.

> `.env` is excluded from Git and should never be committed.

---

## Running Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The test suite covers:

```text
Dataset A — canonical input format
Dataset B — alternate column names
Dataset C — missing unit cost
Dataset D — previously unseen category
Estimated-cost scenario
```

These cases verify that schema adaptation and capability detection work independently of any specific restaurant or coffee-chain dataset.

---

## Data & Modeling Limitations

Public restaurant or coffee-company datasets often contain sales transactions, item prices, categories, and quantities but do not contain confidential information such as:

```text
true unit costs
store contribution margins
internal demand curves
supplier contracts
operating economics
```

Menu Engineering Bot does not infer those values unless a user deliberately chooses a labeled scenario assumption.

Similarly, category elasticity priors are modeling assumptions and should not be interpreted as historical estimates.

This distinction is exposed directly in the application through `elasticity_source` and `elasticity_confidence`.

---

## Tech Stack

**Python · pandas · NumPy · Streamlit · Plotly · Anthropic Claude API · unittest**

---

## What This Project Demonstrates

This project combines four areas that are often implemented separately:

**Data Engineering**  
Adapting heterogeneous POS datasets into a stable canonical schema.

**Business Analytics**  
Revenue, contribution margin, product mix, and menu-engineering classification.

**Pricing Analytics**  
Elasticity reliability checks and deterministic price simulations.

**Applied AI**  
Using an LLM to communicate model outputs without delegating numerical reasoning to the model.

The result is a system designed to remain transparent, testable, and reusable across different food-service datasets.

---

Built by [Stephanie Anshell](https://github.com/stephaniepatriciaans)  
[Portfolio](https://stephaniepatriciaans.github.io/portfolio)
