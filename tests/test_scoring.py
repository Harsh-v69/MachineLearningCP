from experiments.export_demo import BAD_PLAN, DEMO_LEVEL_ROWS
from tape.envs.sokoban import SokobanLevel, State
from tape.graph import build_validated_plan_graph
from tape.llm import _bfs_plan
from tape.scoring import ScoreWeights, goal_distance, score_transition
from tape.validator import CornerDeadlockValidator

LEVEL = SokobanLevel(
    [
        "#######",
        "#$    #",
        "#     #",
        "#     #",
        "#     #",
        "#    .#",
        "#@    #",
    ]
)
GOAL = next(iter(LEVEL.goals))  # (5, 5)


def state_with_box(box: tuple[int, int]) -> State:
    return State(player=(0, 0), boxes=frozenset({box}))


def test_goal_distance_is_manhattan_to_nearest_goal():
    assert goal_distance(LEVEL, state_with_box(GOAL)) == 0
    assert goal_distance(LEVEL, state_with_box((3, 3))) == abs(3 - GOAL[0]) + abs(3 - GOAL[1])


def test_regression_costs_more_than_equal_progress():
    from_state = state_with_box((3, 3))
    progress_state = state_with_box((4, 4))  # closer to goal
    regress_state = state_with_box((2, 2))  # farther from goal

    progress = score_transition(LEVEL, from_state, progress_state, step_index=0, max_depth=10, confidence=1.0)
    regress = score_transition(LEVEL, from_state, regress_state, step_index=0, max_depth=10, confidence=1.0)

    assert progress.regression == 0
    assert regress.regression > 0
    assert regress.cost > progress.cost


def test_lower_confidence_costs_more_all_else_equal():
    from_state = state_with_box((3, 3))
    to_state = state_with_box((4, 4))

    confident = score_transition(LEVEL, from_state, to_state, step_index=0, max_depth=10, confidence=1.0)
    unsure = score_transition(LEVEL, from_state, to_state, step_index=0, max_depth=10, confidence=0.3)

    assert unsure.cost > confident.cost


def test_budget_pressure_grows_as_the_step_budget_is_used_up():
    from_state = state_with_box((3, 3))
    to_state = state_with_box((4, 4))

    early = score_transition(LEVEL, from_state, to_state, step_index=0, max_depth=10, confidence=1.0)
    late = score_transition(LEVEL, from_state, to_state, step_index=9, max_depth=10, confidence=1.0)

    assert late.budget_used_fraction > early.budget_used_fraction
    assert late.cost > early.cost


def test_cost_is_always_a_positive_integer():
    s = score_transition(LEVEL, state_with_box((3, 3)), state_with_box((4, 4)), 0, 10, 1.0, ScoreWeights())
    assert isinstance(s.cost, int)
    assert s.cost >= 1


def test_validated_graph_edges_carry_a_nonnegative_regression_score():
    level = SokobanLevel(DEMO_LEVEL_ROWS)
    start = level.initial_state
    good_plan = _bfs_plan(level, start, 20)
    graph = build_validated_plan_graph(
        level, start, [good_plan, BAD_PLAN], CornerDeadlockValidator(), max_depth=20
    )
    edges = list(graph.graph.edges(data=True))
    assert edges  # the demo's known-good candidates do produce a real graph
    for _, _, data in edges:
        assert "regression" in data
        assert data["regression"] >= 0
        assert data["cost"] >= 1
