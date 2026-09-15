from tape.envs.sokoban import LEVEL_MULTI, LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.graph import build_plan_graph
from tape.llm import MockLLMClient
from tape.path_selector import (
    ASTAR,
    CP_SAT,
    astar_select_path,
    decide_method,
    select_path_adaptive,
)
from tape.solver import select_path


def test_astar_finds_a_path_on_trivial_level():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    plan_graph = build_plan_graph(level, start, [["R"]])
    solution = astar_select_path(level, plan_graph)
    assert solution is not None
    assert solution.actions == ["R"]
    assert level.is_goal(solution.node_path[-1])


def test_astar_matches_cp_sat_cost_on_a_richer_graph():
    level = LEVEL_SIMPLE
    start = level.initial_state
    candidates = MockLLMClient(seed=1).generate_candidate_plans(level, start, 12, 12)
    plan_graph = build_plan_graph(level, start, candidates)

    astar_solution = astar_select_path(level, plan_graph)
    cp_sat_solution = select_path(plan_graph)

    assert astar_solution is not None and cp_sat_solution is not None
    assert astar_solution.cost == cp_sat_solution.cost


def test_astar_returns_none_when_infeasible():
    level = LEVEL_SIMPLE
    start = level.initial_state
    plan_graph = build_plan_graph(level, start, [["U"]])  # doesn't reach the goal
    assert astar_select_path(level, plan_graph) is None


def test_decide_method_prefers_astar_for_single_box_levels():
    for level in (LEVEL_TRIVIAL, LEVEL_SIMPLE):
        plan_graph = build_plan_graph(level, level.initial_state, [["R"]])
        assert decide_method(plan_graph) == ASTAR


def test_decide_method_prefers_cp_sat_for_multi_box_levels():
    level = LEVEL_MULTI
    plan_graph = build_plan_graph(level, level.initial_state, [["U"]])
    assert decide_method(plan_graph) == CP_SAT


def test_select_path_adaptive_solves_single_box_level_with_astar():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    plan_graph = build_plan_graph(level, start, [["R"]])
    solution, method = select_path_adaptive(level, plan_graph)
    assert method == ASTAR
    assert solution is not None
    assert level.is_goal(solution.node_path[-1])


def test_select_path_adaptive_solves_multi_box_level_with_cp_sat():
    level = LEVEL_MULTI
    start = level.initial_state
    candidates = MockLLMClient(seed=1).generate_candidate_plans(level, start, 20, 14)
    plan_graph = build_plan_graph(level, start, candidates)
    solution, method = select_path_adaptive(level, plan_graph)
    assert method == CP_SAT
    assert solution is not None
    assert level.is_goal(solution.node_path[-1])
