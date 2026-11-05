"""Non-destructive menu/POS data-quality checks.

No rows are dropped, prices rewritten, or products merged by this module.
Alias suggestions are advisory until a human reviews them.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, cast

import numpy as np
import pandas as pd


def normalized_item_key(value: object) -> str | None:
    """Return a Unicode-normalized, case-insensitive comparison key."""
    if value is None or bool(pd.isna(cast(Any, value))):
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text or None


def _cents(value: object) -> Decimal | None:
    """Parse finite numeric price without accepting booleans or missing values."""
    if isinstance(value, bool) or bool(pd.isna(cast(Any, value))):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not amount.is_finite():
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _column(mapping: dict[str, str | None], name: str, df: pd.DataFrame) -> str | None:
    column = mapping.get(name)
    return column if column is not None and column in df.columns else None


@dataclass(frozen=True)
class MenuQualityReport:
    inspected_rows: int
    missing_item_rows: int
    repeated_item_spelling_groups: int
    item_alias_suggestions: pd.DataFrame
    multi_price_items: pd.DataFrame
    exact_duplicate_candidates: int
    repeated_line_ids: int | None
    missing_required_values: dict[str, int]
    invalid_numeric_values: dict[str, int]
    nonpositive_price_rows: int | None
    nonpositive_quantity_rows: int | None
    invalid_date_rows: int | None
    preview: pd.DataFrame


def _map_unique_values(
    series: pd.Series,
    transform: Any,
) -> pd.Series:
    """Transform distinct values once, preserving source row positions.

    Missing inputs remain missing. Useful when a large POS export
    repeats the same item names or prices thousands of times.
    """
    codes, unique_values = pd.factorize(
        series,
        sort=False,
    )

    transformed = np.asarray(
        [transform(value) for value in unique_values],
        dtype=object,
    )

    result = np.empty(len(series), dtype=object)
    result[:] = None

    valid = codes >= 0

    if valid.any():
        result[valid] = transformed[codes[valid]]

    return pd.Series(result, index=series.index, dtype=object)


def audit_menu_quality(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    *,
    line_id_column: str | None = None,
    aliases: dict[str, str] | None = None,
) -> MenuQualityReport:
    """Review menu identity, prices, duplicate candidates and field integrity.

    `line_id_column` must identify a unique *line*, not an order or event
    containing multiple items. A duplicate row may be a legitimate transaction.
    """
    if not df.columns.is_unique:
        raise ValueError("Source column names must be unique before quality auditing.")
    if line_id_column is not None and line_id_column not in df.columns:
        raise ValueError(f"Unknown line ID column: {line_id_column}")

    item_col = _column(mapping, "item", df)
    if item_col is None:
        raise ValueError("Map an item column to run menu quality checks.")
    if aliases:
        normalized_aliases: dict[str, str] = {}
        for alias, canonical in aliases.items():
            key = normalized_item_key(alias)
            target = str(canonical).strip()
            if key is None or not target:
                raise ValueError("Alias and canonical item labels must be nonempty.")
            if key in normalized_aliases and normalized_aliases[key] != target:
                raise ValueError("Conflicting aliases collapse to the same comparison key.")
            normalized_aliases[key] = target
    else:
        normalized_aliases = {}


    # Normalize each distinct source item once.
    # Keep every original source row unchanged.
    names = _map_unique_values(
        df[item_col],
        normalized_item_key,
    )

    display_names = df[item_col].astype("string").str.strip()

    suggested_names = names.map(normalized_aliases)
    suggested_names = suggested_names.where(
        suggested_names.notna(),
        display_names,
    )

    preview = pd.DataFrame(
        {
            "source_item": df[item_col],
            "item_key": names,
            "suggested_item": suggested_names,
        },
        index=df.index,
    )

    # Build the grouping only once and reuse it for
    # spelling consistency and multiple-price analysis.
    item_groups = names.groupby(
        names,
        dropna=True,
    ).indices

    alias_rows: list[dict[str, object]] = []
    repeated_groups = 0

    for key, positions in item_groups.items():
        row_positions = np.asarray(positions, dtype=np.intp)

        spellings = sorted({
            str(value)
            for value in display_names.iloc[row_positions]
        })

        if len(spellings) > 1:
            repeated_groups += 1
            alias_rows.append({
                "item_key": str(key),
                "source_spellings": " | ".join(spellings),
                "suggested_label": normalized_aliases.get(
                    str(key),
                    spellings[0],
                ),
                "transaction_rows": len(positions),
            })

    price_col = _column(mapping, "price", df)
    multi_prices: list[dict[str, object]] = []

    if price_col:
        # Convert distinct source prices to Decimal once.
        # Preserve existing half-up cent rounding.
        price_values = _map_unique_values(
            df[price_col],
            _cents,
        )

        preview["listed_price"] = df[price_col]

        for key, positions in item_groups.items():
            row_positions = np.asarray(positions, dtype=np.intp)
            group_prices = price_values.iloc[row_positions]

            # Unique valid prices, without repeatedly
            # accessing each row through Python-level iloc.
            valid_prices = group_prices.dropna()
            amounts = sorted(
                valid_prices.unique().tolist()
            )

            if len(amounts) > 1:
                multi_prices.append({
                    "item_key": str(key),
                    "distinct_prices": len(amounts),
                    "lowest_price": str(amounts[0]),
                    "highest_price": str(amounts[-1]),
                    "transaction_rows": len(positions),
                })
    else:
        price_values = None

    missing: dict[str, int] = {}
    invalid: dict[str, int] = {}
    for field in ("date", "item", "category", "price", "units_sold", "unit_cost"):
        col = _column(mapping, field, df)
        if col is None:
            continue
        series = df[col]
        blanks = series.isna() | series.astype("string").str.strip().fillna("").eq("")
        missing[field] = int(blanks.sum())
        if field in ("price", "units_sold", "unit_cost"):
            parsed = pd.to_numeric(series, errors="coerce")
            valid_numeric = parsed.notna() & parsed.map(lambda x: bool(pd.notna(x) and abs(x) != float("inf")))
            invalid[field] = int((~blanks & ~valid_numeric).sum())

    date_col = _column(mapping, "date", df)
    if date_col is not None:
        with pd.option_context("mode.chained_assignment", None):
            dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
        invalid_dates = int((dates.isna() & df[date_col].notna() & df[date_col].astype("string").str.strip().ne("")).sum())
    else:
        invalid_dates = None

    quantity_col = _column(mapping, "units_sold", df)
    if quantity_col:
        quantities = pd.to_numeric(df[quantity_col], errors="coerce")
        nonpositive_qty = int((quantities <= 0).sum())
    else:
        nonpositive_qty = None

    nonpositive_price = int(sum(value is not None and value <= 0 for value in price_values)) if price_values is not None else None

    # Exact duplicate candidates are not assumed fraudulent or safe to delete.
    # The entire source row is checked; distinct line IDs distinguish events.
    duplicate_candidates = int(df.duplicated(keep=False).sum())
    if line_id_column is not None:
        ids = df[line_id_column]
        present = ids.notna() & ids.astype("string").str.strip().ne("")
        repeated_ids = int(ids.loc[present].duplicated(keep=False).sum())
    else:
        repeated_ids = None

    return MenuQualityReport(
        inspected_rows=len(df),
        missing_item_rows=int(names.isna().sum()),
        repeated_item_spelling_groups=repeated_groups,
        item_alias_suggestions=pd.DataFrame(alias_rows, columns=["item_key", "source_spellings", "suggested_label", "transaction_rows"]),
        multi_price_items=pd.DataFrame(multi_prices, columns=["item_key", "distinct_prices", "lowest_price", "highest_price", "transaction_rows"]),
        exact_duplicate_candidates=duplicate_candidates,
        repeated_line_ids=repeated_ids,
        missing_required_values=missing,
        invalid_numeric_values=invalid,
        nonpositive_price_rows=nonpositive_price,
        nonpositive_quantity_rows=nonpositive_qty,
        invalid_date_rows=invalid_dates,
        preview=preview,
    )
