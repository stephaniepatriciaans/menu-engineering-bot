from __future__ import annotations

import os
import sys
import unittest

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from analysis import build_item_summary, recommend_price_moves
from data_adapter import adapt_to_canonical, apply_estimated_cost_percentage, detect_column_mapping
from validation import determine_capabilities, validate_sales_df


class UniversalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dates = pd.date_range("2026-01-01", periods=12, freq="D")

    def _original_format(self) -> pd.DataFrame:
        rows = []
        prices = [4.00, 4.20, 4.40] * 4
        for i, day in enumerate(self.dates):
            rows.append({
                "date": day,
                "item": "Latte",
                "category": "Coffee",
                "price": prices[i],
                "unit_cost": 1.20,
                "units_sold": max(20, 50 - i),
            })
        return pd.DataFrame(rows)

    def test_dataset_a_original_format_full_analysis(self) -> None:
        raw = self._original_format()
        mapping = detect_column_mapping(raw.columns)
        canonical, _warnings = adapt_to_canonical(raw, mapping)
        cleaned, errors, _warnings = validate_sales_df(canonical)
        self.assertFalse(errors)
        self.assertIsNotNone(cleaned)
        capabilities = determine_capabilities(cleaned)
        self.assertTrue(capabilities["profit_analysis"])
        summary = build_item_summary(cleaned)
        self.assertIn(summary.loc[0, "quadrant"], {"Star", "Plowhorse", "Puzzle", "Dog"})
        moves = recommend_price_moves(summary)
        self.assertFalse(moves.empty)

    def test_dataset_b_aliases_auto_map(self) -> None:
        raw = self._original_format().rename(columns={
            "date": "transaction_date",
            "item": "product_detail",
            "category": "product_category",
            "price": "unit_price",
            "unit_cost": "cost",
            "units_sold": "transaction_qty",
        })
        mapping = detect_column_mapping(raw.columns)
        expected = {
            "date": "transaction_date",
            "item": "product_detail",
            "category": "product_category",
            "price": "unit_price",
            "unit_cost": "cost",
            "units_sold": "transaction_qty",
            "transaction_time": None,
        }
        self.assertEqual(mapping, expected)
        canonical, _warnings = adapt_to_canonical(raw, mapping)
        cleaned, errors, _warnings = validate_sales_df(canonical)
        self.assertFalse(errors)
        self.assertEqual(list(cleaned.columns), ["date", "item", "category", "price", "unit_cost", "units_sold", "transaction_time"])

    def test_dataset_c_no_unit_cost_disables_profit_gracefully(self) -> None:
        raw = self._original_format().drop(columns="unit_cost").rename(columns={
            "date": "transaction_date",
            "item": "product_name",
            "category": "product_category",
            "price": "unit_price",
            "units_sold": "quantity",
        })
        mapping = detect_column_mapping(raw.columns)
        canonical, warnings = adapt_to_canonical(raw, mapping)
        self.assertTrue(any("Unit cost" in warning for warning in warnings))
        cleaned, errors, _warnings = validate_sales_df(canonical)
        self.assertFalse(errors)
        capabilities = determine_capabilities(cleaned)
        self.assertFalse(capabilities["profit_analysis"])
        self.assertFalse(capabilities["menu_engineering_quadrants"])
        summary = build_item_summary(cleaned)
        self.assertTrue(summary["total_profit"].isna().all())
        self.assertTrue(recommend_price_moves(summary).empty)

    def test_dataset_d_unknown_category_uses_default_prior(self) -> None:
        raw = pd.DataFrame({
            "Date": self.dates,
            "Menu Item": ["Berry Refresher"] * len(self.dates),
            "Type": ["Refreshers"] * len(self.dates),
            "Selling Price": [5.0] * len(self.dates),
            "COGS": [1.2] * len(self.dates),
            "Qty": [30] * len(self.dates),
        })
        mapping = detect_column_mapping(raw.columns)
        canonical, _warnings = adapt_to_canonical(raw, mapping)
        cleaned, errors, _warnings = validate_sales_df(canonical)
        self.assertFalse(errors)
        summary = build_item_summary(cleaned)
        self.assertEqual(summary.loc[0, "elasticity_source"], "default_prior")
        self.assertEqual(summary.loc[0, "elasticity_confidence"], "Prior")

    def test_explicit_estimated_cost_scenario_enables_profit(self) -> None:
        raw = self._original_format().drop(columns="unit_cost")
        mapping = detect_column_mapping(raw.columns)
        canonical, _warnings = adapt_to_canonical(raw, mapping)
        scenario = apply_estimated_cost_percentage(canonical, 0.30)
        cleaned, errors, _warnings = validate_sales_df(scenario)
        self.assertFalse(errors)
        self.assertTrue(determine_capabilities(cleaned)["profit_analysis"])

    
    def test_adapter_preserves_transaction_time(self):
        raw = pd.DataFrame({
            "transaction_date": ["2023-03-06"],
            "transaction_time": ["14:35:20"],
            "product_detail": ["Latte"],
            "product_category": ["Coffee"],
            "unit_price": [5.0],
            "transaction_qty": [2],
        })

        adapted, warnings = adapt_to_canonical(raw)

        assert "transaction_time" in adapted.columns
        assert adapted["transaction_time"].iloc[0] == "14:35:20"
        assert adapted["date"].iloc[0] == "2023-03-06"


    def test_adapter_without_transaction_time(self):
        raw = pd.DataFrame({
            "date": ["2023-03-06"],
            "item": ["Latte"],
            "price": [5.0],
            "units_sold": [2],
        })

        adapted, warnings = adapt_to_canonical(raw)

        assert "transaction_time" in adapted.columns
        assert pd.isna(adapted["transaction_time"].iloc[0])
    

    def test_combined_datetime_preserves_time(self):
        raw = pd.DataFrame({
            "date": ["2023-03-06 14:35:20"],
            "item": ["Latte"],
            "price": [5.0],
            "units_sold": [2],
        })

        adapted, _ = adapt_to_canonical(raw)
        cleaned, errors, _ = validate_sales_df(adapted)

        self.assertFalse(errors)
        self.assertEqual(
            str(cleaned["date"].iloc[0]),
            "2023-03-06 00:00:00",
        )
        self.assertEqual(
            cleaned["transaction_time"].iloc[0],
            "14:35:20",
        )

    def test_midnight_transaction_time(self):
        raw = pd.DataFrame({
            "date": ["2023-03-06 00:00:00"],
            "item": ["Latte"],
            "price": [5.0],
            "units_sold": [2],
        })

        adapted, _ = adapt_to_canonical(raw)
        cleaned, errors, _ = validate_sales_df(adapted)

        self.assertFalse(errors)
        self.assertEqual(
            cleaned["transaction_time"].iloc[0],
            "00:00:00",
        )

    def test_date_only_has_no_transaction_time(self):
        raw = pd.DataFrame({
            "date": ["2023-03-06"],
            "item": ["Latte"],
            "price": [5.0],
            "units_sold": [2],
        })

        adapted, _ = adapt_to_canonical(raw)
        cleaned, errors, _ = validate_sales_df(adapted)

        self.assertFalse(errors)
        self.assertTrue(
            pd.isna(cleaned["transaction_time"].iloc[0])
        )

    def test_separate_transaction_time_preserved(self):
        raw = pd.DataFrame({
            "transaction_date": ["2023-03-06"],
            "transaction_time": ["09:15:30"],
            "product_detail": ["Latte"],
            "unit_price": [5.0],
            "transaction_qty": [2],
        })

        adapted, _ = adapt_to_canonical(raw)
        cleaned, errors, _ = validate_sales_df(adapted)

        self.assertFalse(errors)
        self.assertEqual(
            cleaned["transaction_time"].iloc[0],
            "09:15:30",
        )



if __name__ == "__main__":
    unittest.main()
