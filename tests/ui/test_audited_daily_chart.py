"""Regression checks for audited daily chart date-axis presentation."""

from decimal import Decimal

import pandas as pd
import pytest

from ui.audited_daily_chart import build_audited_daily_sales_chart


def test_two_day_chart_uses_dates_not_hourly_ticks():
    days = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02", "2026-01-01"]),
        "revenue": [Decimal("5.00"), Decimal("20.00")],
    })
    original = days.copy(deep=True)
    chart = build_audited_daily_sales_chart(days)
    axis = chart.layout.xaxis
    assert axis.type == "category"
    assert list(axis.ticktext) == ["Jan 01, 2026", "Jan 02, 2026"]
    assert list(chart.data[0].x) == list(axis.tickvals)
    assert list(chart.data[0].y) == [20.0, 5.0]
    pd.testing.assert_frame_equal(days, original)


def test_single_day_chart_displays_single_date_without_hourly_axis():
    chart = build_audited_daily_sales_chart(pd.DataFrame({
        "date": ["2026-01-01"],
        "revenue": [Decimal("25.00")],
    }))
    assert chart.layout.xaxis.type == "category"
    assert list(chart.layout.xaxis.ticktext) == ["Jan 01, 2026"]
    assert list(chart.data[0].y) == [25.0]
    assert chart.data[0].mode == "markers"


def test_empty_day_chart_is_rejected():
    with pytest.raises(ValueError, match="at least one date"):
        build_audited_daily_sales_chart(pd.DataFrame(columns=["date", "revenue"]))
