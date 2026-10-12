import random

from tape.bidirectional import BidirectionalProposer
from tape.envs.peg_solitaire import LEVEL_CLASSIC as PEG
from tape.envs.peg_solitaire_validator import PegPagodaValidator
from tape.envs.river_crossing import LEVEL_CLASSIC as RIVER
from tape.envs.river_crossing_validator import RiverSafetyValidator
from tape.envs.sliding_puzzle import LEVEL_24
from tape.uninformed import BFSProposer, DFSProposer


def _plays(level, start, plan):
    cur = start
    for a in plan:
        cur, moved = level.step(cur, a)
        assert moved
    return level.is_goal(cur)


def test_bfs_finds_the_shortest_safe_plan():
    (plan,) = BFSProposer(validator=RiverSafetyValidator()).generate_candidate_plans(RIVER, RIVER.initial_state, 1, 20)
    assert len(plan) == 11 and _plays(RIVER, RIVER.initial_state, plan)


def test_dfs_solves_peg_solitaire_far_cheaper_than_the_budget():
    prop = DFSProposer(node_budget=60_000)
    (plan,) = prop.generate_candidate_plans(PEG, PEG.initial_state, 1, 31)
    assert len(plan) == 31 and _plays(PEG, PEG.initial_state, plan)
    assert prop.expansions < 30_000
    checked = DFSProposer(node_budget=60_000, validator=PegPagodaValidator())
    assert checked.generate_candidate_plans(PEG, PEG.initial_state, 1, 31) and checked.expansions <= prop.expansions


def test_budget_is_respected_and_failure_returns_no_plan():
    for cls in (BFSProposer, DFSProposer):
        prop = cls(node_budget=500)
        assert prop.generate_candidate_plans(PEG, PEG.initial_state, 1, 31) == []
        assert prop.expansions <= 500


def test_meet_in_the_middle_also_works_on_the_sliding_puzzle():
    s = LEVEL_24.scramble(16, random.Random(2))
    lv = LEVEL_24.with_start(s)
    (plan, *_) = BidirectionalProposer(node_budget=300_000).generate_candidate_plans(lv, s, 1, 40)
    assert len(plan) <= 16 and _plays(lv, s, plan)
