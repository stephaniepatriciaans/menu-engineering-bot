"""Streamlit UI for optional menu cost handling."""

import pandas as pd
import streamlit as st

from data_adapter import (
    NOT_AVAILABLE,
    read_delimited_csv,
    detect_column_mapping,
    merge_cost_reference,
    apply_estimated_cost_percentage,
)


def render_cost_settings(
    canonical_df: pd.DataFrame,
) -> tuple[pd.DataFrame, str, bool]:
    """Render optional cost controls and return updated cost information.

    Returns:
        canonical_df: Dataset with original, merged, or assumed costs.
        cost_basis: Description of the source of cost information.
        cost_is_assumption: Whether costs use a scenario assumption.
    """

    cost_basis = (
        "provided_cost_column"
        if canonical_df["unit_cost"].notna().all()
        else "unavailable"
    )

    cost_is_assumption = False

    with st.expander("💰 Optional Cost Settings", expanded=False):

        if not canonical_df["unit_cost"].notna().all():

            st.write(
                "Unit cost is not fully available. "
                "Only provide real cost data or explicitly choose "
                "a scenario assumption."
            )

            cost_option = st.radio(
                "Cost handling",
                [
                    "Continue without unit cost",
                    "Upload a separate menu-cost CSV",
                    "Scenario analysis using estimated cost percentage",
                ],
            )

            if cost_option == "Upload a separate menu-cost CSV":

                cost_upload = st.file_uploader(
                    "Upload menu-cost CSV",
                    type=["csv"],
                    key="cost_upload",
                )

                if cost_upload is not None:
                    try:
                        cost_upload.seek(0)

                        raw_cost_df = read_delimited_csv(
                            cost_upload
                        )

                        cost_detected = detect_column_mapping(
                            raw_cost_df.columns
                        )

                        cost_options = [
                            NOT_AVAILABLE,
                            *[str(c) for c in raw_cost_df.columns],
                        ]

                        c1, c2 = st.columns(2)

                        item_default = (
                            cost_detected.get("item")
                            or NOT_AVAILABLE
                        )

                        cost_default = (
                            cost_detected.get("unit_cost")
                            or NOT_AVAILABLE
                        )

                        cost_item_col = c1.selectbox(
                            "Cost file: Item",
                            cost_options,
                            index=(
                                cost_options.index(item_default)
                                if item_default in cost_options
                                else 0
                            ),
                        )

                        cost_value_col = c2.selectbox(
                            "Cost file: Unit Cost",
                            cost_options,
                            index=(
                                cost_options.index(cost_default)
                                if cost_default in cost_options
                                else 0
                            ),
                        )

                        if (
                            cost_item_col != NOT_AVAILABLE
                            and cost_value_col != NOT_AVAILABLE
                        ):

                            canonical_df, cost_warnings = (
                                merge_cost_reference(
                                    canonical_df,
                                    raw_cost_df,
                                    cost_item_col,
                                    cost_value_col,
                                )
                            )

                            cost_basis = "separate_menu_cost_csv"

                            for warning in cost_warnings:
                                st.warning(warning)

                    except Exception as exc:
                        st.error(
                            f"Could not use the cost CSV: {exc}"
                        )

            elif (
                cost_option
                == "Scenario analysis using estimated cost percentage"
            ):

                estimated_pct = st.slider(
                    "Estimated cost as % of price",
                    5,
                    95,
                    30,
                    1,
                )

                canonical_df = apply_estimated_cost_percentage(
                    canonical_df,
                    estimated_pct / 100,
                )

                cost_basis = (
                    f"assumption_{estimated_pct}_percent_of_price"
                )

                cost_is_assumption = True

                st.warning(
                    f"Scenario assumption enabled: unit cost is modeled "
                    f"as {estimated_pct}% of selling price. "
                    "These are not actual business costs."
                )

        else:
            st.success(
                "Complete unit cost data is available. "
                "Profit-based analysis can use the provided costs."
            )

    return canonical_df, cost_basis, cost_is_assumption
