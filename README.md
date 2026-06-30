# ☕ Menu Engineering Bot

A tool that reads a cafe's sales data and tells the owner — in plain English — which
menu items to reprice, promote, or cut, backed by real price-elasticity math instead
of guesswork.

**Why this project:** I worked as a barista and in food service before pivoting into
data science. Every cafe I've worked in made pricing and menu decisions by gut feel.
This project applies the same kind of analysis I used in my data science internships
(price/demand modeling, automated reporting) to a problem I've seen up close from the
other side of the counter.

## What it does

1. **Ingests sales data** — `date, item, category, price, unit_cost, units_sold`
2. **Runs menu engineering analysis** (`src/analysis.py`, pure Python/pandas, no LLM):
   - Contribution margin and sales velocity per item
   - Price elasticity estimated from historical price variation (or a category-level
     prior when an item's price never changed)
   - Classic menu-engineering quadrant classification: **Star / Plowhorse / Puzzle / Dog**
   - Simulated profit impact of candidate price changes (-10% to +15%), picks the
     best move per item
3. **Generates a plain-English memo** (`src/agent.py`) — Claude takes the *numbers only*
   (never invents figures) and writes a short, prioritized memo a non-technical cafe
   owner could act on immediately.
4. **Interactive dashboard** (`src/app.py`, Streamlit) — upload your own CSV or use the
   bundled synthetic dataset, see the quadrant chart, full item table, recommended
   price moves, and generate the memo on demand.

## Why the math and the LLM are kept separate

This is intentional, and mirrors how I'd actually want this used in a real business:
the elasticity model and profit simulation are deterministic and auditable — you can
check every number by hand. The LLM's only job is to **explain and prioritize** those
numbers in plain language. It never generates or alters a figure. This avoids the
classic failure mode of LLM tools "hallucinating" business numbers.

## Demo data

The bundled `data/cafe_sales.csv` is **synthetic** — 180 days × 15 menu items,
generated with realistic prices, costs, day-of-week seasonality, and a known
elasticity baked in per item (see `src/generate_data.py` for the assumptions). It's
meant to demonstrate the pipeline end-to-end; swap in a real POS export with the same
column structure and it works the same way.

## Running it

```bash
git clone https://github.com/stephaniepatriciaans/menu-engineering-bot
cd menu-engineering-bot
pip install -r requirements.txt

# Generate the demo dataset (optional, already included)
python src/generate_data.py

# Set your Anthropic API key to enable memo generation
export ANTHROPIC_API_KEY=sk-...

# Run the dashboard
streamlit run src/app.py
```

Without an API key, the dashboard and all numeric analysis still work — only the
LLM-generated memo requires a key.

## Project structure

```
menu-engineering-bot/
├── data/
│   ├── cafe_sales.csv        # synthetic demo dataset (generated)
│   └── menu_reference.csv    # ground-truth menu/elasticity used to generate demo data
├── src/
│   ├── generate_data.py      # synthetic data generator
│   ├── analysis.py           # margin, velocity, elasticity, quadrant, price simulation
│   ├── agent.py               # Claude API call -> plain-English memo
│   └── app.py                 # Streamlit dashboard
├── requirements.txt
└── README.md
```

## Tech stack

Python, pandas, NumPy, Streamlit, Plotly, Anthropic API (Claude)

## Possible extensions

- Replace category-level elasticity priors with a proper experiment (e.g. a real
  cafe running a 2-week A/B price test)
- Add menu **placement/bundling** recommendations (e.g. pairing a Puzzle item with a
  Star item)
- Multi-location comparison if a cafe has several branches
- Slack/email delivery of the weekly memo automatically

---
Built by [Stephanie Anshell](https://github.com/stephaniepatriciaans) —
[portfolio](https://stephaniepatriciaans.github.io/portfolio) · [LinkedIn](https://linkedin.com/in/stephaniepatriciaanshell)
