"""Synthetic tests: no confidential store data used."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from analytics.monthly_business_insights import build_monthly_business_insights


def _rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"period_start": date(2026, 8, 1), "Menu Code": "A", "Menu": "Latte", "Menu Category": "BEVERAGE", "Menu Category Detail": "COFFEE", "Qty": 10, "Net Sales Total": 1000},
        {"period_start": date(2026, 8, 1), "Menu Code": "X", "Menu": "Promo", "Menu Category": "FOOD", "Menu Category Detail": "PROMO", "Qty": 120, "Net Sales Total": 0},
        {"period_start": date(2026, 9, 1), "Menu Code": "A", "Menu": "Latte", "Menu Category": "BEVERAGE", "Menu Category Detail": "COFFEE", "Qty": 15, "Net Sales Total": 1500},
        {"period_start": date(2026, 9, 1), "Menu Code": "B", "Menu": "Tea", "Menu Category": "BEVERAGE", "Menu Category Detail": "TEA", "Qty": 20, "Net Sales Total": 2000},
        {"period_start": date(2026, 9, 1), "Menu Code": "X", "Menu": "Promo", "Menu Category": "FOOD", "Menu Category Detail": "PROMO", "Qty": 130, "Net Sales Total": 0},
    ])


def test_contiguous_growth_and_no_invented_cause():
    results = build_monthly_business_insights(_rows())
    growth = results[0]
    assert "Sep 2026" in growth.observation
    assert "250.0%" in growth.observation  # 3,500 vs 1,000
    assert "+35" in growth.observation
    assert "before attributing a cause" in growth.next_step


def test_high_volume_zero_revenue_is_flagged_not_called_free():
    results = build_monthly_business_insights(_rows())
    flagged = next(i for i in results if i.kind == "caution" and "High volume" in i.heading)
    assert "Promo" in flagged.observation
    assert "250" in flagged.observation
    assert "free products" in flagged.next_step


def test_candidate_revenue_leader_preserves_identity():
    results = build_monthly_business_insights(_rows())
    leader = next(i for i in results if i.heading == "Product revenue leader")
    assert "Latte" in leader.observation
    assert "2,500" in leader.observation
    assert "standalone" in leader.next_step


def test_missing_immediately_previous_month_does_not_invent_mom():
    rows = _rows()
    rows.loc[rows["period_start"] == date(2026, 8, 1), "period_start"] = date(2026, 7, 1)
    results = build_monthly_business_insights(rows)
    assert "No report" in results[0].observation
    assert not any("250.0%" in i.observation for i in results)


def test_indonesian_language_and_month_label():
    results = build_monthly_business_insights(_rows(), language="id")
    assert results[0].heading == "Perubahan penjualan bulanan"
    assert "September 2026" in results[0].observation
    assert "Agustus 2026" in results[0].observation


def test_no_cost_or_profit_inferred():
    results = build_monthly_business_insights(_rows())
    assert "cannot establish profit" in results[-1].observation


def test_bad_language_is_rejected():
    with pytest.raises(ValueError, match="language"):
        build_monthly_business_insights(_rows(), language="fr")


def test_empty_rows_returns_no_insights():
    assert build_monthly_business_insights(_rows().iloc[:0]) == []
