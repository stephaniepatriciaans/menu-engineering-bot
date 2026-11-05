"""Streamlit workflow module extracted from app.py."""

from __future__ import annotations

from typing import NamedTuple

import pandas as pd
import streamlit as st

from analytics.analysis import build_item_summary
from core.dashboard_utils import add_transaction_datetime
from core.financial_review import summarize_financial_review
from core.validation import determine_capabilities, validate_sales_df
from data_pipeline.adapter import adapt_to_canonical, validate_mapping
from pos.transactions import split_pos_transactions
from ui.capabilities import build_capability_report
from ui.components import render_validation_overview
from ui.cost_settings import render_cost_settings
from ui.data_upload import (
    render_pos_accounting_summary,
    render_pos_classification_summary,
)
from ui.filters import render_category_filter, render_date_filter
from ui.menu_quality import render_menu_quality
from ui.pages.data_setup import SetupData
from ui.pos_reconciliation import render_pos_reconciliation


class QualityData(NamedTuple):
    df: pd.DataFrame
    summary: pd.DataFrame
    capabilities: dict
    refund_candidates_df: pd.DataFrame
    cost_basis: str
    cost_is_assumption: bool
    start_date: object
    end_date: object
    financial_preview: dict[str, object] | None = None


def render_data_quality(setup: SetupData) -> QualityData:
    raw_df = setup.raw_df
    mapping = setup.mapping
    source = setup.source
    discount_column = setup.discount_column
    discount_percent_column = setup.discount_percent_column
    transaction_status_column = setup.transaction_status_column
    transaction_amount_column = setup.transaction_amount_column
    price_basis = setup.price_basis

    # Validate column mapping — visible outside expander
    # ================================================================

    mapping_errors = validate_mapping(mapping, raw_df.columns)

    if mapping_errors:
        st.error(
            "Dataset column mapping needs attention. "
            "Open Data Setup & Column Mapping to correct the selections."
        )

        for error in mapping_errors:
            st.error(error)

        st.stop()


    # ================================================================
    # Preliminary financial review: not an accounting reconciliation.
    # ================================================================
    st.subheader("Financial Review")
    if source == "Upload my own CSV":
        review = summarize_financial_review(
            raw_df,
            mapping,
            status_column=transaction_status_column,
            amount_column=transaction_amount_column,
            discount_column=discount_column,
            discount_percent_column=discount_percent_column,
            price_basis=price_basis,
        )
        st.warning(
            "Financial accounting **not verified**. These source-data checks "
            "do not confirm refunds, discounts, taxes, tips, or net revenue. "
            "The Analytics dashboard uses its existing sales-only calculation."
        )
        a, b, c, d = st.columns(4)
        a.metric(
            "Refund candidates",
            review.refund_candidates if review.refund_candidates is not None else "—",
        )
        b.metric(
            "Cancelled rows",
            review.cancelled if review.cancelled is not None else "—",
        )
        c.metric(
            "Classification conflicts",
            review.conflicts if review.conflicts is not None else "—",
        )
        d.metric("Discount columns mapped", review.discount_fields_mapped)
        if review.classification_note:
            st.warning(review.classification_note)
        if review.price_basis == "unknown" and review.discount_fields_mapped:
            st.info(
                "Discount-adjusted revenue is unavailable until the POS "
                "price basis (listed or realized) is confirmed in Data Setup."
            )
        if review.discount_fields_mapped > 1:
            st.info(
                "Both discount types are mapped; their combined accounting "
                "relationship has not been established."
            )
        if transaction_status_column is None and transaction_amount_column is None:
            st.caption(
                "No signed amount or status field is mapped. Counts above "
                "only identify negative-quantity refund candidates; "
                "cancellations and status-based refunds may be missing."
            )
        st.caption(
            "Refund and cancellation labels are review candidates, not "
            "confirmed accounting entries. A refunded status can label "
            "the original sale rather than a separate refund event."
        )
    else:
        st.info(
            "This is a synthetic demonstration dataset. Schema validation "
            "does not constitute independent financial verification."
        )

    # Read-only Part 5 menu data quality; never changes financial rows.
    render_menu_quality(raw_df, mapping)

    # ================================================================
    # POS transaction accounting preview
    # ================================================================

    if source == "Upload my own CSV":
        render_pos_accounting_summary(
            raw_df,
            mapping,
            discount_column=discount_column,
            discount_percent_column=discount_percent_column,
            price_basis=price_basis,
        )

        render_pos_classification_summary(
            raw_df,
            mapping,
            status_column=transaction_status_column,
            amount_column=transaction_amount_column,
        )


    financial_preview = None
    if source == "Upload my own CSV":
        financial_preview = render_pos_reconciliation(
            raw_df,
            mapping,
            price_basis=price_basis,
            status_column=transaction_status_column,
            amount_column=transaction_amount_column,
            line_discount_column=discount_column,
            percent_column=discount_percent_column,
        )

    # ================================================================
    # Adapt dataset to canonical schema
    # ================================================================

    try:
        canonical_df, adapter_warnings = adapt_to_canonical(
            raw_df,
            mapping,
        )

    except ValueError as exc:
        st.error(
            "The dataset could not be standardized. "
            "Please review the column mapping."
        )
        st.error(str(exc))
        st.stop()


    # ================================================================
    # Separate refund candidates from sales analysis
    # ================================================================

    refund_candidates_df = pd.DataFrame()

    if source == "Upload my own CSV":
        try:
            sales_df, refund_candidates_df = split_pos_transactions(
                canonical_df
            )
        except ValueError as exc:
            st.error(
                f"Unable to classify POS transactions: {exc}"
            )
            st.stop()

        if not refund_candidates_df.empty:
            st.warning(
                f"{len(refund_candidates_df):,} negative-quantity "
                "transaction(s) were identified as refund candidates. "
                "These records are preserved for the POS accounting "
                "preview but excluded from sales-only dashboard analysis. "
                "Dashboard revenue is gross sales revenue before refunds, "
                "not net revenue."
            )

        if sales_df.empty:
            st.error(
                "No nonnegative-quantity sales records are available "
                "for analysis. Review the uploaded transactions."
            )
            st.stop()

        canonical_df = sales_df

    # ================================================================
    # Optional cost handling
    # ================================================================

    canonical_df, cost_basis, cost_is_assumption = (
        render_cost_settings(canonical_df)
    )

    # ================================================================
    # Feature 3: Validate Dataset
    # ================================================================

    st.subheader("Dataset Validation")
    st.caption(
        "Checks that sales data can be standardized and analyzed. "
        "This does not certify the financial accuracy of the POS export."
    )

    # Validate the canonical dataframe.
    df, errors, validation_warnings = validate_sales_df(
        canonical_df
    )

    # Blocking errors must always remain visible.
    if errors or df is None:
        st.error(
            "Dataset validation failed. "
            "Please review the errors below."
        )

        for error in errors:
            st.error(error)

        st.stop()

    render_validation_overview(
        df=df,
        adapter_warnings=adapter_warnings,
        validation_warnings=validation_warnings,
    )

    # ================================================================
    # Date range filtering
    # ================================================================
    with st.expander("⚙️ Sales Filters", expanded=False):

        st.subheader("Filter sales by date")

        # Date filtering is handled by the reusable UI module.
        df, start_date, end_date = render_date_filter(df)

        # Category Filters
        df = render_category_filter(df)

        # Recalculate capabilities and item summaries
        # using the selected categories.
        capabilities = determine_capabilities(df)
        summary = build_item_summary(df)

        # This is stricter than simply seeing multiple prices: it reflects whether the
        # estimator actually accepted at least one item-level historical estimate.
        capabilities["historical_elasticity_estimation"] = bool(
            not summary.empty and (summary["elasticity_source"] == "estimated").any()
        )


        # ================================================================
        # Feature 7: Create transaction timestamps for hourly analysis.
        # ================================================================
        df = add_transaction_datetime(df)

        valid_timestamp_count = int(
            df["transaction_datetime"].notna().sum()
        )

        if valid_timestamp_count > 0:
            st.caption(
                f"Transaction times available for "
                f"{valid_timestamp_count:,} of {len(df):,} sales rows."
            )
        else:
            st.info(
                "This dataset does not contain usable transaction times. "
                "Daily and category analysis remain available, "
                "but hourly analysis will be unavailable."
            )


    # ================================================================
    # Dataset capabilities
    # ================================================================
    # Build the dataset capability report from the filtered summary
    # Reporting logic lives in ui/capabilities.py

    capability_text = build_capability_report(
        summary=summary,
        capabilities=capabilities,
        cost_is_assumption=cost_is_assumption,
    )


    # ================================================================
    # Active Filter Summary
    # ================================================================
    # Count the food groups remaining after category filtering
    active_group_count = df["category_group"].nunique()

    st.caption(
        f"📅 {start_date:%b %d, %Y} – {end_date:%b %d, %Y}"
        f"   |   🗂️ {active_group_count} food groups"
        f"   |   🧾 {len(df):,} sales records"
    )


    # ================================================================
    # Modern Fintech — Collapsible Dataset Capabilities
    # ================================================================

    with st.expander("View Dataset Capabilities", expanded=False):
        st.caption(
            "See which analyses are supported by your dataset "
            "and why certain features may be unavailable."
        )

        for capability in capability_text:
            if capability.startswith("✓ "):
                available = True
                description = capability[2:]
            elif capability.startswith("✗ "):
                available = False
                description = capability[2:]
            else:
                available = False
                description = capability

            # Separate the capability name from its explanation.
            name, separator, reason = description.partition(" — ")

            with st.container(border=True):
                status_col, content_col = st.columns(
                    [1, 12],
                    gap="small",
                    vertical_alignment="center",
                )

                with status_col:
                    if available:
                        st.markdown("🟢")
                    else:
                        st.markdown("🟠")

                with content_col:
                    st.markdown(f"**{name}**")

                    if separator and reason:
                        st.caption(reason)


    return QualityData(
        df=df,
        summary=summary,
        capabilities=capabilities,
        refund_candidates_df=refund_candidates_df,
        cost_basis=cost_basis,
        cost_is_assumption=cost_is_assumption,
        start_date=start_date,
        end_date=end_date,
        financial_preview=financial_preview,
    )
