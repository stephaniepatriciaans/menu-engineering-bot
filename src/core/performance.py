"""Small deterministic timing collector; no POS records are stored here."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class PerformanceProfiler:
    durations: dict[str, float] = field(default_factory=dict)

    @contextmanager
    def measure(self, label: str) -> Iterator[None]:
        start = perf_counter()
        try:
            yield
        finally:
            self.durations[label] = perf_counter() - start

    @property
    def total_seconds(self) -> float:
        return sum(self.durations.values())
