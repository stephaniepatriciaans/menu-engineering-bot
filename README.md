# Menu Engineering Bot

### Universal POS Analytics · Menu Engineering · Pricing Simulation · AI Decision Support

A Streamlit application that transforms restaurant and coffee-shop sales data into actionable business insights through **data engineering, deterministic analytics, pricing simulations, and AI-assisted reporting**.

The application adapts different point-of-sale (POS) CSV formats into a standardized schema, analyzes revenue and profitability where sufficient data exists, evaluates price elasticity, and generates downloadable business decision memos.

**The key design principle:** Python performs the numerical calculations. The LLM explains the results rather than calculating or inventing financial figures.

![Menu Engineering Dashboard](assets/dashboard.png)

---

## Overview

Restaurant and coffee-shop transaction datasets rarely follow the same structure.

Different POS systems use different column names, delimiters, and data formats. Many external datasets also lack ingredient costs or other information required for profitability analysis.

Menu Engineering Bot addresses these challenges through a reusable analytics workflow that:

1. Accepts external CSV datasets.
2. Detects and maps different column names.
3. Audits potential duplicate transactions.
4. Validates data quality and analytical capabilities.
5. Calculates sales and profitability metrics.
6. Estimates or assigns clearly labeled price elasticities.
7. Simulates price changes using deterministic calculations.
8. Communicates modeling limitations.
9. Generates AI-assisted business decision memos.
10. Exports reports in Markdown, plain text, and PDF.

The application is designed for food-service businesses with different data structures and levels of information completeness.

---

## Key Features

| Feature | Description |
|---|---|
| Universal CSV adapter | Converts different POS schemas into one standard format |
| Column mapping presets | Provides example Starbucks-, Blue Bottle-, and Square/Toast-style mappings |
| Manual mapping | Allows users to verify or correct detected columns |
| Mapping confidence | Distinguishes exact, alias, and uncertain column matches |
| Transaction audit | Flags identical source records and repeated transaction IDs |
| Capability-aware analysis | Enables analyses only when required information is available |
| Cost handling | Supports supplied costs, separate cost files, and assumed-cost scenarios |
| Menu engineering | Classifies products into Stars, Plowhorses, Puzzles, and Dogs |
| Price elasticity | Reports historical estimates, confidence, and assumed priors |
| Price simulation | Calculates rounded-price scenarios and estimated profit changes |
| Pricing reliability | Labels uncertain scenarios and explains why review is required |
| AI decision memo | Uses Claude to explain deterministic analysis outputs |
| PDF reporting | Generates downloadable business reports |

---

## 1. Universal Data Adapter

The application accepts different POS and restaurant sales exports without requiring the original columns to match the internal schema.

For example, an external transaction dataset may contain:

```text
transaction_date
product_detail
product_category
unit_price
transaction_qty
```

The adapter maps these to:

| Original column | Canonical field |
|---|---|
| transaction_date | date |
| product_detail | item |
| product_category | category |
| unit_price | price |
| transaction_qty | units_sold |

The internal analytical schema contains:

```text
date
item
category
price
unit_cost
units_sold
```

The application supports:

- Automatic column detection using aliases and conservative fuzzy matching.
- Manual column selection.
- Dataset-specific example mapping presets.
- Mapping-confidence feedback.
- Required-field validation.
- Optional category and unit-cost handling.

Presets are convenience templates, not guaranteed official export formats.

### CSV delimiter support

The reader supports common delimiter styles:

```text
Comma       ,
Semicolon   ;
Pipe        |
Tab         \t
```

The upload limit can be configured through `.streamlit/config.toml`. Large files may require substantial system memory because processing uses pandas.

![Column Mapping Interface](assets/column_mapping.png)

---

## 2. Transaction Auditing and Data Validation

Before the original dataset is standardized, the application audits possible duplicate records.

The audit can identify:

- Completely identical source rows.
- Missing transaction identifiers.
- Repeated transaction IDs.
- Potentially ambiguous transaction records.

It does not automatically delete matching rows.

Repeated transaction identifiers may represent legitimate multi-item orders, while different transactions may contain identical product and quantity values.

The validation layer also checks the canonical dataset before allowing analytical calculations.

### Capability-aware analysis

Not every dataset includes ingredient or unit-cost information.

When costs are unavailable, the app can still provide:

- Revenue analysis.
- Sales volume and popularity.
- Item rankings.
- Sales trends.
- Product mix analysis.
- Price variation analysis.
- Elasticity analysis when supported by the data.

Actual profitability calculations require appropriate cost information.

Users can choose to:

1. Continue without unit costs.
2. Upload a separate menu-cost CSV.
3. Run a scenario using an assumed cost percentage.

Estimated costs are explicitly labeled as assumptions rather than measured business expenses.

![Dataset Capabilities](assets/capabilities.png)

---

## 3. Demonstration Datasets

The application has been demonstrated using two different data situations.

### External Coffee-Shop Transaction Dataset

An external coffee-shop POS dataset demonstrates schema adaptation and analysis when actual unit costs are unavailable.

The evaluated dataset contains:

| Metric | Value |
|---|---:|
| Transaction rows | 149,116 |
| Unique items | 80 |
| Product categories | 9 |
| Total units sold | 214,470 |
| Recorded revenue | $698,812.33 |
| Date range | January–June 2023 |

Its source fields include transaction identifiers, transaction dates and times, quantities, store information, product categories, and selling prices.

The app successfully generates revenue analysis, item rankings, price-variation analysis, and an AI decision memo.

**Elasticity reliability in this example:**

- 15 products have historical elasticity estimates.
- All 15 estimates have low confidence.
- 37 products use category-level priors.
- 28 products use default priors.

Therefore, historical estimates and assumptions are displayed separately.

The external raw dataset is not bundled in this repository.

### Bundled Synthetic Cafe Dataset

The repository includes a synthetic cafe dataset with unit costs and selling prices.

This dataset demonstrates the complete analytical workflow, including:

- Revenue analysis.
- Contribution margin calculations.
- Menu Engineering Quadrants.
- Profit-based pricing simulations.
- Pricing reliability classifications.
- AI-generated decision memos.
- PDF reporting.

The synthetic data allows the profitability workflow to be demonstrated without claiming access to confidential restaurant financial information.

---

## 4. Menu Engineering Analysis

When complete cost information exists, the application calculates product-level financial and operational metrics.

These include:

- Selling price.
- Unit cost.
- Total sales volume.
- Total revenue.
- Contribution margin.
- Estimated contribution profit.
- Average daily units sold.
- Menu popularity.

Products are classified into traditional menu-engineering quadrants.

| Quadrant | Popularity | Margin | Interpretation |
|---|---|---|---|
| Star | High | High | Strong performers |
| Plowhorse | High | Low | Popular but margin-constrained |
| Puzzle | Low | High | Strong margin but lower popularity |
| Dog | Low | Low | Products requiring business review |

The quadrants help managers identify products that may deserve attention, promotion, repricing, or further investigation.

Classification alone does not determine whether a product should be removed or repriced.

![Menu Engineering Quadrants](assets/quadrant_chart.png)

---

## 5. Price Elasticity and Reliability

Price elasticity describes the relationship between changes in price and changes in quantity demanded.

When historical observations provide sufficient price variation, the analytical engine uses a log-log approach to estimate item-level elasticity.

```text
log(quantity) ~ log(price)
```

The engine evaluates information such as:

- Observation count.
- Distinct historical price points.
- Relative price variation.
- Valid quantity observations.
- Data sufficiency.

Historical estimates remain observational and do not establish causation.

### Elasticity sources

| Source | Meaning |
|---|---|
| estimated | Derived from observed price and quantity data |
| category_prior | Assumed from a configured product category |
| default_prior | General fallback assumption |

The application also reports confidence and supporting information, including observation counts and historical price variation.

A low-confidence historical estimate is not treated as equivalent to a reliable estimate.

### Why reliability matters

Demand can change for reasons other than selling price, including seasonality, promotions, product changes, store location, and customer behavior.

Therefore, elasticity values are used as exploratory modeling inputs unless stronger validation exists.

---

## 6. Deterministic Price Simulation

The pricing engine evaluates configured candidate price changes in Python.

For each item, simulations can consider:

- Current selling price.
- Unit cost.
- Average daily sales volume.
- Elasticity.
- Estimated demand response.
- Estimated contribution profit.

### Currency rounding

Selling prices are rounded to currency cents before demand response and profit are simulated.

The reported percentage change reflects the implemented rounded price rather than only the originally requested percentage.

For example:

```text
Original price:    $3.25
Requested change:  +15%
New price:         $3.74
Actual change:     +15.1%
```

This keeps displayed selling prices and simulation calculations consistent.

### Pricing reliability

Every simulated recommendation includes reliability information.

Possible labels include:

- Historical estimate — review required.
- Exploratory — low-confidence estimate.
- Exploratory — category assumption.
- Exploratory — default assumption.
- Exploratory — unknown reliability.

The dashboard also provides explanations for why additional business review is necessary.

**Important:** The engine selects the highest estimated profit scenario from the configured candidates. This is not proof that the scenario is the best real-world pricing decision.

![Price Recommendations](assets/price_moves.png)

---

## 7. AI Decision Memo

The application integrates the Anthropic Claude API to translate computed analytical results into a concise business memo.

The AI receives structured outputs containing information such as:

- Business and dataset metadata.
- Available analytical capabilities.
- Revenue and product summaries.
- Profitability information, when available.
- Historical elasticity counts and confidence.
- Pricing simulations and reliability information.

The LLM is instructed to:

- Use supplied calculations rather than invent figures.
- Distinguish historical estimates from assumed priors.
- Explain low-confidence results.
- Avoid profit claims when cost data is unavailable.
- Label estimated-cost scenarios.
- Provide practical recommendations with appropriate caveats.

The numerical calculation layer remains separate from the AI explanation layer.

![AI Decision Memo](assets/ai_memo.png)

### Downloadable Reports

Generated decision memos can be downloaded in three formats:

| Format | Use |
|---|---|
| Markdown (.md) | Editable, structured text |
| Plain text (.txt) | Simple text sharing |
| PDF (.pdf) | Business-ready reading and sharing |

The PDF report generator supports Markdown headings, paragraphs, basic emphasis, lists, separators, and page numbering.

Its layout is based on memo structure rather than a specific business or CSV dataset.

![Downloadable Decision Reports](assets/report_download.png)

---

## 8. Application Architecture

```text
Raw CSV / POS Export
        |
        v
Delimiter Detection
        |
        v
Automatic Mapping / Presets / Manual Mapping
        |
        v
Source Transaction Audit
        |
        v
Canonical Data Adapter
        |
        v
Data Validation & Capability Detection
        |
        v
Deterministic Analytics
        |
        +--> Revenue & Popularity
        +--> Margin & Menu Quadrants
        +--> Elasticity & Reliability
        +--> Price Simulations
        |
        v
Structured Analytical Results
        |
        v
Claude AI Explanation Layer
        |
        v
Decision Memo
        |
        +--> Markdown
        +--> Plain Text
        +--> PDF
```

### Project Structure

```text
menu-engineering-bot/
├── .streamlit/
│   └── config.toml
│
├── assets/
│   ├── dashboard.png
│   ├── column_mapping.png
│   ├── capabilities.png
│   ├── quadrant_chart.png
│   ├── price_moves.png
│   ├── ai_memo.png
│   └── report_download.png
│
├── data/
│   ├── cafe_sales.csv
│   └── menu_reference.csv
│
├── src/
│   ├── app.py
│   ├── agent.py
│   ├── analysis.py
│   ├── config.py
│   ├── data_adapter.py
│   ├── generate_data.py
│   ├── pdf_report.py
│   └── validation.py
│
├── tests/
│   ├── test_universal_pipeline.py
│   ├── test_price_rounding.py
│   ├── test_pricing_reliability.py
│   └── test_pdf_report.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Main Modules

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit interface and application workflow |
| `data_adapter.py` | CSV ingestion, presets, mapping, cost merging |
| `validation.py` | Source auditing, data validation, capability detection |
| `analysis.py` | Revenue, margin, elasticity, and price simulations |
| `config.py` | Column aliases, modeling assumptions, currencies |
| `agent.py` | AI decision memo generation and reliability context |
| `pdf_report.py` | PDF generation and Markdown layout |
| `generate_data.py` | Synthetic demonstration data utilities |

---

## 9. Installation

### Prerequisites

- Python 3.10 or newer.
- pip.
- An Anthropic API key for optional AI memo generation.

### Clone the Repository

```bash
git clone https://github.com/stephaniepatriciaans/menu-engineering-bot.git
cd menu-engineering-bot
```

### Create a Virtual Environment

On macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Start Streamlit

```bash
python3 -m streamlit run src/app.py
```

Open:

```text
http://localhost:8501
```

---

## 10. Optional Anthropic API Configuration

Numerical analysis works without an API key.

To enable AI-generated decision memos:

```bash
cp .env.example .env
```

Add your own key to `.env`:

```text
ANTHROPIC_API_KEY=your_api_key_here
```

Restart Streamlit.

Never commit a populated `.env` file to GitHub.

The AI integration requires a valid API key and may incur API usage charges.

---

## 11. Running Automated Tests

Install development dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run the tests:

```bash
python3 -m pytest -q
```

The test suite covers key areas including:

- Universal dataset adaptation.
- Missing-cost and cost-scenario behavior.
- Price-rounding calculations.
- Pricing-reliability classification.
- PDF generation.

**Latest locally reported result:**

```text
16 passed
```

This result reflects the tested local version and is not a guarantee that every possible CSV format or large dataset will work.

---

## 12. Data and Modeling Limitations

### Missing cost information

External POS datasets may not contain actual ingredient costs, labor costs, supplier terms, or other confidential business information.

The application does not fabricate these values.

Estimated-cost scenarios are labeled separately from actual cost-based calculations.

### Elasticity uncertainty

Historical price correlations do not establish causal effects.

Low-confidence elasticity estimates and category/default priors are exploratory and require validation before operational pricing decisions.

### Profit simulation

Simulated demand and contribution-profit changes depend on modeling assumptions.

They are not guaranteed financial outcomes.

### Large datasets

CSV upload limits can be configured, but in-memory pandas processing can require substantially more RAM than the source file size.

### AI-generated explanations

Claude interprets computed analytical outputs, but the resulting memo can still contain misleading wording or unsupported interpretations.

Reports should be reviewed before being used for business decisions.

---

## 13. Tech Stack

**Language:** Python

**Data Processing:** pandas, NumPy

**Application:** Streamlit

**Visualization:** Plotly

**Applied AI:** Anthropic Claude API

**Reporting:** ReportLab, Markdown, PDF

**Testing:** pytest

**Version Control:** Git, GitHub

---

## What This Project Demonstrates

### Data Engineering

Building a reusable ingestion and schema-mapping pipeline for heterogeneous POS and restaurant datasets.

### Data Analytics

Analyzing revenue, sales volume, product mix, and contribution margins.

### Pricing Analytics

Estimating observational price elasticity, evaluating uncertainty, and simulating pricing scenarios.

### Applied AI

Integrating an LLM as an explanation layer over deterministic calculations rather than relying on AI-generated arithmetic.

### Software Engineering

Organizing a modular Python application with configurable workflows, automated tests, error handling, and downloadable reports.

---

## Author

Built by [Stephanie Anshell](https://github.com/stephaniepatriciaans)

[Portfolio](https://stephaniepatriciaans.github.io/portfolio/)
