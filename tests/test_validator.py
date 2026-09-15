from tape.envs.sokoban import SokobanLevel
from tape.graph import build_plan_graph, build_validated_plan_graph
from tape.validator import CornerDeadlockValidator

# Pushing the box up lands it on (1,1), which has a wall above (0,1) and a
# wall to its left (1,0): a corner, off the goal at (3,3). The push itself
# is physically legal (the cell it lands on is open floor), so
# level.step() reports it as a normal successful move -- only a domain
# rule ("a box off-goal in a corner can never be moved again") knows it's
# a dead end.
CORNER_TRAP_LEVEL = SokobanLevel(
    [
        "#####",
        "#   #",
        "#$  #",
        "#@ .#",
        "#####",
    ]
)


def test_baseline_graph_accepts_the_deadlocking_push():
    level = CORNER_TRAP_LEVEL
    result = build_plan_graph(level, level.initial_state, [["U"]])
    assert result.invalid_transitions == 0  # physically legal, so Phase 1 lets it through
    assert result.graph.number_of_edges() == 1


def test_validator_rejects_the_same_push():
    level = CORNER_TRAP_LEVEL
    result = build_validated_plan_graph(
        level, level.initial_state, [["U"]], CornerDeadlockValidator()
    )
    assert result.validator_rejections == 1
    assert result.graph.number_of_edges() == 0  # never entered the graph


def test_pushing_onto_the_goal_is_never_flagged_as_a_deadlock():
    level = SokobanLevel(["#####", "#@$.#", "#####"])
    result = build_validated_plan_graph(
        level, level.initial_state, [["R"]], CornerDeadlockValidator()
    )
    assert result.validator_rejections == 0
    assert result.goal_nodes


def test_box_against_one_wall_is_uncertain_not_rejected():
    # Box ends up against the top wall only (not a corner) -- should be
    # accepted but with reduced confidence, reflected as a higher edge cost.
    level = SokobanLevel(
        [
            "######",
            "#    #",
            "#  $ #",
            "#  @.#",
            "#    #",
            "######",
        ]
    )
    result = build_validated_plan_graph(
        level, level.initial_state, [["U"]], CornerDeadlockValidator()
    )
    assert result.validator_rejections == 0
    edge = next(iter(result.graph.edges(data=True)))
    assert edge[2]["confidence"] == 0.5
    assert edge[2]["cost"] > 1
