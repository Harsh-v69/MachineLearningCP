from tape.envs.boxoban import load_boxoban, parse_boxoban
from tape.envs.sokoban import LEVEL_SIMPLE
from tape.search_proposer import WeightedAStarProposer
from tape.validator import CornerDeadlockValidator

FIXTURE = "; 0\n" + LEVEL_SIMPLE.render(LEVEL_SIMPLE.initial_state) + "\n\n; 1\n" + LEVEL_SIMPLE.render(LEVEL_SIMPLE.initial_state) + "\n"


def test_parse_blocks_into_levels():
    levels = parse_boxoban(FIXTURE)
    assert len(levels) == 2 and levels[0].initial_state == LEVEL_SIMPLE.initial_state


def test_real_file_has_1000_ten_by_ten_levels():
    levels = load_boxoban()
    assert len(levels) == 1000 and (levels[0].width, levels[0].height) == (10, 10)
    assert len(levels[0].initial_state.boxes) == 4


def test_proposer_solves_and_pruning_never_expands_more_on_a_solved_level():
    lv = load_boxoban(limit=4)[3]
    plain = WeightedAStarProposer(weights=(4,), node_budget=30_000)
    prune = WeightedAStarProposer(weights=(4,), node_budget=30_000, validator=CornerDeadlockValidator())
    plans = prune.generate_candidate_plans(lv, lv.initial_state, 1, 200)
    assert plans and plain.generate_candidate_plans(lv, lv.initial_state, 1, 200)
    assert prune.expansions <= plain.expansions
    cur = lv.initial_state
    for a in plans[0]:
        cur, moved = lv.step(cur, a)
        assert moved
    assert lv.is_goal(cur)
