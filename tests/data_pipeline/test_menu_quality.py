"""Part 5 menu data-quality regression tests."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.menu_quality import audit_menu_quality, normalized_item_key


@pytest.fixture
def sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "menu": [" Latte ", "LATTE", "Tea", "Tea", None, "Matcha"],
            "cost": [2.0, 2.0, 1.0, 1.0, 0.3, 3.0],
            "price": [5.0, 5.5, 3.0, 3.0, "bad", 6.0],
            "qty": [1, 2, 1, 1, -1, 0],
            "day": ["2026-01-01", "2026-01-02", "bad", "2026-01-03", None, "2026-01-05"],
            "line_id": ["a", "b", "c", "d", "e", "f"],
        }
    )


@pytest.fixture
def mapping() -> dict[str, str | None]:
    return {
        "item": "menu", "price": "price", "unit_cost": "cost",
        "units_sold": "qty", "date": "day",
    }


def test_normalizes_names_without_rewriting_source(sales, mapping):
    before = sales.copy(deep=True)
    result = audit_menu_quality(sales, mapping)
    assert result.repeated_item_spelling_groups == 1
    assert result.missing_item_rows == 1
    assert result.preview["item_key"].iloc[0] == "latte"
    assert result.preview["item_key"].iloc[1] == "latte"
    pd.testing.assert_frame_equal(sales, before)


def test_multiple_observed_prices_are_not_collapsed(sales, mapping):
    result = audit_menu_quality(sales, mapping)
    assert len(result.multi_price_items) == 1
    assert result.multi_price_items.iloc[0]["item_key"] == "latte"
    assert result.multi_price_items.iloc[0]["lowest_price"] == "5.00"
    assert result.multi_price_items.iloc[0]["highest_price"] == "5.50"


def test_alias_map_suggests_but_does_not_replace(sales, mapping):
    result = audit_menu_quality(sales, mapping, aliases={"LATTE": "Caffe Latte"})
    assert result.preview["suggested_item"].iloc[0] == "Caffe Latte"
    assert sales["menu"].iloc[0] == " Latte "
    assert result.preview["suggested_item"].iloc[2] == "Tea"


def test_detects_invalid_values_and_refund_candidates(sales, mapping):
    result = audit_menu_quality(sales, mapping)
    assert result.invalid_numeric_values["price"] == 1
    assert result.invalid_date_rows == 1
    assert result.nonpositive_quantity_rows == 2
    assert result.missing_required_values["item"] == 1


def test_duplicate_rows_are_candidates_not_removed(mapping):
    df = pd.DataFrame({"menu": ["Tea", "Tea"], "price": [3, 3]})
    audit = audit_menu_quality(df, mapping)
    assert audit.exact_duplicate_candidates == 2
    assert audit.inspected_rows == 2
    assert len(df) == 2


def test_distinct_line_id_is_different_from_order_id(sales, mapping):
    df = sales.copy()
    df.loc[3, "line_id"] = "c"
    report = audit_menu_quality(df, mapping, line_id_column="line_id")
    assert report.repeated_line_ids == 2
    with pytest.raises(ValueError, match="Unknown line ID"):
        audit_menu_quality(df, mapping, line_id_column="missing")


def test_unicode_and_whitespace_name_key():
    assert normalized_item_key(" Ｃａｆｅ\u0301\t LATTE  ") == "café latte"
    assert normalized_item_key(" \t ") is None
    assert normalized_item_key(None) is None


def test_conflicting_aliases_rejected(sales, mapping):
    with pytest.raises(ValueError, match="Conflicting aliases"):
        audit_menu_quality(sales, mapping, aliases={"Latte": "A", " LATTE ": "B"})


def test_duplicate_column_names_rejected(sales, mapping):
    df = sales.copy()
    df.columns = ["menu", "price", "price", "qty", "day", "line_id"]
    with pytest.raises(ValueError, match="unique"):
        audit_menu_quality(df, mapping)


def test_mixed_data_never_silently_coerced(mapping):
    df = pd.DataFrame({"menu": ["A", "A"], "price": ["5.00", "five"], "qty": [1, -1]})
    result = audit_menu_quality(df, mapping)
    assert result.invalid_numeric_values["price"] == 1
    assert result.nonpositive_quantity_rows == 1
    assert len(result.preview) == 2
