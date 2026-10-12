"""Integration tests for the menu-engineering analysis workflow"""

import json
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent import build_user_prompt
from analysis import build_item_summary, recommend_price_moves
from validation import determine_capabilities, validate_sales_df


def test_complete_csv_to_ai_prompt_workflow():
    """A valid CSV should flow through analytics into the AI prompt."""

    # Simulate a restaurant-uploaded CSV.
    csv_content = """date,item,category,price,units_sold,unit_cost
2026-01-05,Latte,Coffee,5.00,10,2.00
2026-01-06,Latte,Coffee,5.00,12,2.00
2026-01-07,Latte,Coffee,5.50,9,2.00
2026-01-05,Tea,Tea,3.00,8,1.00
2026-01-06,Tea,Tea,3.00,10,1.00
2026-01-07,Tea,Tea,3.00,7,1.00
"""

    raw = pd.read_csv(StringIO(csv_content))

    # Step 1: Validate uploaded data.
    validated, errors, _warnings = validate_sales_df(raw)

    assert errors == []
    assert validated is not None
    assert len(validated) == 6

    # Step 2: Determine supported analyses.
    capabilities = determine_capabilities(validated)

    assert capabilities["revenue_analysis"] is True
    assert capabilities["profit_analysis"] is True
    assert capabilities["price_optimization"] is True

    # Step 3: Build deterministic item summaries.
    summary = build_item_summary(validated)

    assert len(summary) == 2
    assert set(summary["item"]) == {"Latte", "Tea"}

    records = summary.set_index("item").to_dict(orient="index")

    # Latte: 10 + 12 + 9 = 31 units.
    assert records["Latte"]["total_units_sold"] == (
        pytest.approx(31.0)
    )

    # Latte revenue: 10*5 + 12*5 + 9*5.5 = 159.5
    assert records["Latte"]["total_revenue"] == (
        pytest.approx(159.5)
    )

    # Latte contribution profit: 159.5 - 31*2 = 97.5
    assert records["Latte"]["total_profit"] == (
        pytest.approx(97.5)
    )

    # Tea: 25 units at $3, cost $1 per unit.
    assert records["Tea"]["total_revenue"] == (
        pytest.approx(75.0)
    )
    assert records["Tea"]["total_profit"] == (
        pytest.approx(50.0)
    )

    # Step 4: Generate deterministic price simulations.
    moves = recommend_price_moves(summary)

    assert not moves.empty
    assert "daily_profit_delta" in moves.columns
    assert "item" in moves.columns

    # Step 5: Prepare data for the AI memo.
    prompt = build_user_prompt(
        summary,
        moves,
        metadata={
            "business_name": "Integration Test Cafe",
            "dataset_name": "Synthetic January Sales",
            "currency": "USD",
            "cost_basis": "actual",
            "cost_is_assumption": False,
        },
        capabilities=capabilities,
    )

    assert "Integration Test Cafe" in prompt
    assert "Latte" in prompt
    assert "Tea" in prompt

    # Verify the actual numbers sent to Claude,
    # rather than checking only whether words appear.
    item_section = prompt.split(
        "ITEM SUMMARY (deterministic calculations):\n",
        1,
    )[1].split("\n\n", 1)[0]

    prompt_records = json.loads(item_section)

    prompt_by_item = {
        record["item"]: record
        for record in prompt_records
    }

    assert prompt_by_item["Latte"]["total_revenue"] == (
        pytest.approx(159.5)
    )
    assert prompt_by_item["Latte"]["total_profit"] == (
        pytest.approx(97.5)
    )
    assert prompt_by_item["Tea"]["total_profit"] == (
        pytest.approx(50.0)
    )
