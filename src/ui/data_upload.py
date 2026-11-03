"""Streamlit presentation helpers for uploaded datasets."""

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from data_adapter import read_delimited_csv
from pos_classification import classify_pos_transactions
from pos_transactions import (
    calculate_discounted_sales,
    calculate_percentage_discounted_sales,
    summarize_pos_transactions,
)
from validation import audit_source_transactions


def render_source_audit(messages: Iterable[str]) -> None:
    """Display source transaction audit messages."""

    with st.expander("Source transaction audit"):
        for message in messages:
            st.write(message)

        st.caption(
            "This audit checks for identical source records "
            "and repeated transaction IDs. "
            "Repeated IDs may be normal for multi-item orders. "
            "No records are automatically removed."
        )


def render_pos_accounting_summary(
    raw_df: pd.DataFrame,
    mapping: dict[str, str | None],
    discount_column: str | None = None,
    discount_percent_column: str | None = None,
    price_basis: str = "listed",
) -> None:
    """Display POS accounting when price and quantity are mapped.

    This is a source-data audit, not an authorization to use
    refund candidates as positive demand observations.
    """
    price_column = mapping.get("price")
    quantity_column = mapping.get("units_sold")

    if not price_column or not quantity_column:
        return

    if (
        price_column not in raw_df.columns
        or quantity_column not in raw_df.columns
    ):
        return

    transaction_df = raw_df[
        [price_column, quantity_column]
    ].rename(
        columns={
            price_column: "price",
            quantity_column: "units_sold",
        }
    )

    try:
        summary = summarize_pos_transactions(transaction_df)
    except ValueError as exc:
        st.warning(
            f"POS transaction accounting is unavailable: {exc}"
        )
        return

    with st.expander("POS transaction accounting", expanded=False):
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Gross Revenue",
            f"{summary['gross_revenue']:,.2f}",
        )
        col2.metric(
            "Refund Candidates",
            int(summary["refund_candidate_rows"]),
        )
        col3.metric(
            "Revenue After Refund Candidates",
            f"{summary['net_revenue']:,.2f}",
        )

        st.caption(
            "Negative quantities are treated as potential refund "
            "candidates for this preview. Revenue After Refund "
            "Candidates subtracts their estimated value from gross "
            "sales but does not account for discounts, taxes, tips, "
            "or other adjustments. Confirm the POS export conventions "
            "before using these figures for financial reporting. "
            "Refund candidates remain excluded from the validated "
            "demand-model pipeline."
        )
        
        if discount_column is not None or discount_percent_column is not None:
            st.divider()
            st.markdown("#### Discount Accounting Preview")
            
            if price_basis == "unknown":
                st.warning(
                    "Discount-adjusted revenue is unavailable because "
                    "the POS price basis has not been verified. "
                    "Confirm whether source prices are before or "
                    "after discounts."
                )
            elif price_basis == "realized":
                st.info(
                    "Source prices are already discounted. "
                    "Discounts will not be subtracted again. "
                    "The existing sales amounts reflect the "
                    "source prices, subject to other adjustments."
                )

            elif (
                discount_column is not None
                and discount_percent_column is not None
            ):
                st.warning(
                    "Both monetary and percentage discount columns "
                    "are mapped. Their accounting relationship is "
                    "unknown, so no combined discount calculation "
                    "will be displayed. Select only one discount "
                    "type for this preview."
                )
            else:
                selected_column = (
                    discount_column
                    if discount_column is not None
                    else discount_percent_column
                )

                if selected_column not in raw_df.columns:
                    st.warning(
                        "The selected discount column is missing "
                        "from the uploaded dataset."
                    )
                elif selected_column in {
                    price_column,
                    quantity_column,
                }:
                    st.warning(
                        "The discount column must be different "
                        "from the price and quantity columns."
                    )
                else:
                    # Refund candidates are excluded from
                    # sales-only discount calculations.
                    quantities = pd.to_numeric(
                        transaction_df["units_sold"],
                        errors="coerce",
                    )
                    sales_mask = quantities >= 0

                    discount_sales = transaction_df.loc[
                        sales_mask
                    ].copy()

                    source_field = (
                        "discount_amount"
                        if discount_column is not None
                        else "discount_percent"
                    )

                    discount_sales[source_field] = (
                        raw_df.loc[
                            sales_mask,
                            selected_column,
                        ].to_numpy()
                    )

                    try:
                        if discount_column is not None:
                            discount_result = calculate_discounted_sales(
                                discount_sales
                            )
                        else:
                            discount_result = (
                                calculate_percentage_discounted_sales(
                                    discount_sales
                                )
                            )
                    except ValueError as exc:
                        st.warning(
                            "Discount accounting is unavailable: "
                            f"{exc}"
                        )
                    else:
                        gross_sales = float(
                            discount_result["gross_line_amount"].sum()
                        )
                        total_discounts = float(
                            discount_result["discount_amount"].sum()
                        )
                        realized_sales = float(
                            discount_result["realized_line_amount"].sum()
                        )

                        d1, d2, d3 = st.columns(3)

                        d1.metric(
                            "Gross Sales",
                            f"{gross_sales:,.2f}",
                        )
                        d2.metric(
                            "Discounts",
                            f"{total_discounts:,.2f}",
                        )
                        d3.metric(
                            "Realized Sales",
                            f"{realized_sales:,.2f}",
                        )

                        st.caption(
                            "Discount-adjusted sales exclude "
                            "negative-quantity refund candidates. "
                            "Amounts assume listed prices before "
                            "discounts and exclude taxes, tips, "
                            "and service charges only when the "
                            "source price does. Realized Sales "
                            "is not necessarily refund-adjusted "
                            "net revenue. Dashboard and pricing "
                            "calculations still use original prices."
                        )

                    

def load_uploaded_sales(
    uploaded,
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, list[str]]:
    """Load uploaded sales data and audit source transactions.

    Reading and auditing are kept separate from Streamlit
    error handling so they can be independently tested.

    UTF-8 is the default. Windows-1252 can be selected
    explicitly for legacy POS exports.
    """
    uploaded.seek(0)

    raw_df = read_delimited_csv(
        uploaded,
        encoding=encoding,
    )

    source_audit_messages = audit_source_transactions(
        raw_df
    )

    return raw_df, source_audit_messages


def render_pos_classification_summary(
    raw_df: pd.DataFrame,
    mapping: dict[str, str | None],
    status_column: str | None = None,
    amount_column: str | None = None,
) -> None:
    """Preview transaction classifications without altering sales data."""
    quantity_column = mapping.get("units_sold")

    if quantity_column is None:
        return

    if status_column is None and amount_column is None:
        return

    try:
        classified = classify_pos_transactions(
            raw_df,
            quantity_column=quantity_column,
            status_column=status_column,
            amount_column=amount_column,
        )
    except ValueError as exc:
        st.warning(
            f"Transaction classification is unavailable: {exc}"
        )
        return

    counts = classified["transaction_class"].value_counts()

    with st.expander(
        "POS transaction classification",
        expanded=False,
    ):
        c1, c2, c3 = st.columns(3)

        c1.metric("Sales", int(counts.get("sale", 0)))
        c2.metric(
            "Refund Candidates",
            int(counts.get("refund_candidate", 0)),
        )
        c3.metric(
            "Cancelled",
            int(counts.get("cancelled", 0)),
        )

        c4, c5 = st.columns(2)

        c4.metric(
            "Classification Conflicts",
            int(classified["has_classification_conflict"].sum()),
        )
        c5.metric(
            "Records Requiring Review",
            int(classified["requires_accounting_review"].sum()),
        )

        st.caption(
            "Classifications are preliminary and depend on POS "
            "export conventions. Refunded statuses may identify "
            "original sales rather than separate refund events. "
            "No records are removed or financial adjustments "
            "made by this preview."
        )
