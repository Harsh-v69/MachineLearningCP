import math

import numpy as np
import pytest

from tapegraph.stats import bootstrap_ci, wilson_interval


def test_wilson_hand_computed():
    # centre (p + z^2/2n)/(1+z^2/n), half-width z*sqrt(p(1-p)/n + z^2/4n^2)/(1+z^2/n), z = 1.96
    lo, hi = wilson_interval(8, 10)
    assert (round(lo, 4), round(hi, 4)) == (0.4902, 0.9433)
    lo, hi = wilson_interval(0, 10)
    assert (lo, round(hi, 4)) == (0.0, 0.2775)
    lo, hi = wilson_interval(10, 10)
    assert (round(lo, 4), hi) == (0.7225, 1.0)
    lo, hi = wilson_interval(1, 1)
    assert (round(lo, 4), hi) == (0.2065, 1.0)


def test_wilson_z_and_empty():
    lo, hi = wilson_interval(8, 10, z=1.0)
    assert hi - lo < wilson_interval(8, 10)[1] - wilson_interval(8, 10)[0]
    lo, hi = wilson_interval(0, 0)
    assert math.isnan(lo) and math.isnan(hi)


def test_bootstrap_constant_and_determinism():
    assert bootstrap_ci([0.5] * 7) == (0.5, 0.5)
    v = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.5, 0.25]
    assert bootstrap_ci(v, seed=3) == bootstrap_ci(v, seed=3)
    w = list(np.linspace(0, 1, 37) ** 2)
    assert bootstrap_ci(w, seed=3) == bootstrap_ci(w, seed=3)
    assert bootstrap_ci(w, seed=3) != bootstrap_ci(w, seed=4)
    lo, hi = bootstrap_ci(v)
    assert min(v) <= lo < np.mean(v) < hi <= max(v)


def test_bootstrap_other_stat_and_empty():
    lo, hi = bootstrap_ci([1.0, 2.0, 3.0, 100.0], stat=np.median)
    assert 1.0 <= lo <= hi <= 100.0
    lo, hi = bootstrap_ci([])
    assert math.isnan(lo) and math.isnan(hi)
