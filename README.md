# Menu Engineering Bot

**Universal POS Analytics · Menu Engineering · Pricing Intelligence · AI Decision Support**

A Streamlit application that turns restaurant and coffee-shop sales data into **revenue insights, menu performance analysis, exploratory pricing simulations, and AI-assisted decision memos**. It supports different point-of-sale (POS) CSV layouts and adapts its analyses to the information available in each dataset.

**Design principle:** Financial calculations run in Python. The language model explains supplied results; it is not the source of financial arithmetic.

![Menu Engineering Dashboard](assets/dashboard.png)

> **Project status:** The application and its core analytical workflows are implemented and tested locally. Public deployment has not yet been completed.

## Why this project?

Restaurant POS exports are rarely standardized. Different systems use different names for dates, products, quantities, and prices, while many datasets do not provide item-level costs. Applying a single rigid analysis to every export can produce invalid or misleading financial recommendations.

Menu Engineering Bot addresses this with a **capability-aware pipeline**: standardize and validate the data, determine which analyses are supported, calculate results deterministically, then present recommendations together with their assumptions and limitations.

## Key capabilities

| Area | What it does |
|---|---|
| Universal CSV ingestion | Detects comma, semicolon, pipe, and tab delimiters; maps source fields into a canonical schema |
| Mapping assistance | Suggests mappings using aliases and conservative fuzzy matches; provides example POS-style presets and manual correction |
| Transaction audit | Flags identical source records, missing transaction IDs, and repeated IDs without deleting rows |
| Data validation | Checks dates, prices, quantities, costs, and missing required fields |
| Capability-aware dashboard | Keeps revenue and volume analytics available without cost data; gates profit-dependent functionality |
| Sales exploration | Provides revenue trends, popularity, hourly/day-of-week views, product mix, and item exploration |
| Menu engineering | Uses contribution-margin and popularity information to classify Stars, Plowhorses, Puzzles, and Dogs when cost data supports it |
| Elasticity analysis | Separates observational historical estimates from category and default assumptions; reports reliability information |
| Pricing simulation | Tests candidate price changes, rounded selling prices, and optimistic/central/pessimistic outcomes |
| Pricing strategies | Offers **Base case** and **Conservative** optimization objectives and a pricing-risk overview |
| AI decision memo | Uses Anthropic Claude to summarize computed results, with pattern-based financial claim checks and export options |
| Automated verification | Includes unit, regression, and Streamlit application-interaction tests |

## Quick start

**Requirements:** Python, pip, and a local terminal. Python 3.12 is used in the latest local test run. An Anthropic API key is **optional** and only needed for AI memo generation.

```bash
git clone https://github.com/stephaniepatriciaans/menu-engineering-bot.git
cd menu-engineering-bot
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run src/app.py
```

Open **http://localhost:8501**. The sidebar defaults to the **Full Demo Dataset — Synthetic Cafe**, so the analytical dashboard can be explored without uploading data or configuring an AI key.

On Windows, activate the virtual environment with `venv\Scripts\activate` instead.

### Optional AI memo setup

```bash
cp .env.example .env
```

Add your own key to `.env`:

```dotenv
ANTHROPIC_API_KEY=your_api_key_here
```

Restart Streamlit. Keep `.env` and other secrets out of version control. API use may incur provider charges. Without a configured key, deterministic analytics remain available and AI memo generation is disabled.

## Typical workflow

1. **Select the bundled synthetic cafe demo or upload a POS CSV.**
2. **Review column mapping.** Automatic suggestions can be corrected manually; presets are illustrative, not verified official vendor formats.
3. **Review data quality.** The source audit flags potential duplicates, and validation rejects unusable financial inputs.
4. **Choose a cost basis.** Use recorded costs, optionally merge a separate item-cost CSV, run an explicitly labeled estimated-cost scenario, or continue with non-profit analyses.
5. **Explore results.** Use date and category filters, sales trends, menu quadrants, and item-level views.
6. **Test pricing assumptions.** Compare Base case and Conservative strategies and examine worst-case risk flags.
7. **Generate an optional AI decision memo.** Review flagged numerical claims before exporting Markdown, text, or PDF.

![Column Mapping Interface](assets/column_mapping.png)

## Supported dataset structure

The adapter maps heterogeneous POS column names to these canonical fields:

| Canonical field | Purpose | Requirement |
|---|---|---|
| `date` | Transaction date | Required |
| `item` | Menu item name | Required |
| `price` | Selling price per item | Required |
| `units_sold` | Quantity sold | Required |
| `category` | Menu category | Optional; missing values become `Uncategorized` |
| `unit_cost` | Per-unit cost | Optional; required for cost-based profit analyses |
| `transaction_time` | Time of transaction | Optional; used in time-of-day analysis where available |

For example, a CSV with `transaction_date`, `product_detail`, `product_category`, `unit_price`, and `transaction_qty` can be mapped to `date`, `item`, `category`, `price`, and `units_sold`.

The adapter recognizes aliases and uses conservative fuzzy matching. **Users should verify suggested mappings** before relying on any result. CSV upload processing is in-memory using pandas; supported input sizes depend on available memory and Streamlit configuration.

### Missing costs and cost scenarios

The app does **not** treat unit price as unit cost. If cost data is absent, revenue, quantity, popularity, and supported trend analyses can still run, but cost-based profit and pricing optimization are restricted. Alternatively, the user may supply a separate menu-cost file or apply an **estimated cost percentage**, which is explicitly labeled as an assumption.

![Dataset Capabilities](assets/capabilities.png)

## Analytical methods

### Revenue and menu performance

The deterministic engine calculates sales volume, revenue, average daily sales, and—where costs are complete—contribution margin and contribution profit. It groups items into four conventional menu-engineering quadrants:

| Quadrant | Popularity | Contribution margin | Interpretation |
|---|---|---|---|
| Star | High | High | Strong performer |
| Plowhorse | High | Low | Popular, but margin-constrained |
| Puzzle | Low | High | Higher margin, lower popularity |
| Dog | Low | Low | Requires further business review |

Quadrant assignment is descriptive. It is **not** an automatic instruction to discontinue or reprice an item.

![Menu Engineering Quadrants](assets/quadrant_chart.png)

### Price elasticity and evidence quality

When sufficient historical price variation exists, the application uses a log-log price–demand relationship to derive **observational** elasticity estimates. It also reports data sufficiency and confidence indicators. Items without adequate evidence use explicit `category_prior` or `default_prior` assumptions.

```text
log(quantity) ~ log(price)
```

Observed correlation is **not** proof of a causal response to changing prices. Seasonality, promotions, store-level variation, and customer behavior can confound the relationship. Low-confidence estimates and priors should be treated as exploratory assumptions.

### Pricing simulations

The pricing engine calculates candidate price changes in Python using selling price, cost, volume, and elasticity inputs. Prices are rounded to currency cents before the simulated demand and contribution-profit impact are calculated.

The dashboard offers two optimization objectives:

- **Base case:** select the candidate with the highest simulated contribution-profit outcome under the central elasticity estimate.
- **Conservative:** select the candidate with the strongest simulated worst-case result among tested candidates.

Simulations include sensitivity to elasticity assumptions and a pricing-risk overview. **Optimistic, central, and pessimistic scenarios are modeled outcomes, not statistically validated prediction intervals or guaranteed business results.**

![Price Recommendations](assets/price_moves.png)

## AI Decision Memo and financial safeguards

The optional Claude integration receives structured analytical outputs and supporting business metadata. Python remains responsible for calculations; the model provides explanatory narrative and suggested questions or actions for review.

The memo workflow also includes a **limited, pattern-based audit** that flags some unsupported dollar amounts and mismatches in explicitly stated item prices, recommended prices, profit impacts, and scenario values. These are review flags, **not a guarantee that the memo is factually correct**. A memo is invalidated when its underlying inputs or relevant pricing results change, preventing a stale explanation from being reused inadvertently.

Exports are available in **Markdown (`.md`)**, **plain text (`.txt`)**, and **PDF (`.pdf`)**.

![AI Decision Memo](assets/ai_memo.png)

![Downloadable Decision Reports](assets/report_download.png)

## Architecture

```text
POS CSV / Synthetic Demo
         |
         v
CSV Parsing + Column Mapping
         |
         v
Source Transaction Audit
         |
         v
Canonical Data Adapter
         |
         v
Validation + Capability Detection
         |
         +--------------------+
         |                    |
         v                    v
Sales/Revenue Analytics   Cost-Aware Analytics
         |                    |
         |                    +--> Margins and Menu Quadrants
         |                    +--> Elasticity / Assumptions
         |                    +--> Pricing Scenarios / Risk
         +--------------------+
                              |
                              v
                  Structured Python Results
                              |
                              v
                     Streamlit Dashboard
                              |
                       Optional Claude
                              |
                              v
                   Memo + Financial Audit
                              |
                    Markdown / TXT / PDF
```

**Primary modules:**

| Path | Responsibility |
|---|---|
| `src/app.py` | Streamlit entry point and workflow orchestration |
| `src/data_adapter.py` | CSV reading, column mapping, cost-file matching |
| `src/validation.py` | Data-quality checks, transaction auditing, capability detection |
| `src/analysis.py` | Item summaries, elasticity handling, pricing calculations |
| `src/model_evaluation.py` | Chronological forecasting evaluation and reports |
| `src/dashboard_utils.py` | Time-series and aggregated dashboard analytics |
| `src/agent.py` | AI memo generation |
| `src/memo_validation.py` | Pattern-based checks of memo financial claims |
| `src/memo_export.py`, `src/pdf_report.py` | Memo formatting and PDF rendering |
| `src/ui/` | Sidebar, filters, components, visual styling, and dashboard sections |
| `tests/` | Automated unit, regression, and Streamlit interaction tests |
| `data/cafe_sales.csv` | Bundled synthetic demonstration sales |

## Demonstration data

**Bundled synthetic cafe.** The default dataset contains example selling prices, costs, and transaction quantities, allowing the full contribution-margin and pricing workflow to be demonstrated without disclosing private business data.

**External coffee-shop example.** The project has also been used with an external POS-style coffee-shop dataset to exercise schema adaptation and no-cost-data workflows. The raw external dataset is **not bundled in the repository**. Dataset-specific results should be interpreted as illustrative evaluations, not validated business performance claims.

## Tests and code quality

The project uses `pytest`, Streamlit's `AppTest`, and Ruff. For development dependencies, if the repository includes `requirements-dev.txt`, install it with:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run the test suite and lint checks:

```bash
PYTHONPATH=src python3 -m pytest -q
python3 -m ruff check src tests
python3 -m compileall -q src tests
```

For a coverage report (with `pytest-cov` installed):

```bash
PYTHONPATH=src python3 -m pytest --cov=src --cov-report=term-missing -q
```

**Latest locally reported results:** **266 passing tests** and **89% overall statement coverage** (coverage measured at an earlier nearby test milestone; rerun for the latest exact figure). The test suite includes data ingestion, financial validations, pricing regression checks, AI memo auditing, dashboard startup, filter interactions, and memo invalidation when changing pricing strategies.

Passing tests and high statement coverage do not establish production readiness, economic validity, or support for every possible vendor export.

## Limitations and responsible use

- **Not a causal pricing model.** Historical elasticity estimates are observational and may be confounded by promotions, seasonality, and other changes.
- **Missing costs are meaningful.** Without complete costs, the app does not present actual cost-based contribution-profit results; assumed-cost scenarios are labeled as such.
- **Modeled risk is not real-world certainty.** Worst-case scenarios depend on configured uncertainty and assumptions, not a statistically certified forecast interval.
- **Transaction auditing is conservative.** Duplicate-like records are flagged but not automatically removed, since repeated IDs can represent multi-item orders.
- **AI claims still require review.** The memo audit only covers recognized claim patterns and does not verify every numerical or qualitative assertion.
- **Large uploads consume memory.** Dataset size and processing speed depend on the runtime environment.
- **Public deployment remains pending.** The latest results reflect local testing.

## Tech stack

**Python · pandas · NumPy · Streamlit · Plotly · Altair · Anthropic Claude API · ReportLab · pytest · pytest-cov · Ruff · Git/GitHub**

## What this project demonstrates

This project combines **data engineering** (heterogeneous POS ingestion), **data analytics** (revenue and product mix), **applied statistical modeling** (observational elasticity and forecast evaluation), **pricing analytics** (scenario-based optimization), **AI engineering** (LLM explanations grounded in deterministic outputs), and **software engineering** (modular code, defensive validation, integration tests, and report exports).

## Author

Built by [Stephanie Anshell](https://github.com/stephaniepatriciaans) · [Portfolio](https://stephaniepatriciaans.github.io/portfolio/)