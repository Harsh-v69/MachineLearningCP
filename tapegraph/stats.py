"""Interval estimates for the report: Wilson score interval and a percentile bootstrap (numpy only)."""
from __future__ import annotations

from math import nan, sqrt

import numpy as np


def wilson_interval(successes, trials, z=1.96):
    """Wilson score interval for a binomial proportion; (nan, nan) when trials == 0."""
    if trials <= 0:
        return nan, nan
    p, d = successes / trials, 1 + z * z / trials
    c = (p + z * z / (2 * trials)) / d
    h = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    return max(0.0, c - h), min(1.0, c + h)


def bootstrap_ci(values, stat=np.mean, B=2000, seed=0, alpha=0.05):
    """Percentile bootstrap CI of stat(values); resamples with replacement, deterministic given seed."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return nan, nan
    idx = np.random.default_rng(seed).integers(0, v.size, size=(B, v.size))
    s = np.array([stat(v[i]) for i in idx])
    return float(np.quantile(s, alpha / 2)), float(np.quantile(s, 1 - alpha / 2))
