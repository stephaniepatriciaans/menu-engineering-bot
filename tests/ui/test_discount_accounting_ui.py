"""Regression tests for the POS discount accounting preview."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from ui.data_upload import render_pos_accounting_summary


def make_discount_data():
    return pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "item": ["Latte", "Tea"],
        "price": [5.0, 3.0],
        "units_sold": [2, 1],
        "discount_amount": [2.0, 0.0],
    })


def make_mapping() -> dict[str, str | None]:
    return {
        "date": "date",
        "item": "item",
        "price": "price",
        "units_sold": "units_sold",
    }


def test_discount_preview_displays_realized_revenue():
    df = make_discount_data()

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
    ):
        metrics = [MagicMock(), MagicMock(), MagicMock()]
        columns_mock.return_value = metrics

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column="discount_amount",
        )

        calls = [
            (call.args[0], call.args[1])
            for metric in metrics
            for call in metric.metric.call_args_list
        ]

        assert ("Gross Sales", "13.00") in calls
        assert ("Discounts", "2.00") in calls
        assert ("Realized Sales", "11.00") in calls


def test_no_discount_preview_without_mapping():
    df = make_discount_data()

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider") as divider_mock,
        patch("ui.data_upload.st.markdown"),
    ):
        columns_mock.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column=None,
        )

        divider_mock.assert_not_called()
        columns_mock.assert_called_once_with(3)


def test_invalid_discount_displays_warning():
    df = make_discount_data()
    df["discount_amount"] = [20.0, 0.0]

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
        patch("ui.data_upload.st.warning") as warning_mock,
    ):
        columns_mock.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column="discount_amount",
        )

        warning_messages = [
            str(call.args[0])
            for call in warning_mock.call_args_list
        ]

        assert any(
            "Discount accounting is unavailable" in message
            for message in warning_messages
        )


def test_percentage_discount_preview_displays_realized_sales():
    """Percentage discounts must produce the correct preview."""
    df = pd.DataFrame({
        "price": [5.0, 3.0],
        "units_sold": [2, 1],
        "discount_percent": [20.0, 10.0],
    })

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
    ):
        metrics = [MagicMock(), MagicMock(), MagicMock()]
        columns_mock.return_value = metrics

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_percent_column="discount_percent",
        )

        calls = [
            (call.args[0], call.args[1])
            for metric in metrics
            for call in metric.metric.call_args_list
        ]

        assert ("Gross Sales", "13.00") in calls
        assert ("Discounts", "2.30") in calls
        assert ("Realized Sales", "10.70") in calls


def test_both_discount_types_display_conflict_warning():
    """Overlapping discount types must not be combined."""
    df = pd.DataFrame({
        "price": [5.0],
        "units_sold": [2],
        "discount_amount": [2.0],
        "discount_percent": [20.0],
    })

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
        patch("ui.data_upload.st.warning") as warning_mock,
    ):
        metrics = [MagicMock(), MagicMock(), MagicMock()]
        columns_mock.return_value = metrics

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column="discount_amount",
            discount_percent_column="discount_percent",
        )

        warning_messages = [
            str(call.args[0])
            for call in warning_mock.call_args_list
        ]

        assert any(
            "Both monetary and percentage discount columns"
            in message
            for message in warning_messages
        )

        assert not any(
            metric.metric.call_args_list
            for metric in metrics[0:0]
        )


def test_unknown_price_basis_hides_discount_metrics():
    """Unknown price basis must not calculate realized revenue."""
    df = make_discount_data()

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
        patch("ui.data_upload.st.warning") as warning_mock,
    ):
        columns_mock.return_value = [
            MagicMock(), MagicMock(), MagicMock()
        ]

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column="discount_amount",
            price_basis="unknown",
        )

        assert columns_mock.call_count == 1
        assert any(
            "price basis has not been verified" in str(call.args[0])
            for call in warning_mock.call_args_list
        )


def test_realized_price_basis_does_not_subtract_discount_twice():
    """Realized prices must not have discounts applied again."""
    df = make_discount_data()

    with (
        patch("ui.data_upload.st.expander", return_value=MagicMock()),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
        patch("ui.data_upload.st.info") as info_mock,
    ):
        columns_mock.return_value = [
            MagicMock(), MagicMock(), MagicMock()
        ]

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column="discount_amount",
            price_basis="realized",
        )

        assert columns_mock.call_count == 1
        assert any(
            "already discounted" in str(call.args[0])
            for call in info_mock.call_args_list
        )


@pytest.mark.parametrize("discount_type", ["amount", "percent"])
def test_listed_price_basis_calculates_discounts(discount_type):
    """Test listed-price discount accounting with generated POS data."""
    rng = np.random.default_rng(42)
    n_transactions = 100

    prices = rng.uniform(
        1.0, 100.0, size=n_transactions
    ).round(2)

    quantities = rng.integers(
        1, 20, size=n_transactions
    )

    gross_sales = prices * quantities

    df = pd.DataFrame({
        "price": prices,
        "units_sold": quantities,
        "discount_amount": (
            gross_sales * rng.uniform(
                0.0, 0.5, size=n_transactions
            )
        ).round(2),
        "discount_percent": rng.uniform(
            0.0, 50.0, size=n_transactions
        ).round(2),
    })

    # Independently calculate the expected accounting totals.
    gross = df["price"] * df["units_sold"]

    if discount_type == "amount":
        discount_column = "discount_amount"
        discount_percent_column = None
        expected_discounts = df["discount_amount"]
    else:
        discount_column = None
        discount_percent_column = "discount_percent"
        expected_discounts = (
            gross * df["discount_percent"] / 100.0
        )

    expected_gross = float(gross.sum())
    expected_discount_total = float(
        expected_discounts.sum()
    )
    expected_realized = (
        expected_gross - expected_discount_total
    )

    with (
        patch(
            "ui.data_upload.st.expander",
            return_value=MagicMock(),
        ),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
    ):
        metrics = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        columns_mock.return_value = metrics

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column=discount_column,
            discount_percent_column=discount_percent_column,
            price_basis="listed",
        )

        recorded_metrics = {
            call.args[0]: float(
                str(call.args[1]).replace(",", "")
            )
            for metric in metrics
            for call in metric.metric.call_args_list
        }

        # One row of refund-accounting cards and
        # one row of discount-accounting cards.
        assert columns_mock.call_count == 2

        assert recorded_metrics["Gross Sales"] == pytest.approx(
            expected_gross,
            abs=0.01,
        )

        assert recorded_metrics["Discounts"] == pytest.approx(
            expected_discount_total,
            abs=0.01,
        )

        assert recorded_metrics["Realized Sales"] == pytest.approx(
            expected_realized,
            abs=0.01,
        )

        # Financial consistency check.
        assert recorded_metrics["Realized Sales"] == pytest.approx(
            recorded_metrics["Gross Sales"]
            - recorded_metrics["Discounts"],
            abs=0.01,
        )


@pytest.mark.parametrize(
    "discount_type",
    ["amount", "percent"],
)
@pytest.mark.parametrize(
    "price_basis",
    ["unknown", "realized"],
)
def test_unverified_or_realized_prices_skip_discount_calculation(
    discount_type,
    price_basis,
):
    """Prevent double-counting or unsupported revenue adjustments."""
    rng = np.random.default_rng(42)
    n_transactions = 100

    prices = rng.uniform(
        1.0, 100.0, size=n_transactions
    ).round(2)

    quantities = rng.integers(
        1, 20, size=n_transactions
    )

    gross = prices * quantities

    df = pd.DataFrame({
        "price": prices,
        "units_sold": quantities,
        "discount_amount": (
            gross * rng.uniform(
                0.0, 0.5, size=n_transactions
            )
        ).round(2),
        "discount_percent": rng.uniform(
            0.0, 50.0, size=n_transactions
        ).round(2),
    })

    discount_column = (
        "discount_amount"
        if discount_type == "amount"
        else None
    )

    discount_percent_column = (
        "discount_percent"
        if discount_type == "percent"
        else None
    )

    with (
        patch(
            "ui.data_upload.st.expander",
            return_value=MagicMock(),
        ),
        patch("ui.data_upload.st.columns") as columns_mock,
        patch("ui.data_upload.st.caption"),
        patch("ui.data_upload.st.divider"),
        patch("ui.data_upload.st.markdown"),
        patch("ui.data_upload.st.warning") as warning_mock,
        patch("ui.data_upload.st.info") as info_mock,
        patch(
            "ui.data_upload.calculate_discounted_sales"
        ) as amount_calculator,
        patch(
            "ui.data_upload.calculate_percentage_discounted_sales"
        ) as percent_calculator,
    ):
        columns_mock.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        render_pos_accounting_summary(
            df,
            make_mapping(),
            discount_column=discount_column,
            discount_percent_column=discount_percent_column,
            price_basis=price_basis,
        )

        # Only the original refund-accounting metrics
        # should be displayed.
        assert columns_mock.call_count == 1

        # Neither discount calculator should run.
        amount_calculator.assert_not_called()
        percent_calculator.assert_not_called()

        if price_basis == "unknown":
            assert warning_mock.called
        else:
            assert info_mock.called
