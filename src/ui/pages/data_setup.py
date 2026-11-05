"""Streamlit workflow module extracted from app.py."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pandas as pd
import streamlit as st

from analytics.analysis import load_sales
from config import CANONICAL_FIELDS
from ui.data_upload import load_uploaded_sales, render_source_audit
from ui.mapping import (
    discount_amount_selector,
    discount_percent_selector,
    mapping_selectors,
    transaction_amount_selector,
    transaction_status_selector,
)
from ui.sidebar import SidebarSettings
from ui.table_formatters import prepare_dataframe_for_display


class SetupData(NamedTuple):
    raw_df: pd.DataFrame
    mapping: dict[str, str | None]
    source: str
    business_name: str
    dataset_name: str
    discount_column: str | None
    discount_percent_column: str | None
    transaction_status_column: str | None
    transaction_amount_column: str | None
    price_basis: str


def render_data_setup(settings: SidebarSettings) -> SetupData:
    business_name = settings.business_name
    dataset_name = settings.dataset_name
    source = settings.source
    uploaded = settings.uploaded
    encoding = settings.encoding

    # Load dataset
    # ================================================================

    raw_df: pd.DataFrame | None = None

    mapping: dict[str, str | None] = {field: None for field in CANONICAL_FIELDS}

    if source == "Full Demo Dataset — Synthetic Cafe":
        demo_path = Path(__file__).resolve().parents[3] / "data" / "cafe_sales.csv"

        raw_df = load_sales(str(demo_path))

        # Map only columns that actually exist in the demo dataset.
        # Optional fields, such as transaction_time, may be missing.
        mapping = {
            field: field if field in raw_df.columns else None
            for field in CANONICAL_FIELDS
        }

        business_name = (
            business_name
            if business_name != "My Food-Service Business"
            else "Synthetic Cafe"
        )

        dataset_name = (
            dataset_name
            if dataset_name != "Menu Sales Dataset"
            else "Full Demo Dataset — Synthetic Cafe"
        )

        st.info(
            "Using the bundled synthetic dataset with complete "
            "price, cost, and quantity fields."
        )

    elif uploaded is not None:
        try:
            raw_df, source_audit_messages = load_uploaded_sales(
                uploaded,
                encoding=encoding,
                sheet_name=getattr(settings, "sheet_name", None),
            )

            render_source_audit(source_audit_messages)

        except Exception as exc:  # noqa: BLE001
            # CSV uploads can fail during parsing, decoding, or source auditing.
            # Show a user-friendly error instead of crashing the dashboard.
            st.error(f"Could not read or audit the dataset: {exc}")
            st.stop()

    else:
        st.info("Upload a CSV or Excel workbook to startYou do not need to rename its columns first")
        st.stop()

    # ================================================================
    # Feature 2: Data Setup & Column Mapping
    # ================================================================

    with st.expander("⚙️ Data Setup & Column Mapping", expanded=False):
        if source == "Upload my own CSV":
            st.write(
                "Automatic detection has preselected likely matches. "
                "Correct any mapping that is wrong."
            )

            with st.expander("Preview raw columns", expanded=False):
                st.dataframe(
                    prepare_dataframe_for_display(raw_df.head(10)),
                    use_container_width=True,
                )

            mapping = mapping_selectors(raw_df)

            st.markdown("#### Optional POS Discount Mapping")

            price_basis_label = st.selectbox(
                "POS Price Basis",
                [
                    "Unknown (not verified)",
                    "Listed price (before discounts)",
                    "Realized price (already discounted)",
                ],
                index=0,
                key="sales_pos_price_basis",
                help=(
                    "Specify whether the mapped Price column contains "
                    "original prices before discounts or prices that "
                    "already include discounts. Choose Unknown unless "
                    "you have verified the POS export convention."
                ),
            )

            price_basis = {
                "Unknown (not verified)": "unknown",
                "Listed price (before discounts)": "listed",
                "Realized price (already discounted)": "realized",
            }[price_basis_label]

            discount_column = discount_amount_selector(
                raw_df,
                prefix="sales",
                mapping=mapping,
            )

            discount_percent_column = discount_percent_selector(
                raw_df,
                prefix="sales",
                mapping=mapping,
                discount_amount_column=discount_column,
            )

            st.markdown("#### Optional POS Transaction Classification")

            excluded_pos_columns = {
                column
                for column in (
                    discount_column,
                    discount_percent_column,
                )
                if column is not None
            }

            transaction_status_column = transaction_status_selector(
                raw_df,
                prefix="sales",
                mapping=mapping,
                excluded_columns=excluded_pos_columns,
            )

            if transaction_status_column is not None:
                excluded_pos_columns.add(transaction_status_column)

            transaction_amount_column = transaction_amount_selector(
                raw_df,
                prefix="sales",
                mapping=mapping,
                excluded_columns=excluded_pos_columns,
            )

            if (
                transaction_status_column is not None
                or transaction_amount_column is not None
            ):
                st.caption(
                    "Transaction classification fields are mapped "
                    "for review only. Refund and cancellation statuses "
                    "do not automatically change dashboard revenue "
                    "or demand calculations."
                )

            if discount_column is not None:
                st.caption(f"Monetary discount column: `{discount_column}`.")

            if discount_percent_column is not None:
                st.caption(f"Percentage discount column: `{discount_percent_column}`.")

            if discount_column is not None or discount_percent_column is not None:
                st.info(
                    "Discounts are currently shown in the POS "
                    "accounting preview only. Dashboard revenue, "
                    "profit, and pricing calculations have not "
                    "been adjusted for discounts."
                )

            if discount_column is not None and discount_percent_column is not None:
                st.warning(
                    "Both monetary and percentage discounts are "
                    "mapped. These may describe overlapping "
                    "promotions. They will not be combined until "
                    "their accounting relationship is confirmed."
                )

            # Warn users when the POS price basis is uncertain.
            if discount_column is not None or discount_percent_column is not None:
                if price_basis == "unknown":
                    st.warning(
                        "The POS price basis has not been verified. "
                        "Discount-adjusted revenue should not be "
                        "treated as reliable until you confirm "
                        "whether prices are listed or already discounted."
                    )
                elif price_basis == "realized":
                    st.info(
                        "Source prices already include discounts. "
                        "Discounts must not be subtracted again."
                    )

            if discount_column is not None:
                st.caption(
                    f"Discount column selected: `{discount_column}`. "
                    "Discounts are not yet applied to dashboard "
                    "revenue or pricing calculations."
                )

        else:
            discount_column = None
            discount_percent_column = None
            transaction_status_column = None
            transaction_amount_column = None
            price_basis = "unknown"

            st.success("Bundled demo columns already match the canonical schema.")

    return SetupData(
        raw_df=raw_df,
        mapping=mapping,
        source=source,
        business_name=business_name,
        dataset_name=dataset_name,
        discount_column=discount_column,
        discount_percent_column=discount_percent_column,
        transaction_status_column=transaction_status_column,
        transaction_amount_column=transaction_amount_column,
        price_basis=price_basis,
    )
