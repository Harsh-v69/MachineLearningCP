import random

from tape.envs.sokoban import LEVEL_TRIVIAL
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import MockLLMClient
from tape.validator import CornerDeadlockValidator


def test_no_history_means_full_confidence():
    store = ExperienceStore()
    assert store.confidence("lvl", LEVEL_TRIVIAL.initial_state, "R") == 1.0


def test_repeated_failures_lower_confidence_below_repeated_successes():
    store = ExperienceStore()
    state = LEVEL_TRIVIAL.initial_state
    for _ in range(5):
        store.record("lvl", state, "R", success=False)
    low = store.confidence("lvl", state, "R")

    store2 = ExperienceStore()
    for _ in range(5):
        store2.record("lvl", state, "R", success=True)
    high = store2.confidence("lvl", state, "R")

    assert low < 0.5 < high


def test_experience_persists_and_biases_graph_confidence_across_episodes():
    level = LEVEL_TRIVIAL
    store = ExperienceStore()
    validator = CornerDeadlockValidator()
    rng = random.Random(7)

    # Force every executed transition to mismatch, so the store accumulates
    # failure history for the transitions this level actually uses.
    for _ in range(3):
        run_episode(
            level,
            MockLLMClient(seed=3),
            n_candidates=3,
            max_depth=5,
            max_replans=1,
            slip_prob=1.0,
            rng=rng,
            validator=validator,
            experience=store,
            level_id="lvl",
        )

    stats = store.stats("lvl", level.initial_state, "R")
    assert stats.failures > 0
    assert store.confidence("lvl", level.initial_state, "R") < 1.0
