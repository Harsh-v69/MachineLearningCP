from tape.envs.sokoban import LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.graph import build_plan_graph
from tape.solver import select_path


def test_finds_shortest_path_to_goal():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    plan_graph = build_plan_graph(level, start, [["R"]])
    solution = select_path(plan_graph)
    assert solution is not None
    assert solution.actions == ["R"]
    assert level.is_goal(solution.node_path[-1])


def test_picks_the_cheaper_of_two_candidates():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    # A longer, wasteful candidate alongside the direct one -- solver must
    # prefer the 1-step path over the 3-step detour.
    plan_graph = build_plan_graph(level, start, [["R"], ["U", "D", "R"]])
    solution = select_path(plan_graph)
    assert solution is not None
    assert solution.cost == 1


def test_infeasible_when_no_candidate_reaches_goal():
    level = LEVEL_SIMPLE
    start = level.initial_state
    plan_graph = build_plan_graph(level, start, [["U"]])  # doesn't reach the goal
    assert select_path(plan_graph) is None
