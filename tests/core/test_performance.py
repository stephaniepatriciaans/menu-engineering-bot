"""Instrumentation must not swallow exceptions or store transaction rows."""

import pytest

from core.performance import PerformanceProfiler


def test_profiler_records_duration():
    profiler = PerformanceProfiler()
    with profiler.measure("Data Setup"):
        pass
    assert profiler.durations["Data Setup"] >= 0
    assert profiler.total_seconds >= 0


def test_profiler_records_even_on_failure():
    profiler = PerformanceProfiler()
    with (
        pytest.raises(RuntimeError, match="example"),
        profiler.measure("Data Quality"),
    ):
        raise RuntimeError("example")
    assert "Data Quality" in profiler.durations
