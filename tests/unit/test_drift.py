"""Drift detection unit tests."""

from __future__ import annotations

import numpy as np

from fraud_detection.monitoring.drift import psi


def test_psi_zero_when_identical():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 5000)
    assert psi(x, x) < 1e-6


def test_psi_detects_mean_shift():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 5000)
    b = rng.normal(2, 1, 5000)
    score = psi(a, b)
    assert score > 0.25  # major shift


def test_psi_handles_empty_arrays():
    assert psi(np.array([]), np.array([1, 2, 3])) == 0.0
