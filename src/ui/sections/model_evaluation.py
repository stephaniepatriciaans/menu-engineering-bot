"""Streamlit dashboard for historical demand model evaluation"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from model_evaluation import build_model_evaluation_report

REQUIRED_COLUMNS = {"date", "item", "price", "units_sold"}


def _dataset_fingerprint(df: pd.DataFrame) -> str:
    """Identify changes to the data used by forecast evaluation."""
    relevant = df[["date", "item", "price", "units_sold"]]
    hashes = pd.util.hash_pandas_object(
        relevant,
        index=False,
    )

    return hashlib.sha256(
        hashes.to_numpy().tobytes()
    ).hexdigest()


def render_model_evaluation(df: pd.DataFrame) -> None:
    """Render reproducible historical forecast evaluations."""
    st.header("Model Evaluation")

    st.caption(
        "Compare historical-average demand predictions with "
        "elasticity-based predictions on later recorded sales dates."
    )

    st.info(
        "This is historical backtesting, not a guarantee of future "
        "demand or a causal estimate of the effect of price changes."
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

    # # Changing the filtered dataset invalidates previous results.
    # if st.session_state["model_evaluation_context"] != context_id:
    #     st.session_state["model_evaluation_report"] = None
    #     st.session_state["model_evaluation_context"] = None

    train_pct = st.slider(
        "Training data (%)",
        min_value=60,
        max_value=80,
        value=70,
        step=5,
        key="model_evaluation_train_pct",
        help=(
            "Earlier dates are used for training. "
            "Later dates are reserved for evaluation."
        ),
    )

    evaluation_id = f"{context_id}:{train_pct}"

    if (
        st.session_state["model_evaluation_context"]
        != evaluation_id
    ):
        st.session_state["model_evaluation_report"] = None
        st.session_state["model_evaluation_context"] = None

    if st.button(
        "Run Model Evaluation",
        key="run_model_evaluation",
        type="primary",
    ):
        with st.spinner("Evaluating historical demand predictions..."):
            try:
                report = build_model_evaluation_report(
                    df,
                    train_fraction=train_pct / 100.0,
                )
            except ValueError as exc:
                st.error(f"Model evaluation could not run: {exc}")
                return

        st.session_state["model_evaluation_report"] = report
        st.session_state["model_evaluation_context"] = evaluation_id

    report = st.session_state["model_evaluation_report"]

    if report is None:
        st.caption(
            "Select a training fraction and click "
            "'Run Model Evaluation' to view results."
        )
        return

    coverage = report["coverage"]
    assert isinstance(coverage, dict)

    total = int(coverage["total_items"] or 0)
    evaluated_count = int(coverage["evaluated_items"] or 0)
    insufficient = int(
        coverage["insufficient_evidence_items"] or 0
    )

    coverage_pct = coverage["evaluation_coverage_pct"]
    better_count = int(
        coverage["elasticity_better_items"] or 0
    )

    st.subheader("Evaluation Coverage")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Items", total)
    col2.metric("Evaluated Items", evaluated_count)
    col3.metric("Insufficient Evidence", insufficient)
    col4.metric(
        "Evaluation Coverage",
        (
            f"{float(coverage_pct):.1f}%"
            if coverage_pct is not None
            else "N/A"
        ),
    )

    item_df = pd.DataFrame(report["items"])

    if evaluated_count == 0:
        st.warning(
            "No items have sufficient historical evidence for "
            "a supported forecast comparison. "
            "No model accuracy claims can be made."
        )
    else:
        evaluated = item_df.loc[
            item_df["status"] == "evaluated"
        ].copy()

        st.subheader("Forecast Error Comparison")

        st.caption(
            "Lower MAE and RMSE are better. The chart shows "
            "unweighted averages of item-level errors among "
            "eligible items only."
        )

        metric_columns = [
            "baseline_mae",
            "elasticity_mae",
        ]

        comparison = evaluated[metric_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )

        average_mae = comparison.mean()

        chart_df = pd.DataFrame(
            {
                "Model": [
                    "Historical average",
                    "Elasticity-based",
                ],
                "Mean item MAE": [
                    average_mae["baseline_mae"],
                    average_mae["elasticity_mae"],
                ],
            }
        ).set_index("Model")

        st.bar_chart(chart_df)

        better_pct = coverage["elasticity_better_pct"]

        st.caption(
            f"Elasticity model had lower MAE for "
            f"{better_count} of {evaluated_count} evaluated items"
            + (
                f" ({float(better_pct):.1f}%)."
                if better_pct is not None
                else "."
            )
        )

    st.subheader("Item-Level Results")

    if evaluated_count == 0:
        st.info(
            "Model evaluation requires sufficient historical "
            "price variation for each item. At least two distinct "
            "training prices are required. No accuracy metrics "
            "are available for this dataset."
        )

        display_df = item_df[
            ["item", "status", "reason"]
        ].rename(
            columns={
                "item": "Menu Item",
                "status": "Evaluation Status",
                "reason": "Reason",
            }
        )

    else:
        display_df = item_df.rename(
            columns={
                "item": "Menu Item",
                "status": "Evaluation Status",
                "reason": "Reason",
                "baseline_mae": "Baseline MAE",
                "elasticity_mae": "Elasticity MAE",
                "baseline_rmse": "Baseline RMSE",
                "elasticity_rmse": "Elasticity RMSE",
                "baseline_wape": "Baseline WAPE",
                "elasticity_wape": "Elasticity WAPE",
            }
        )

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )

    with st.expander("Evaluation Methodology"):
        st.write(
            "Data is split chronologically. The baseline uses "
            "historical-average demand, while the candidate "
            "uses a log-log elasticity relationship."
        )
        st.write(
            "The evaluation uses observed prices from the "
            "test period. Missing transaction dates are not "
            "assumed to be zero-sales days."
        )
        st.write(
            "Items without sufficient evidence are excluded "
            "from model accuracy comparisons."
        )
        st.json(report["methodology"])

    # Convert missing pandas values into JSON nulls.
    clean_items = json.loads(
        item_df.to_json(
            orient="records",
            date_format="iso",
        )
    )

    export_report = {
        **report,
        "items": clean_items,
    }

    json_bytes = json.dumps(
        export_report,
        indent=2,
        allow_nan=False,
        default=str,
    ).encode("utf-8")

    csv_bytes = item_df.to_csv(
        index=False,
    ).encode("utf-8")

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
        "These results evaluate historical predictions only. "
        "Eligibility and performance may change with different "
        "datasets, dates, and training fractions."
    )
