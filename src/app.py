"""Streamlit front end for the universal Menu Engineering Bot."""

from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(__file__))

from analysis import build_item_summary, load_sales, recommend_price_moves
from config import CANONICAL_FIELDS, CURRENCY_CONFIG, format_currency
from data_adapter import (
    NOT_AVAILABLE,
    adapt_to_canonical,
    apply_estimated_cost_percentage,
    detect_column_mapping,
    merge_cost_reference,
    read_delimited_csv,
    validate_mapping,
)
from validation import determine_capabilities, validate_sales_df

st.set_page_config(page_title="Menu Engineering Bot", page_icon="📊", layout="wide")


def mapping_selectors(raw_df: pd.DataFrame, prefix: str = "sales") -> dict[str, str | None]:
    """Render manual mapping controls with automatic aliases preselected."""
    detected = detect_column_mapping(raw_df.columns)
    options = [NOT_AVAILABLE] + [str(col) for col in raw_df.columns]
    labels = {
        "date": "Date (required)",
        "item": "Item (required)",
        "category": "Category (optional)",
        "price": "Price (required)",
        "unit_cost": "Unit Cost (optional)",
        "units_sold": "Units Sold (required)",
    }
    result: dict[str, str | None] = {}
    columns = st.columns(3)
    for idx, field in enumerate(CANONICAL_FIELDS):
        preselected = detected.get(field) or NOT_AVAILABLE
        choice = columns[idx % 3].selectbox(
            labels[field],
            options,
            index=options.index(preselected) if preselected in options else 0,
            key=f"{prefix}_map_{field}",
        )
        result[field] = None if choice == NOT_AVAILABLE else choice
    return result


def capability_line(ok: bool, label: str, reason: str = "") -> str:
    icon = "✓" if ok else "✗"
    suffix = f" — {reason}" if reason else ""
    return f"{icon} {label}{suffix}"


def display_item_table(summary: pd.DataFrame, currency: str, has_cost: bool) -> pd.DataFrame:
    table = summary.copy()
    table["price"] = table["price"].map(lambda x: format_currency(x, currency))
    table["total_revenue"] = table["total_revenue"].map(lambda x: format_currency(x, currency))
    if has_cost:
        table["unit_cost"] = table["unit_cost"].map(lambda x: format_currency(x, currency))
        table["contribution_margin_amount"] = table["contribution_margin_amount"].map(lambda x: format_currency(x, currency))
        table["total_profit"] = table["total_profit"].map(lambda x: format_currency(x, currency))
    return table


def display_moves_table(moves: pd.DataFrame, currency: str) -> pd.DataFrame:
    table = moves.copy()
    for col in ["old_price", "new_price", "old_daily_profit_est", "new_daily_profit_est", "daily_profit_delta"]:
        if col in table:
            table[col] = table[col].map(lambda x: format_currency(x, currency))
    return table


st.title("Menu Engineering Bot")
st.caption(
    "Universal menu/POS data adapter + deterministic pricing analytics + AI explanation. "
    "The numerical engine never delegates calculations to the LLM."
)

with st.sidebar:
    st.header("Business settings")
    business_name = st.text_input("Business name", value="My Food-Service Business")
    dataset_name = st.text_input("Dataset name", value="Menu Sales Dataset")
    currency = st.selectbox("Currency", list(CURRENCY_CONFIG.keys()), index=0)

    st.header("Price simulation")
    max_decrease = st.slider("Maximum price decrease", 0, 30, 10, 5, format="-%d%%")
    max_increase = st.slider("Maximum price increase", 0, 30, 15, 5, format="+%d%%")

    st.header("1. Load dataset")
    source = st.radio(
        "Data source",
        ["Full Demo Dataset — Synthetic Cafe", "Upload my own CSV"],
    )
    uploaded = None
    if source == "Upload my own CSV":
        uploaded = st.file_uploader("Upload sales/POS CSV", type=["csv"])

raw_df: pd.DataFrame | None = None
if source == "Full Demo Dataset — Synthetic Cafe":
    demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "cafe_sales.csv")
    raw_df = load_sales(demo_path)
    mapping = {field: field for field in CANONICAL_FIELDS}
    business_name = business_name if business_name != "My Food-Service Business" else "Synthetic Cafe"
    dataset_name = dataset_name if dataset_name != "Menu Sales Dataset" else "Full Demo Dataset — Synthetic Cafe"
    st.info("Using the bundled synthetic dataset with complete price, cost, and quantity fields.")
elif uploaded is not None:
    try:
        uploaded.seek(0)
        raw_df = read_delimited_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read the CSV: {exc}")
        st.stop()
else:
    st.info("Upload a CSV to begin. You do not need to rename its columns first.")
    st.stop()

st.header("2. Detect / map columns")
if source == "Upload my own CSV":
    st.write("Automatic detection has preselected likely matches. Correct any mapping that is wrong.")
    with st.expander("Preview raw columns", expanded=False):
        st.dataframe(raw_df.head(10), use_container_width=True)
    mapping = mapping_selectors(raw_df)
else:
    st.success("Bundled demo columns already match the canonical schema.")

mapping_errors = validate_mapping(mapping, raw_df.columns)
if mapping_errors:
    for error in mapping_errors:
        st.error(error)
    st.stop()

try:
    canonical_df, adapter_warnings = adapt_to_canonical(raw_df, mapping)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

for warning in adapter_warnings:
    st.warning(warning)

cost_basis = "provided_cost_column" if canonical_df["unit_cost"].notna().all() else "unavailable"
cost_is_assumption = False

if not canonical_df["unit_cost"].notna().all():
    st.subheader("Optional cost data")
    st.write(
        "Unit cost is not fully available. Do not add a cost source unless you actually have one or intentionally want a scenario assumption."
    )
    cost_option = st.radio(
        "Cost handling",
        [
            "Continue without unit cost",
            "Upload a separate menu-cost CSV",
            "Scenario analysis using estimated cost percentage",
        ],
    )

    if cost_option == "Upload a separate menu-cost CSV":
        cost_upload = st.file_uploader("Upload menu-cost CSV", type=["csv"], key="cost_upload")
        if cost_upload is not None:
            try:
                cost_upload.seek(0)
                raw_cost_df = read_delimited_csv(cost_upload)
                cost_detected = detect_column_mapping(raw_cost_df.columns)
                cost_options = [NOT_AVAILABLE] + [str(c) for c in raw_cost_df.columns]
                c1, c2 = st.columns(2)
                item_default = cost_detected.get("item") or NOT_AVAILABLE
                cost_default = cost_detected.get("unit_cost") or NOT_AVAILABLE
                cost_item_col = c1.selectbox(
                    "Cost file: Item",
                    cost_options,
                    index=cost_options.index(item_default) if item_default in cost_options else 0,
                )
                cost_value_col = c2.selectbox(
                    "Cost file: Unit Cost",
                    cost_options,
                    index=cost_options.index(cost_default) if cost_default in cost_options else 0,
                )
                if cost_item_col != NOT_AVAILABLE and cost_value_col != NOT_AVAILABLE:
                    canonical_df, cost_warnings = merge_cost_reference(
                        canonical_df, raw_cost_df, cost_item_col, cost_value_col
                    )
                    cost_basis = "separate_menu_cost_csv"
                    for warning in cost_warnings:
                        st.warning(warning)
            except Exception as exc:
                st.error(f"Could not use the cost CSV: {exc}")

    elif cost_option == "Scenario analysis using estimated cost percentage":
        estimated_pct = st.slider("Estimated cost as % of price", 5, 95, 30, 1)
        canonical_df = apply_estimated_cost_percentage(canonical_df, estimated_pct / 100)
        cost_basis = f"assumption_{estimated_pct}_percent_of_price"
        cost_is_assumption = True
        st.warning(
            f"Scenario assumption enabled: unit cost is modeled as {estimated_pct}% of selling price. "
            "These are not actual business costs."
        )

st.header("3. Validate dataset")
df, errors, validation_warnings = validate_sales_df(canonical_df)
for warning in validation_warnings:
    st.warning(warning)
if errors or df is None:
    for error in errors:
        st.error(error)
    st.stop()
st.success("Dataset validated in the canonical schema.")

capabilities = determine_capabilities(df)
summary = build_item_summary(df)
# This is stricter than simply seeing multiple prices: it reflects whether the
# estimator actually accepted at least one item-level historical estimate.
capabilities["historical_elasticity_estimation"] = bool(
    not summary.empty and (summary["elasticity_source"] == "estimated").any()
)

st.subheader("Dataset capabilities")
capability_text = [
    capability_line(capabilities["revenue_analysis"], "Revenue analysis"),
    capability_line(capabilities["popularity_analysis"], "Popularity analysis"),
    capability_line(capabilities["sales_trend_analysis"], "Sales trend analysis"),
    capability_line(capabilities["price_variation_analysis"], "Price variation analysis"),
    capability_line(
        capabilities["historical_elasticity_estimation"],
        "Historical elasticity estimation",
        "insufficient price variation; labeled priors are shown instead" if not capabilities["historical_elasticity_estimation"] else "",
    ),
    capability_line(
        capabilities["profit_analysis"],
        "Profit analysis",
        "unit cost missing or incomplete" if not capabilities["profit_analysis"] else ("cost is a scenario assumption" if cost_is_assumption else ""),
    ),
    capability_line(
        capabilities["menu_engineering_quadrants"],
        "Menu Engineering Quadrants",
        "unit cost missing or incomplete" if not capabilities["menu_engineering_quadrants"] else "",
    ),
    capability_line(
        capabilities["price_optimization"],
        "Profit-based price recommendations",
        "unit cost missing or incomplete" if not capabilities["price_optimization"] else ("scenario only" if cost_is_assumption else ""),
    ),
]
st.code("\n".join(capability_text), language=None)

st.header("4. Dataset overview")
revenue_total = float((df["price"] * df["units_sold"]).sum())
metric_cols = st.columns(6)
metric_cols[0].metric("Rows", f"{len(df):,}")
metric_cols[1].metric("Unique Items", f"{df['item'].nunique():,}")
metric_cols[2].metric("Categories", f"{df['category'].nunique():,}")
metric_cols[3].metric("Total Units", f"{df['units_sold'].sum():,.0f}")
metric_cols[4].metric("Revenue", format_currency(revenue_total, currency))
metric_cols[5].metric("Date Range", f"{df['date'].min().date()} → {df['date'].max().date()}")

st.header("5. Run available analyses")
analysis_tabs = st.tabs(["Revenue & Popularity", "Elasticity Reliability", "Menu Quadrants", "Item Detail"])

with analysis_tabs[0]:
    left, right = st.columns(2)
    top_volume = summary.nlargest(min(15, len(summary)), "total_units_sold")
    left.plotly_chart(
        px.bar(top_volume, x="total_units_sold", y="item", orientation="h", title="Top items by units sold"),
        use_container_width=True,
    )
    daily = df.assign(revenue=df["price"] * df["units_sold"]).groupby("date", as_index=False).agg(
        revenue=("revenue", "sum"), units_sold=("units_sold", "sum")
    )
    right.plotly_chart(
        px.line(daily, x="date", y="revenue", title=f"Daily revenue ({currency})"),
        use_container_width=True,
    )

with analysis_tabs[1]:
    st.caption(
        "'estimated' means the item had enough historical price/quantity variation for an item-level log-log estimate. "
        "'category_prior' and 'default_prior' are labeled assumptions, not measured demand curves."
    )
    st.dataframe(
        summary[[
            "item", "category", "elasticity", "elasticity_source", "elasticity_confidence",
            "price_points", "observations", "price_variation_%",
        ]],
        use_container_width=True,
        hide_index=True,
    )

with analysis_tabs[2]:
    if capabilities["menu_engineering_quadrants"]:
        fig = px.scatter(
            summary,
            x="avg_daily_units",
            y="contribution_margin_%",
            color="quadrant",
            size="total_profit",
            hover_name="item",
            hover_data=["category", "price", "elasticity_source", "elasticity_confidence"],
            labels={"avg_daily_units": "Avg Daily Units Sold", "contribution_margin_%": "Contribution Margin %"},
        )
        fig.add_vline(x=summary["avg_daily_units"].median(), line_dash="dash", line_color="gray")
        fig.add_hline(y=summary["contribution_margin_%"].median(), line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
        if cost_is_assumption:
            st.warning("Quadrants use the estimated cost-percentage scenario, not actual unit costs.")
    else:
        st.info("Menu quadrants require complete unit cost data because margin is one axis of the classification.")

with analysis_tabs[3]:
    has_cost = capabilities["profit_analysis"]
    columns = ["item", "category", "price", "avg_daily_units", "total_units_sold", "total_revenue"]
    if has_cost:
        columns += ["unit_cost", "contribution_margin_amount", "contribution_margin_%", "total_profit", "quadrant"]
    columns += ["elasticity", "elasticity_source", "elasticity_confidence"]
    st.dataframe(display_item_table(summary[columns], currency, has_cost), use_container_width=True, hide_index=True)

st.header("6. Price recommendations")
price_changes = [value / 100 for value in range(-max_decrease, max_increase + 1, 5)]
if 0.0 not in price_changes:
    price_changes.append(0.0)
moves = recommend_price_moves(summary, price_changes) if capabilities["price_optimization"] else pd.DataFrame()

if moves.empty:
    st.info(
        "Profit-based price recommendations are disabled because complete unit cost data is unavailable. "
        "The app will not fabricate cost or profit figures."
    )
else:
    st.caption(
        f"Candidate moves are tested from -{max_decrease}% to +{max_increase}% in 5% steps. "
        "Demand response uses historical estimates when reliable enough, otherwise a clearly labeled prior."
    )
    if cost_is_assumption:
        st.warning("These price/profit recommendations are scenario results based on your estimated cost percentage.")
    move_columns = [
        "item", "old_price", "new_price", "pct_change_recommended", "daily_profit_delta",
        "quadrant", "elasticity_source", "elasticity_confidence",
    ]
    st.dataframe(display_moves_table(moves[move_columns], currency), use_container_width=True, hide_index=True)

st.header("7. Generate AI decision memo")
metadata = {
    "business_name": business_name,
    "dataset_name": dataset_name,
    "currency": currency,
    "cost_basis": cost_basis,
    "cost_is_assumption": cost_is_assumption,
    "available_analysis": [name for name, available in capabilities.items() if available],
}

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning("No ANTHROPIC_API_KEY is configured. All deterministic analytics still work; only memo generation is disabled.")
else:
    if st.button("Generate decision memo", type="primary"):
        try:
            from agent import generate_menu_memo

            with st.spinner("Generating memo from computed results..."):
                memo = generate_menu_memo(summary, moves, metadata=metadata, capabilities=capabilities)
            st.markdown("### Decision Memo")
            st.markdown(memo)
        except Exception as exc:
            st.error("Could not generate the AI memo. The analytics above are unaffected.")
            st.code(str(exc))
