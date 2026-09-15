import random

from tape.envs.sokoban import LEVEL_MULTI, LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.executor import run_episode
from tape.llm import MockLLMClient
from tape.validator import CornerDeadlockValidator


def test_mock_llm_solves_trivial_level():
    result = run_episode(LEVEL_TRIVIAL, MockLLMClient(seed=1), n_candidates=3, max_depth=5)
    assert result.success
    assert result.total_actions >= 1


def test_mock_llm_solves_simple_level_with_enough_candidates():
    result = run_episode(
        LEVEL_SIMPLE, MockLLMClient(seed=1), n_candidates=12, max_depth=10, max_replans=3
    )
    assert result.success


def test_slips_trigger_replanning_and_still_reach_goal_eventually():
    result = run_episode(
        LEVEL_TRIVIAL,
        MockLLMClient(seed=2),
        n_candidates=4,
        max_depth=5,
        max_replans=10,
        slip_prob=0.5,
        rng=random.Random(42),
    )
    assert result.success
    assert result.planning_rounds >= 1


def test_two_box_level_solves_with_validator_and_experience_enabled():
    from tape.experience import ExperienceStore

    result = run_episode(
        LEVEL_MULTI,
        MockLLMClient(seed=4),
        n_candidates=20,
        max_depth=14,
        max_replans=3,
        validator=CornerDeadlockValidator(),
        experience=ExperienceStore(),
        level_id="multi",
    )
    assert result.success


def test_run_episode_solves_with_astar_path_selection():
    result = run_episode(
        LEVEL_TRIVIAL, MockLLMClient(seed=1), n_candidates=3, max_depth=5, path_selection="astar"
    )
    assert result.success
    assert result.path_selection_methods == ["astar"]


def test_run_episode_adaptive_picks_astar_for_single_box_level():
    result = run_episode(
        LEVEL_SIMPLE, MockLLMClient(seed=1), n_candidates=12, max_depth=10,
        max_replans=3, path_selection="adaptive",
    )
    assert result.success
    assert all(m == "astar" for m in result.path_selection_methods)


def test_run_episode_adaptive_picks_cp_sat_for_multi_box_level():
    result = run_episode(
        LEVEL_MULTI, MockLLMClient(seed=4), n_candidates=20, max_depth=14,
        max_replans=3, path_selection="adaptive",
    )
    assert result.success
    assert all(m == "cp_sat" for m in result.path_selection_methods)
