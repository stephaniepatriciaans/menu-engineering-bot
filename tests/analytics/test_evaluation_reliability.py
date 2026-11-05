"""Paired metrics must never confuse baseline coverage and comparative accuracy."""

import numpy as np
import pandas as pd
import pytest

from analytics.evaluation_reliability import audit_paired_models


def test_no_paired_rows():
    frame = pd.DataFrame({
        "status": ["baseline_only", "insufficient_evidence"],
        "baseline_mae": [1.0, None],
        "elasticity_mae": [None, None],
    })
    audit = audit_paired_models(frame)
    assert audit.compared == 0
    assert audit.mean_baseline_mae is None


def test_paired_only_and_extrapolation():
    frame = pd.DataFrame({
        "status": ["evaluated", "evaluated", "evaluated", "baseline_only"],
        "baseline_mae": [1.0, 3.0, 2.0, 0.01],
        "elasticity_mae": [0.5, 9.0, 2.0, None],
        "price_extrapolation": [False, True, False, False],
    })
    audit = audit_paired_models(frame)
    assert audit.compared == 3
    assert (audit.elasticity_wins, audit.baseline_wins, audit.ties) == (1, 1, 1)
    assert audit.extrapolated == 1
    assert audit.mean_baseline_mae == pytest.approx(2.0)
    assert audit.mean_elasticity_mae == pytest.approx(11.5 / 3)


def test_nonfinite_values_ignored():
    frame = pd.DataFrame({
        "status": ["evaluated", "evaluated", "evaluated"],
        "baseline_mae": [1.0, np.nan, 0.0],
        "elasticity_mae": [20.0, 1.0, float("inf")],
    })
    audit = audit_paired_models(frame)
    assert audit.compared == 1
    assert audit.high_error_ratio == 1


def test_required_columns_are_enforced():
    with pytest.raises(ValueError, match="Missing evaluation columns"):
        audit_paired_models(pd.DataFrame({"status": ["evaluated"]}))


def test_empty_valid_schema():
    frame = pd.DataFrame(columns=["status", "baseline_mae", "elasticity_mae"])
    assert audit_paired_models(frame).compared == 0
