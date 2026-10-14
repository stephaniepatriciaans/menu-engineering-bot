"""Streamlit dashboard for historical demand model evaluation."""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from model_evaluation import (
    build_model_evaluation_report,
    evaluate_historical_average,
)

REQUIRED_COLUMNS = {"date", "item", "price", "units_sold"}


def prepare_evaluation_table(item_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare readable evaluation results without changing source data.

    Converts internal status codes into user-friendly labels,
    preserves numeric metrics, and retains missing values.
    """
    display_df = item_df.copy()

    status_labels = {
        "evaluated": "Both Models Evaluated",
        "baseline_only": "Baseline Only",
        "insufficient_evidence": "Insufficient Data",
    }

    if "status" in display_df.columns:
        display_df["status"] = (
            display_df["status"]
            .map(status_labels)
            .fillna(display_df["status"])
        )

    display_df = display_df.rename(
        columns={
            "item": "Menu Item",
            "status": "Evaluation Status",
            "reason": "Reason",
            "train_days": "Training Days",
            "test_days": "Test Days",
            "baseline_mae": "Baseline MAE",
            "baseline_rmse": "Baseline RMSE",
            "baseline_wape": "Baseline WAPE (%)",
            "elasticity_mae": "Elasticity MAE",
            "elasticity_rmse": "Elasticity RMSE",
            "elasticity_wape": "Elasticity WAPE (%)",
            "elasticity_lower_mae": "Elasticity Lower MAE",
            "price_extrapolation": "Price Extrapolation",
        }
    )

    numeric_columns = [
        "Baseline MAE",
        "Baseline RMSE",
        "Baseline WAPE (%)",
        "Elasticity MAE",
        "Elasticity RMSE",
        "Elasticity WAPE (%)",
    ]

    for column in numeric_columns:
        if column in display_df.columns:
            display_df[column] = pd.to_numeric(
                display_df[column],
                errors="coerce",
            )

    return display_df


def _dataset_fingerprint(df: pd.DataFrame) -> str:
    """Identify changes to the data used by forecast evaluation."""
    relevant = df[["date", "item", "price", "units_sold"]]
    hashes = pd.util.hash_pandas_object(relevant, index=False)
    return hashlib.sha256(hashes.to_numpy().tobytes()).hexdigest()


def _percentage(value: float | None) -> str:
    """Format optional coverage values without implying accuracy."""
    if value is None:
        return "N/A"
    return f"{float(value):.1f}%"


def render_model_evaluation(df: pd.DataFrame) -> None:
    """Display baseline and two-model backtesting coverage separately."""
    st.header("Model Evaluation")
    st.caption(
        "Evaluate historical-average demand forecasts independently, and "
        "compare against elasticity-based forecasts when pricing evidence permits."
    )
    st.info(
        "This is chronological historical backtesting, not a guarantee "
        "of future demand or a causal estimate of price changes."
    )

    if df is None or df.empty:
        st.warning("No sales data is available for evaluation.")
        return

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        st.warning(
            "Model evaluation requires these missing fields: "
            + ", ".join(sorted(missing))
        )
        return

    context_id = _dataset_fingerprint(df)
    if "model_evaluation_report" not in st.session_state:
        st.session_state["model_evaluation_report"] = None
    if "model_evaluation_context" not in st.session_state:
        st.session_state["model_evaluation_context"] = None

    train_pct = st.slider(
        "Training data (%)",
        min_value=60,
        max_value=80,
        value=70,
        step=5,
        key="model_evaluation_train_pct",
        help="Earlier dates are training data; later recorded dates are held out.",
    )
    evaluation_id = f"{context_id}:{train_pct}"
    if st.session_state["model_evaluation_context"] != evaluation_id:
        st.session_state["model_evaluation_report"] = None
        st.session_state["model_evaluation_context"] = None

    if st.button("Run Model Evaluation", key="run_model_evaluation", type="primary"):
        with st.spinner("Evaluating historical demand predictions..."):
            try:
                report = build_model_evaluation_report(
                    df, train_fraction=train_pct / 100.0
                )
            except ValueError as exc:
                st.error(f"Model evaluation could not run: {exc}")
                return
        st.session_state["model_evaluation_report"] = report
        st.session_state["model_evaluation_context"] = evaluation_id

    report = st.session_state["model_evaluation_report"]
    if report is None:
        st.caption("Select a training fraction and click 'Run Model Evaluation'.")
        return

    coverage = report["coverage"]
    assert isinstance(coverage, dict)
    item_df = pd.DataFrame(report["items"])

    total = int(coverage["total_items"] or 0)
    compared = int(coverage["evaluated_items"] or 0)
    baseline_only = int(coverage["baseline_only_items"] or 0)
    baseline_count = int(coverage["baseline_evaluated_items"] or 0)
    insufficient = int(coverage["insufficient_evidence_items"] or 0)
    better_count = int(coverage["elasticity_better_items"] or 0)

    st.subheader("Evaluation Coverage")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Items", total)
    col2.metric("Baseline Evaluated", baseline_count)
    col3.metric("Two-Model Comparisons", compared)

    col4, col5, col6 = st.columns(3)
    col4.metric("Baseline Only", baseline_only)
    col5.metric("Insufficient Evidence", insufficient)
    col6.metric("Fully Evaluated", compared)

    coverage_col1, coverage_col2 = st.columns(2)
    coverage_col1.metric(
        "Baseline Coverage", _percentage(coverage["baseline_coverage_pct"])
    )
    coverage_col2.metric(
        "Comparison Coverage", _percentage(coverage["evaluation_coverage_pct"])
    )
    st.caption(
        "Coverage is the share of items eligible for a historical evaluation; "
        "it is not forecast accuracy. Two-model coverage is a subset of "
        "baseline coverage."
    )

    if baseline_count == 0:
        st.warning(
            "No items have sufficient observations for baseline backtesting. "
            "No forecast error metrics are available."
        )
    elif compared == 0:
        st.info(
            "Historical-average baseline errors are available, but no item "
            "has enough historical pricing evidence for a supported "
            "two-model comparison."
        )
    else:
        st.success(
            f"{compared} of {total} items support a baseline-versus-elasticity "
            "comparison. Baseline-only items are not included in the comparison."
        )

    if baseline_count > 0:
        st.subheader("Baseline Forecast Error")
        st.caption(
            "Historical-average forecast errors for all baseline-eligible "
            "items. MAE and RMSE are in daily units sold; WAPE is a percentage. "
            "These are unweighted averages of item-level metrics."
        )
        eligible_baseline = item_df.loc[
            item_df["status"].isin(["evaluated", "baseline_only"])
        ].copy()
        base_mae = pd.to_numeric(
            eligible_baseline["baseline_mae"], errors="coerce"
        ).mean()
        base_rmse = pd.to_numeric(
            eligible_baseline["baseline_rmse"], errors="coerce"
        ).mean()
        base_wape = pd.to_numeric(
            eligible_baseline["baseline_wape"], errors="coerce"
        ).mean()
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Mean Baseline MAE", f"{base_mae:.2f}")
        metric2.metric("Mean Baseline RMSE", f"{base_rmse:.2f}")
        metric3.metric("Mean Baseline WAPE", f"{base_wape:.2f}%")

    if compared > 0:
        st.subheader("Forecast Error Comparison")
        st.caption(
            "Mean item-level MAE across the same two-model-eligible items. "
            "Lower error is better; baseline-only items are excluded here."
        )
        eligible_comparison = item_df.loc[
            item_df["status"] == "evaluated"
        ].copy()
        comparison = eligible_comparison[
            ["baseline_mae", "elasticity_mae"]
        ].apply(pd.to_numeric, errors="coerce")
        means = comparison.mean()
        chart_df = pd.DataFrame(
            {
                "Model": ["Historical average", "Elasticity-based"],
                "Mean item MAE": [
                    means["baseline_mae"],
                    means["elasticity_mae"],
                ],
            }
        ).set_index("Model")
        st.bar_chart(chart_df)
        better_pct = coverage["elasticity_better_pct"]
        st.caption(
            f"Elasticity had lower MAE for {better_count} of {compared} "
            f"compared items ({_percentage(better_pct)})."
        )
        
        
    # ============================================================
    # ITEM-LEVEL RESULTS
    # ============================================================
    st.subheader("Item-Level Results")

    if not item_df.empty:
        display_df = prepare_evaluation_table(item_df)

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Menu Item": st.column_config.TextColumn(
                    "Menu Item",
                    width="medium",
                ),
                "Evaluation Status": st.column_config.TextColumn(
                    "Evaluation Status",
                    width="medium",
                ),
                "Reason": st.column_config.TextColumn(
                    "Reason",
                    width="large",
                ),
                "Baseline MAE": st.column_config.NumberColumn(
                    "Baseline MAE",
                    format="%.2f",
                ),
                "Baseline RMSE": st.column_config.NumberColumn(
                    "Baseline RMSE",
                    format="%.2f",
                ),
                "Baseline WAPE (%)": st.column_config.NumberColumn(
                    "Baseline WAPE (%)",
                    format="%.2f",
                ),
                "Elasticity MAE": st.column_config.NumberColumn(
                    "Elasticity MAE",
                    format="%.2f",
                ),
                "Elasticity RMSE": st.column_config.NumberColumn(
                    "Elasticity RMSE",
                    format="%.2f",
                ),
                "Elasticity WAPE (%)": st.column_config.NumberColumn(
                    "Elasticity WAPE (%)",
                    format="%.2f",
                ),
            },
        )

        st.caption(
            "Baseline Only means baseline forecast metrics are "
            "available, but elasticity evaluation is unsupported. "
            "Blank metric cells indicate unavailable values, not zero."
        )

    else:
        st.info("No item-level results are available.")


    # ============================================================
    # ACTUAL VS. PREDICTED DEMAND
    # ============================================================
    if baseline_count > 0:
        st.subheader("Actual vs. Predicted Demand")

        st.caption(
            "Compare recorded daily sales with the historical-average "
            "forecast on held-out dates. Only earlier observations "
            "are used to fit the baseline."
        )

        eligible_items = item_df.loc[
            item_df["status"].isin(
                ["evaluated", "baseline_only"]
            ),
            "item",
        ].astype(str).tolist()

        selected_item = st.selectbox(
            "Select menu item",
            options=eligible_items,
            key="evaluation_chart_item",
        )

        selected_data = df.loc[
            df["item"].astype(str) == selected_item
        ].copy()

        
        try:
            result = evaluate_historical_average(
                selected_data,
                train_fraction=train_pct / 100.0,
            )

            # Read the exact holdout results from the backend.
            test_dates_value = result["test_dates"]
            actual_values = result["actual"]
            prediction_values = result["predictions"]

            # Validate the returned types.
            if not isinstance(test_dates_value, list):
                raise TypeError(
                    "Test dates must be returned as a list."
                )

            if not isinstance(actual_values, list):
                raise TypeError(
                    "Actual demand must be returned as a list."
                )

            if not isinstance(prediction_values, list):
                raise TypeError(
                    "Predictions must be returned as a list."
                )

            # Ensure date values are strings.
            if not all(
                isinstance(value, str)
                for value in test_dates_value
            ):
                raise TypeError(
                    "Test dates must contain strings."
                )

            # Convert the values into typed numeric arrays.
            test_dates = pd.to_datetime(
                [str(value) for value in test_dates_value],
                format="%Y-%m-%d",
                errors="raise",
            )

            actual = pd.to_numeric(
                pd.Series(
                    [float(value) for value in actual_values]
                ),
                errors="raise",
            )

            predicted = pd.to_numeric(
                pd.Series(
                    [float(value) for value in prediction_values]
                ),
                errors="raise",
            )

            # Verify that dates and predictions align.
            if not (
                len(test_dates) == len(actual) == len(predicted)
            ):
                raise ValueError(
                    "Forecast dates and predictions do not align."
                )

            if len(test_dates) == 0:
                raise ValueError(
                    "No held-out dates are available."
                )

            chart_df = pd.DataFrame({
                "Date": test_dates,
                "Actual Demand": actual.to_numpy(),
                "Baseline Prediction": predicted.to_numpy(),
            })

            st.line_chart(
                chart_df.set_index("Date"),
                height=350,
            )

            test_days = len(test_dates)

            st.caption(
                f"Showing {test_days} held-out recorded dates "
                f"for {selected_item}. "
                "Missing transaction dates are not treated "
                "as zero sales."
            )

        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            st.warning(
                f"Unable to display demand forecast: {exc}"
            )

    with st.expander("Evaluation Methodology"):
        st.write(
            "The evaluation splits recorded dates chronologically. "
            "The baseline predicts from historical-average daily demand; "
            "the elasticity model uses a log-log price-demand relationship."
        )
        st.write(
            "Both models use only training-period sales quantities for fitting. "
            "The elasticity forecast receives observed test-period prices as "
            "known inputs. Missing transaction dates are not treated as zero sales."
        )
        st.write(
            "Baseline-only errors measure demand forecasting performance, "
            "not responsiveness to price changes. The comparison chart "
            "includes only items where both models can be evaluated."
        )
        st.json(report["methodology"])

    clean_items = json.loads(
        item_df.to_json(orient="records", date_format="iso")
    )
    export_report = {**report, "items": clean_items}
    json_bytes = json.dumps(
        export_report, indent=2, allow_nan=False, default=str
    ).encode("utf-8")
    csv_bytes = item_df.to_csv(index=False).encode("utf-8")

    st.subheader("Download Evaluation Results")
    download_col1, download_col2 = st.columns(2)
    with download_col1:
        st.download_button(
            "Download Evaluation Report (.json)",
            data=json_bytes,
            file_name="model_evaluation_report.json",
            mime="application/json",
            width="stretch",
        )
    with download_col2:
        st.download_button(
            "Download Item Results (.csv)",
            data=csv_bytes,
            file_name="model_evaluation_items.csv",
            mime="text/csv",
            width="stretch",
        )
    st.caption(
        "These results evaluate historical predictions only. Eligibility "
        "and performance may change across datasets and training fractions."
    )