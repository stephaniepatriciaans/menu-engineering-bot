"""Regression tests for the POS classification preview."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from ui.data_upload import render_pos_classification_summary


def test_classification_preview_matches_generated_transaction_data():
    """UI counts must match classifications from source transaction data."""
    rng = np.random.default_rng(42)
    n = 100

    quantities = rng.integers(1, 20, size=n)
    amounts = rng.uniform(1.0, 100.0, size=n).round(2)
    statuses = np.full(n, "completed", dtype=object)

    quantities[::7] *= -1
    amounts[1::7] *= -1
    statuses[2::7] = "cancelled"
    statuses[3::7] = "refunded"

    df = pd.DataFrame({
        "quantity": quantities,
        "signed_total": amounts,
        "transaction_state": statuses,
    })

    original = df.copy(deep=True)

    # Independent expectations based on generated input signals.
    refund_mask = (
        (df["quantity"] < 0)
        | (df["signed_total"] < 0)
        | df["transaction_state"].eq("refunded")
    )

    cancelled_mask = (
        df["transaction_state"].eq("cancelled")
        & ~refund_mask
    )

    sale_mask = ~refund_mask & ~cancelled_mask

    conflict_mask = (
        (
            df["transaction_state"].eq("cancelled")
            & (
                (df["quantity"] < 0)
                | (df["signed_total"] < 0)
            )
        )
        | (
            (df["quantity"] > 0)
            & (df["signed_total"] < 0)
        )
        | (
            (df["quantity"] < 0)
            & (df["signed_total"] > 0)
        )
    )

    expected = {
        "Sales": int(sale_mask.sum()),
        "Refund Candidates": int(refund_mask.sum()),
        "Cancelled": int(cancelled_mask.sum()),
        "Classification Conflicts": int(conflict_mask.sum()),
        "Records Requiring Review": int(
            (refund_mask | cancelled_mask | conflict_mask).sum()
        ),
    }

    mapping: dict[str, str | None] = {
        "units_sold": "quantity",
    }

    with (
        patch(
            "ui.data_upload.st.expander",
            return_value=MagicMock(),
        ),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
    ):
        main_metrics = [MagicMock() for _ in range(3)]
        review_metrics = [MagicMock() for _ in range(2)]

        columns_mock.side_effect = [
            main_metrics,
            review_metrics,
        ]

        render_pos_classification_summary(
            df,
            mapping,
            status_column="transaction_state",
            amount_column="signed_total",
        )

        recorded = {
            call.args[0]: call.args[1]
            for column in main_metrics + review_metrics
            for call in column.metric.call_args_list
        }

        assert columns_mock.call_count == 2

        assert recorded == expected

    pd.testing.assert_frame_equal(df, original)


def test_classification_preview_skips_unmapped_fields():
    """Without classification fields, no preview should appear."""
    df = pd.DataFrame({
        "quantity": [1, 2],
    })

    mapping: dict[str, str | None] = {
        "units_sold": "quantity",
    }

    with patch("ui.data_upload.st.expander") as expander_mock:
        render_pos_classification_summary(
            df,
            mapping,
        )

        expander_mock.assert_not_called()
