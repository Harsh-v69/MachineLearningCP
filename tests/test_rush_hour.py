"""Rush Hour: a third benchmark, structurally different from both Sokoban
(pieces have length and orientation, not just position) and river
crossing (multiple independently-movable pieces, not one boat)."""
import pytest

from tape.envs.rush_hour import LEVEL_CLASSIC, RushHourLevel
from tape.executor import run_episode
from tape.llm import MockLLMClient, _bfs_plan


def test_optimal_solution_is_six_moves_move_blocker_then_slide_target():
    plan = _bfs_plan(LEVEL_CLASSIC, LEVEL_CLASSIC.initial_state, 20)
    assert len(plan) == 6

    state = LEVEL_CLASSIC.initial_state
    for action in plan:
        state, moved = LEVEL_CLASSIC.step(state, action)
        assert moved
    assert LEVEL_CLASSIC.is_goal(state)


def test_target_cannot_pass_through_a_blocking_vehicle():
    # From the start, X is blocked by B two cells ahead in the same row.
    state = LEVEL_CLASSIC.initial_state
    _, moved = LEVEL_CLASSIC.step(state, "X+")
    assert not moved


def test_vehicles_cannot_leave_the_board():
    state = LEVEL_CLASSIC.initial_state
    _, moved = LEVEL_CLASSIC.step(state, "X-")  # already at the left edge
    assert not moved


def test_complexity_is_the_vehicle_count():
    assert LEVEL_CLASSIC.complexity(LEVEL_CLASSIC.initial_state) == 3


def test_heuristic_is_zero_only_at_the_goal():
    plan = _bfs_plan(LEVEL_CLASSIC, LEVEL_CLASSIC.initial_state, 20)
    state = LEVEL_CLASSIC.initial_state
    for action in plan:
        state, _ = LEVEL_CLASSIC.step(state, action)
    assert LEVEL_CLASSIC.heuristic(state) == 0
    assert LEVEL_CLASSIC.heuristic(LEVEL_CLASSIC.initial_state) > 0


def test_pipeline_solves_it_and_routes_to_cp_sat():
    result = run_episode(
        LEVEL_CLASSIC, MockLLMClient(seed=1), n_candidates=10, max_depth=20,
        path_selection="adaptive",
    )
    assert result.success
    assert result.total_actions == 6
    assert result.path_selection_methods == ["cp_sat"]  # 3 vehicles, complexity > 1


def test_rejects_a_vehicle_that_is_not_a_straight_contiguous_run():
    with pytest.raises(ValueError):
        RushHourLevel(["A.A", "..."])  # two disconnected 'A' cells


def test_rejects_a_vertical_target_vehicle():
    with pytest.raises(ValueError):
        RushHourLevel(["X.", "X."])
