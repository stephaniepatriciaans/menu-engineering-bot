"""Adapt arbitrary menu/POS CSV columns into the canonical analysis schema."""

from __future__ import annotations

import io
from difflib import SequenceMatcher
from typing import Iterable, Mapping

import pandas as pd

from config import CANONICAL_FIELDS, COLUMN_ALIASES, CORE_FIELDS, normalize_column_name

NOT_AVAILABLE = "Not available"


def read_delimited_csv(file_obj) -> pd.DataFrame:
    """
    Read uploaded CSV-style files with automatic delimiter detection.

    Supports:
    - comma: ,
    - pipe: |
    - semicolon: ;
    - tab: \\t
    """
    file_obj.seek(0)
    raw = file_obj.read()

    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig")
    else:
        text = raw

    if not text.strip():
        raise ValueError("The uploaded file is empty.")

    first_line = text.splitlines()[0]

    delimiters = [",", "|", ";", "\t"]

    delimiter_counts = {
        delimiter: first_line.count(delimiter)
        for delimiter in delimiters
    }

    detected_delimiter = max(
        delimiter_counts,
        key=delimiter_counts.get,
    )

    if delimiter_counts[detected_delimiter] == 0:
        raise ValueError(
            "Could not detect the file delimiter. "
            "Supported delimiters are comma, pipe, semicolon, and tab."
        )

    return pd.read_csv(
        io.StringIO(text),
        sep=detected_delimiter,
    )


def detect_column_mapping(columns: Iterable[object]) -> dict[str, str | None]:
    """Detect raw-to-canonical mappings using normalized aliases and conservative fuzzy matching."""
    raw_columns = [str(col) for col in columns]
    normalized_raw = {raw: normalize_column_name(raw) for raw in raw_columns}
    mapping: dict[str, str | None] = {field: None for field in CANONICAL_FIELDS}
    used: set[str] = set()

    for field in CANONICAL_FIELDS:
        aliases = {normalize_column_name(alias) for alias in COLUMN_ALIASES[field]}
        exact = [raw for raw, norm in normalized_raw.items() if norm in aliases and raw not in used]
        if len(exact) == 1:
            mapping[field] = exact[0]
            used.add(exact[0])
            continue

        # Conservative fallback: useful for minor punctuation/wording differences,
        # but high enough to avoid surprising automatic assignments.
        scored: list[tuple[float, str]] = []
        for raw, norm in normalized_raw.items():
            if raw in used:
                continue
            score = max(SequenceMatcher(None, norm, alias).ratio() for alias in aliases)
            if score >= 0.90:
                scored.append((score, raw))
        scored.sort(reverse=True)
        if scored and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.03):
            mapping[field] = scored[0][1]
            used.add(scored[0][1])

    return mapping


def validate_mapping(mapping: Mapping[str, str | None], available_columns: Iterable[object]) -> list[str]:
    """Return human-readable mapping errors before dataframe adaptation."""
    errors: list[str] = []
    available = {str(col) for col in available_columns}

    missing_core = [field for field in CORE_FIELDS if not mapping.get(field)]
    if missing_core:
        errors.append("Map the required fields: " + ", ".join(missing_core) + ".")

    selected = [str(raw) for raw in mapping.values() if raw]
    duplicates = sorted({raw for raw in selected if selected.count(raw) > 1})
    if duplicates:
        errors.append("Each source column can map to only one field. Reused: " + ", ".join(duplicates) + ".")

    missing_raw = [str(raw) for raw in mapping.values() if raw and str(raw) not in available]
    if missing_raw:
        errors.append("Mapped columns were not found in the CSV: " + ", ".join(missing_raw) + ".")
    return errors


def adapt_to_canonical(
    raw_df: pd.DataFrame,
    mapping: Mapping[str, str | None] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Rename/select raw columns into the canonical schema without doing numeric analysis."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=CANONICAL_FIELDS), []

    mapping = dict(mapping or detect_column_mapping(raw_df.columns))
    errors = validate_mapping(mapping, raw_df.columns)
    if errors:
        raise ValueError(" ".join(errors))

    out = pd.DataFrame(index=raw_df.index)
    for field in CANONICAL_FIELDS:
        raw_col = mapping.get(field)
        if raw_col:
            out[field] = raw_df[str(raw_col)]

    warnings: list[str] = []
    if "category" not in out:
        out["category"] = "Uncategorized"
        warnings.append("No category column was mapped. Missing categories were set to 'Uncategorized'.")
    else:
        blank = out["category"].isna() | out["category"].astype(str).str.strip().isin(["", "nan", "None"])
        if blank.any():
            out.loc[blank, "category"] = "Uncategorized"
            warnings.append(f"{int(blank.sum())} rows had no category and were set to 'Uncategorized'.")

    if "unit_cost" not in out:
        out["unit_cost"] = pd.NA
        warnings.append(
            "Unit cost was not mapped. Revenue/popularity analysis can run, but profit-based analysis needs cost data."
        )

    return out[CANONICAL_FIELDS].copy(), warnings


def merge_cost_reference(
    sales_df: pd.DataFrame,
    raw_cost_df: pd.DataFrame,
    item_column: str,
    cost_column: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Fill unit_cost by matching item names to a separate menu-cost CSV."""
    warnings: list[str] = []
    if item_column not in raw_cost_df.columns or cost_column not in raw_cost_df.columns:
        raise ValueError("The selected item/cost columns were not found in the cost CSV.")

    cost_df = raw_cost_df[[item_column, cost_column]].copy()
    cost_df["_item_key"] = cost_df[item_column].astype(str).str.strip().str.casefold()
    cost_df["_cost"] = pd.to_numeric(cost_df[cost_column], errors="coerce")
    cost_df = cost_df.dropna(subset=["_cost"])

    duplicate_keys = cost_df["_item_key"].duplicated(keep=False)
    if duplicate_keys.any():
        warnings.append("The cost CSV had duplicate item names; the last valid cost for each item was used.")
    cost_df = cost_df.drop_duplicates("_item_key", keep="last")

    out = sales_df.copy()
    out["_item_key"] = out["item"].astype(str).str.strip().str.casefold()
    cost_map = cost_df.set_index("_item_key")["_cost"]
    mapped = out["_item_key"].map(cost_map)
    out["unit_cost"] = out["unit_cost"].where(out["unit_cost"].notna(), mapped)
    out = out.drop(columns=["_item_key"])

    missing = int(out["unit_cost"].isna().sum())
    if missing:
        warnings.append(
            f"Cost lookup did not match {missing} sales rows. Profit-dependent features remain disabled until all rows have cost."
        )
    return out, warnings


def apply_estimated_cost_percentage(df: pd.DataFrame, cost_pct: float) -> pd.DataFrame:
    """Create an explicit scenario cost assumption as a percentage of selling price."""
    if not 0 <= cost_pct < 1:
        raise ValueError("Estimated cost percentage must be between 0% and less than 100%.")
    out = df.copy()
    prices = pd.to_numeric(out["price"], errors="coerce")
    out["unit_cost"] = prices * float(cost_pct)
    return out
