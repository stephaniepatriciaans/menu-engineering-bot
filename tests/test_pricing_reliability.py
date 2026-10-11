import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from analysis import assess_pricing_reliability


@pytest.mark.parametrize(
    "source,confidence,expected",
    [
        (
            "estimated",
            "Low",
            "Exploratory — low-confidence estimate",
        ),
        (
            "estimated",
            "High",
            "Historical estimate — review required",
        ),
        (
            "category_prior",
            "Prior",
            "Exploratory — category assumption",
        ),
        (
            "default_prior",
            "Prior",
            "Exploratory — default assumption",
        ),
        (
            "unknown",
            "unknown",
            "Exploratory — unknown reliability",
        ),
    ],
)
def test_pricing_reliability(
    source,
    confidence,
    expected,
):
    label, reason = assess_pricing_reliability(
        source,
        confidence,
    )

    assert label == expected
    assert isinstance(reason, str)
    assert len(reason) > 0
