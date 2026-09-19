import random

from tape.envs.sokoban import LEVEL_HARD
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import MockLLMClient, _bfs_plan
from tape.validator import CornerDeadlockValidator


def test_hard_level_optimal_solution_is_29_moves():
    plan = _bfs_plan(LEVEL_HARD, LEVEL_HARD.initial_state, 40)
    assert len(plan) == 29
    state = LEVEL_HARD.initial_state
    for a in plan:
        state, moved = LEVEL_HARD.step(state, a)
        assert moved
    assert LEVEL_HARD.is_goal(state)


def test_full_pipeline_solves_hard_level_and_validator_never_rejects_the_optimal_path():
    result = run_episode(
        LEVEL_HARD, MockLLMClient(seed=1), n_candidates=8, max_depth=32,
        validator=CornerDeadlockValidator(), experience=ExperienceStore(),
        level_id="hard", path_selection="adaptive",
    )
    assert result.success
    assert result.total_actions == 29
    assert result.validator_rejections == 0
    assert result.path_selection_methods == ["cp_sat"]  # three boxes -> joint constraints


def test_hard_level_recovers_from_random_slips():
    result = run_episode(
        LEVEL_HARD, MockLLMClient(seed=1), n_candidates=8, max_depth=32, max_replans=6,
        slip_prob=0.05, rng=random.Random(3), validator=CornerDeadlockValidator(),
    )
    assert result.success
    assert result.replans >= 1
