"""Automated (smaller) version of experiments/stress_test.py: proves at
scale, not just via one hand-crafted example, that the validator (a) does
catch real corner deadlocks under adversarial (pure-random) candidates,
and (b) never rejects a state that an independent plain-BFS check shows
is actually still solvable -- i.e. zero false positives.
"""
from experiments.stress_test import run_stress_test


def test_validator_catches_deadlocks_with_zero_false_positives():
    result = run_stress_test(n_trials=5, n_candidates=40, max_depth=12)
    assert result["total_rejected"] > 0  # the adversarial generator does trigger real deadlocks
    assert result["verified_dead_ends"] == result["total_rejected"]  # every rejection is a true dead end
