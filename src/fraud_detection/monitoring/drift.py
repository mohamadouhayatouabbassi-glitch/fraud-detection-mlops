"""Drift detection utilities.

The Population Stability Index (PSI) is the industry standard in financial
services to detect distribution shift between a reference (training) and
a current (live) sample. Thresholds commonly used:

  PSI < 0.10  : no significant shift
  0.10 - 0.25 : moderate shift, investigate
  PSI > 0.25  : major shift, retraining or feature investigation required

The function below is intentionally pure (numpy only) so it can be called
from a daily batch job, a Lambda, or a notebook indifferently.
"""

from __future__ import annotations

import numpy as np


def psi(
    expected: np.ndarray,
    actual: np.ndarray,
    n_bins: int = 10,
    eps: float = 1e-6,
) -> float:
    """Compute the Population Stability Index between two samples.

    Bins are quantile-based on the expected (reference) sample, which is the
    standard practice. NaNs are dropped.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Quantile-based bin edges on the reference distribution
    quantiles = np.linspace(0, 1, n_bins + 1)
    edges = np.unique(np.quantile(expected, quantiles))
    if len(edges) <= 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    exp_counts, _ = np.histogram(expected, bins=edges)
    act_counts, _ = np.histogram(actual, bins=edges)
    exp_pct = exp_counts / max(1, exp_counts.sum()) + eps
    act_pct = act_counts / max(1, act_counts.sum()) + eps
    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
