"""Optional, read-only Data Quality dashboard for menu-name diagnostics."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from data_pipeline.menu_quality import audit_menu_quality


def render_menu_quality(df: pd.DataFrame, mapping: dict[str, str | None]) -> None:
    """Show suggestions without editing uploaded rows or financial inputs."""
    st.subheader("Menu Data Quality")
    st.caption(
        "Read-only diagnostics. Item aliases, repeated rows and varying prices are "
        "review candidates, not automatic corrections or financial adjustments."
    )
    if not mapping.get("item"):
        st.info("Map the menu item column in Data Setup to enable these checks.")
        return

    line_candidates = [
        str(c) for c in df.columns
        if c != mapping.get("item")
        and any(term in str(c).casefold() for term in ("line_id", "row_id", "line_item_id"))
    ]
    with st.expander("Menu names, duplicate candidates and price consistency", expanded=False):
        line_col = st.selectbox(
            "Unique transaction line ID (optional — do not use order ID)",
            [None, *line_candidates],
            key="menu_quality_line_id",
        )
        alias_upload = st.file_uploader(
            "Optional reviewed aliases CSV (columns: alias, canonical)",
            type=["csv"],
            key="menu_quality_alias_upload",
            help="Suggestions only. Does not automatically merge items in revenue or reports.",
        )
        aliases: dict[str, str] = {}
        if alias_upload is not None:
            try:
                alias_df = pd.read_csv(io.BytesIO(alias_upload.getvalue()), dtype="string")
                if not {"alias", "canonical"}.issubset(alias_df.columns):
                    raise ValueError("Alias file must have alias and canonical columns.")
                if alias_df[["alias", "canonical"]].isna().any().any():
                    raise ValueError("Alias file cannot contain empty alias/canonical fields.")
                if alias_df["alias"].duplicated().any():
                    raise ValueError("Alias entries must not be duplicated.")
                aliases = dict(zip(alias_df["alias"].astype(str), alias_df["canonical"].astype(str), strict=True))
            except (ValueError, pd.errors.ParserError, UnicodeError) as exc:
                st.warning(f"Alias CSV could not be used: {exc}")
                return

        try:
            audit = audit_menu_quality(df, mapping, line_id_column=line_col, aliases=aliases)
        except ValueError as exc:
            st.warning(f"Menu quality review unavailable: {exc}")
            return

        a, b, c, d = st.columns(4)
        a.metric("Rows inspected", audit.inspected_rows)
        b.metric("Spelling variants", audit.repeated_item_spelling_groups)
        c.metric("Multiple-price items", len(audit.multi_price_items))
        d.metric("Exact-row duplicate candidates", audit.exact_duplicate_candidates)
        if audit.repeated_line_ids is not None:
            st.metric("Repeated line ID rows", audit.repeated_line_ids)
        if audit.invalid_date_rows is not None:
            st.caption(f"Invalid nonblank date values: {audit.invalid_date_rows}")
        if audit.nonpositive_quantity_rows is not None:
            st.caption(
                f"Nonpositive quantity rows: {audit.nonpositive_quantity_rows} "
                "(negative quantities can indicate refunds)"
            )
        if audit.nonpositive_price_rows is not None:
            st.caption(f"Nonpositive price rows: {audit.nonpositive_price_rows}")
        st.write("**Missing mapped values**", audit.missing_required_values)
        st.write("**Invalid mapped numeric values**", audit.invalid_numeric_values)
        if not audit.item_alias_suggestions.empty:
            st.write("**Spelling variants for review**")
            st.dataframe(audit.item_alias_suggestions, use_container_width=True)
        if not audit.multi_price_items.empty:
            st.write("**Items sold at multiple listed prices**")
            st.dataframe(audit.multi_price_items, use_container_width=True)
        st.download_button(
            "Download menu-name review CSV",
            data=audit.preview.to_csv(index=False).encode("utf-8-sig"),
            file_name="menu_name_review.csv",
            mime="text/csv",
            key="menu_quality_review_download",
        )
        st.caption(
            "A repeated order ID is normal for multi-line orders. Only inspect an "
            "actual unique line ID for line-event duplication. No source rows were removed."
        )
