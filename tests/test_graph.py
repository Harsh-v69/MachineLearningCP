from tape.envs.sokoban import LEVEL_TRIVIAL
from tape.graph import build_plan_graph


def test_merges_shared_states_across_candidates():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    # Two candidates that both take the (only) valid first step "R" should
    # merge onto the same node instead of duplicating it.
    result = build_plan_graph(level, start, [["R"], ["R", "U"]])
    assert result.graph.number_of_nodes() == 2  # start, and the post-push state
    assert result.goal_nodes  # the merged node is a goal


def test_illegal_step_becomes_a_dead_end_not_a_crash():
    level = LEVEL_TRIVIAL
    start = level.initial_state
    result = build_plan_graph(level, start, [["L", "R"]])  # L is illegal (wall)
    assert result.invalid_transitions == 1
    assert result.attempted_transitions == 1  # stops after the illegal step
    assert not result.goal_nodes
