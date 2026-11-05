"""Optional POS sales-reconciliation workflow, separate from core analytics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pos.export_validation import audit_pos_export
from pos.reconciliation import reconcile_pos_sales, summarize_reconciled_sales


def render_pos_reconciliation(
    raw_df: pd.DataFrame,
    mapping: dict[str, str | None],
    *,
    price_basis: str,
    status_column: str | None,
    amount_column: str | None,
    line_discount_column: str | None,
    percent_column: str | None,
) -> dict[str, object] | None:
    """Show reviewed eligible-sales revenue without changing forecast inputs."""
    if not mapping.get("price") or not mapping.get("units_sold"):
        return None
    with st.expander("Advanced POS discount & sales reconciliation", expanded=False):
        st.caption(
            "Optional accounting preview. Negative-quantity rows, cancelled rows and "
            "refund candidates require separate review; they are NOT deducted "
            "to produce net revenue. Taxes, tips and service fees are not included."
        )
        excluded = {
            column for column in (
                *mapping.values(), status_column, amount_column,
                line_discount_column, percent_column,
            ) if column is not None
        }
        def select_column(label: str, key: str) -> str | None:
            choices = [None, *[str(c) for c in raw_df.columns if c not in excluded]]
            selected = st.selectbox(label, choices, format_func=lambda x: x or "Not mapped", key=key)
            if selected:
                excluded.add(selected)
            return selected

        per_unit = select_column("Per-unit discount amount (optional)", "pos_per_unit_discount_col")
        order_id = select_column("Order ID (optional)", "pos_order_id_col")
        order_discount = select_column("Order-level discount total (optional)", "pos_order_discount_col")
        order_percent = select_column("Order-level percentage discount (optional)", "pos_order_percent_col")
        stacking = st.selectbox(
            "How should overlapping line discounts be handled?",
            ["exclusive", "sequential"],
            help="Exclusive rejects overlapping line discounts. Sequential applies the percentage first, then cash discounts; order discounts are last.",
            key="pos_discount_stacking",
        )
        verified = st.checkbox(
            "I have verified this POS export's price, transaction-status and discount conventions",
            value=False,
            key="pos_conventions_verified",
        )
        source_fields = {
            "price": mapping["price"], "units_sold": mapping["units_sold"],
            "status": status_column, "amount": amount_column,
            "line_discount": line_discount_column, "percent": percent_column,
            "per_unit": per_unit, "order_id": order_id,
            "order_discount": order_discount, "order_percent": order_percent,
        }
        canonical = pd.DataFrame(index=raw_df.index)
        for name, column in source_fields.items():
            if column is not None:
                canonical[name] = raw_df[column]
        try:
            rows = reconcile_pos_sales(
                canonical,
                price_basis=price_basis,
                status_column="status" if status_column else None,
                amount_column="amount" if amount_column else None,
                line_discount_column="line_discount" if line_discount_column else None,
                percent_column="percent" if percent_column else None,
                per_unit_discount_column="per_unit" if per_unit else None,
                order_id_column="order_id" if order_id else None,
                order_discount_column="order_discount" if order_discount else None,
                order_percent_column="order_percent" if order_percent else None,
                stacking=stacking,
                verified_conventions=verified,
            )
        except (ValueError, TypeError) as exc:
            st.warning(f"Reconciliation preview unavailable: {exc}")
            return None
        summary = summarize_reconciled_sales(rows)
        a, b, c = st.columns(3)
        a.metric("Eligible sale rows", summary["eligible_sale_rows"])
        b.metric("Refund candidates (review)", summary["refund_candidates"])
        c.metric("Cancelled (review)", summary["cancelled_rows"])
        revenue = summary["eligible_sales_revenue"]
        if revenue is None:
            st.info("Eligible-sales revenue unavailable until the price basis is known.")
        else:
            st.metric("Eligible-sales revenue (not net revenue)", f"${revenue:,.2f}")
            if summary["conventions_verified"]:
                st.success("Declared conventions verified by the operator. Refund accounting remains unverified.")
            else:
                st.warning("Preview only: source accounting conventions have not been confirmed.")
        st.caption("This preview does not replace the existing dashboard KPI, model-evaluation prices or pricing recommendations.")

        st.divider()
        st.markdown("**Independent POS settlement audit (required for financial integration)**")
        st.caption(
            "Compare the complete export against a separately generated pre-tax "
            "net item-sales total. This is not inferred from the uploaded rows."
        )
        audit_enabled = st.checkbox(
            "Compare with an independent POS settlement summary",
            value=False,
            key="pos_financial_audit_enabled",
        )
        if audit_enabled:
            event_choices = [None, *[str(col) for col in raw_df.columns if col not in excluded]]
            event_id = st.selectbox(
                "Unique transaction event ID", event_choices,
                format_func=lambda col: col or "Not mapped",
                key="pos_financial_event_id",
            )
            convention = st.selectbox(
                "Refund representation confirmed by the POS provider",
                ["unknown", "separate_signed_events", "status_only_original"],
                key="pos_financial_refund_convention",
            )
            amount_basis = st.selectbox(
                "Signed amount basis", ["unknown", "pre_tax_sales"],
                key="pos_financial_amount_basis",
            )
            expected_net = st.text_input(
                "Independent pre-tax net item-sales total",
                value="", placeholder="e.g. 1250.00",
                key="pos_financial_expected_net",
            )
            if not expected_net.strip():
                st.info("Enter the independently reported total to run the audit.")
            else:
                audit_frame = canonical.copy()
                if event_id is not None:
                    audit_frame["event_id"] = raw_df[event_id]
                try:
                    audit = audit_pos_export(
                        audit_frame,
                        price_basis=price_basis,
                        amount_column="amount" if amount_column else None,
                        status_column="status" if status_column else None,
                        event_id_column="event_id" if event_id else None,
                        refund_convention=convention,
                        source_amount_basis=amount_basis,
                        expected_net_sales=expected_net.strip(),
                        verified_conventions=verified,
                        line_discount_column="line_discount" if line_discount_column else None,
                        percent_column="percent" if percent_column else None,
                        per_unit_discount_column="per_unit" if per_unit else None,
                        order_id_column="order_id" if order_id else None,
                        order_discount_column="order_discount" if order_discount else None,
                        order_percent_column="order_percent" if order_percent else None,
                        stacking=stacking,
                    )
                except (ValueError, TypeError) as exc:
                    st.warning(f"Independent settlement audit unavailable: {exc}")
                else:
                    if audit.outcome == "matched":
                        st.success("POS settlement matched to the cent for this full export.")
                        # Only an independently matched audit unlocks these rows.
                        summary["audited_rows"] = rows
                        summary["matched_audit"] = audit
                    else:
                        st.warning(f"Settlement audit: {audit.outcome}. Financial integration remains disabled.")
                        for finding in audit.findings:
                            st.caption(f"• {finding}")
        return summary
