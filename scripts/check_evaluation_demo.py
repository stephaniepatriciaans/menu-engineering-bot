"""Check synthetic dataset compatibility with the evaluation backend"""

from collections.abc import Mapping
from typing import Any

import pandas as pd

from model_evaluation import build_model_evaluation_report


def main() -> None:
    """Evaluate the synthetic dataset and display item-level metrics."""
    df = pd.read_csv("data/evaluation_ready_cafe.csv")

    report = build_model_evaluation_report(
        df,
        train_fraction=0.7,
    )

    coverage = report["coverage"]
    items = report["items"]

    # Narrow generic object values to their expected report types.
    if not isinstance(coverage, Mapping):
        raise TypeError("Evaluation coverage must be a mapping.")

    if not isinstance(items, list):
        raise TypeError("Evaluation items must be a list.")

    coverage_data: dict[str, Any] = dict(coverage)

    print("\nMODEL EVALUATION COVERAGE")
    print("-------------------------")
    print(f"Total items: {coverage_data['total_items']}")
    print(f"Evaluated items: {coverage_data['evaluated_items']}")
    print(
        "Insufficient evidence: "
        f"{coverage_data['insufficient_evidence_items']}"
    )
    print(
        "Evaluation coverage: "
        f"{coverage_data['evaluation_coverage_pct']}%"
    )

    results = pd.DataFrame.from_records(items)

    columns = [
        "item",
        "status",
        "reason",
        "baseline_mae",
        "elasticity_mae",
        "baseline_rmse",
        "elasticity_rmse",
    ]

    print("\nITEM-LEVEL RESULTS")
    print("-------------------------")
    print(results[columns].to_string(index=False))


if __name__ == "__main__":
    main()
