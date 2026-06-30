"""
app.py

Streamlit front end for the Menu Engineering Bot.

Run with: streamlit run src/app.py

Flow:
1. User uploads a sales CSV (date, item, category, price, unit_cost,
   units_sold) or uses the bundled demo dataset.
2. analysis.py computes margin, velocity, quadrant, and price-move
   recommendations -- all deterministic, no LLM involved.
3. User clicks "Generate Memo" and agent.py calls Claude to turn the numbers
   into a plain-English memo.
"""

import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px

sys.path.append(os.path.dirname(__file__))
from analysis import load_sales, build_item_summary, recommend_price_moves

st.set_page_config(page_title="Menu Engineering Bot", page_icon="☕", layout="wide")

st.title("☕ Menu Engineering Bot")
st.caption(
    "Upload a cafe sales CSV and get data-driven price/menu recommendations, "
    "narrated in plain English. Built by Stephanie Anshell."
)

REQUIRED_COLS = {"date", "item", "category", "price", "unit_cost", "units_sold"}

with st.sidebar:
    st.header("1. Load data")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"])
    use_demo = st.checkbox("Use bundled demo dataset (synthetic cafe data)", value=uploaded is None)

    st.markdown("---")
    st.markdown(
        "**Expected columns:** `date, item, category, price, unit_cost, units_sold`\n\n"
        "Don't have this format? You can still try the demo dataset to see how it works."
    )

# --- Load data ---
df = None
if uploaded is not None and not use_demo:
    try:
        df = pd.read_csv(uploaded, parse_dates=["date"])
        missing = REQUIRED_COLS - set(df.columns)
        if missing:
            st.error(f"Missing required columns: {missing}")
            df = None
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
elif use_demo:
    demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "cafe_sales.csv")
    df = load_sales(demo_path)
    st.info("Using bundled synthetic demo dataset (180 days, 15 items).")

if df is None:
    st.warning("Upload a CSV or check 'Use bundled demo dataset' to get started.")
    st.stop()

# --- Run analysis ---
summary = build_item_summary(df)
moves = recommend_price_moves(summary)

st.header("2. Menu Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Items", len(summary))
col2.metric("Total Revenue", f"${summary['total_revenue'].sum():,.0f}")
col3.metric("Total Profit", f"${summary['total_profit'].sum():,.0f}")
col4.metric("Avg Margin %", f"{summary['contribution_margin_%'].mean():.1f}%")

tab1, tab2, tab3 = st.tabs(["Menu Quadrants", "Item Detail", "Recommended Price Moves"])

with tab1:
    st.subheader("Margin vs. Popularity")
    st.caption(
        "Stars = high margin & popular. Plowhorses = popular but lower margin. "
        "Puzzles = high margin but underordered. Dogs = low margin & low popularity."
    )
    fig = px.scatter(
        summary,
        x="avg_daily_units",
        y="contribution_margin_%",
        color="quadrant",
        size="total_profit",
        hover_name="item",
        hover_data=["category", "price", "total_profit"],
        labels={"avg_daily_units": "Avg Daily Units Sold", "contribution_margin_%": "Contribution Margin %"},
    )
    fig.add_vline(x=summary["avg_daily_units"].median(), line_dash="dash", line_color="gray")
    fig.add_hline(y=summary["contribution_margin_%"].median(), line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Full Item Summary")
    st.dataframe(
        summary[
            ["item", "category", "price", "unit_cost", "contribution_margin_%",
             "avg_daily_units", "total_revenue", "total_profit", "quadrant"]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader("Numerically Optimal Price Moves")
    st.caption(
        "Each item's price was tested at -10% to +15% and the best estimated "
        "daily profit outcome is shown. Estimates use elasticity fit from the "
        "data where price varied, or a category-level estimate otherwise."
    )
    st.dataframe(
        moves[
            ["item", "old_price", "new_price", "pct_change_recommended",
             "daily_profit_delta", "quadrant"]
        ].rename(columns={"daily_profit_delta": "est_daily_profit_change_$"}),
        use_container_width=True,
        hide_index=True,
    )

st.header("3. Generate Menu Memo")
st.caption("Uses Claude to turn the numbers above into a short, plain-English memo you could hand to a cafe owner.")

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning(
        "No `ANTHROPIC_API_KEY` found in environment. Set it before running "
        "`streamlit run src/app.py` to enable memo generation, e.g.\n\n"
        "`export ANTHROPIC_API_KEY=sk-...`"
    )
else:
    if st.button("✨ Generate Memo", type="primary"):
        with st.spinner("Writing memo..."):
            from agent import generate_menu_memo
            memo = generate_menu_memo(summary, moves)
            st.markdown("### Memo")
            st.markdown(memo)
