import random

from tape.envs.sliding_puzzle import LEVEL_24, SlidingPuzzle
from tape.envs.sliding_puzzle_validator import SlidingParityValidator
from tape.executor import run_episode
from tape.search_proposer import WeightedAStarProposer

V = SlidingParityValidator()


def test_moves_and_goal():
    L = LEVEL_24
    assert L.is_goal(L.goal) and L.heuristic(L.goal) == 0 and len(L.goal) == 25
    s, moved = L.step(L.goal, "D")
    assert not moved  # blank is already in the bottom row
    s, moved = L.step(L.goal, "U")
    assert moved and L.heuristic(s) == 1
    assert L.step(s, "D")[0] == L.goal


def test_parity_is_preserved_by_moves_and_caught_when_broken():
    rng = random.Random(0)
    for n in (3, 4, 5):
        L = SlidingPuzzle(n)
        s = L.scramble(150, rng)
        assert L.solvable(s) and not L.solvable(L.unsolvable_twin(s))


def test_search_solves_a_scramble_and_the_pipeline_runs():
    L = LEVEL_24
    s = L.scramble(25, random.Random(4))
    lv = L.with_start(s)
    prop = WeightedAStarProposer(weights=(2,), node_budget=60_000)
    r = run_episode(lv, prop, n_candidates=1, max_depth=200, validator=V, path_selection="adaptive")
    assert r.success


def test_gate_stops_an_unsolvable_start_at_once():
    L = LEVEL_24
    s = L.unsolvable_twin(L.scramble(30, random.Random(1)))
    lv = L.with_start(s)
    plain = WeightedAStarProposer(weights=(4,), node_budget=5_000)
    gated = WeightedAStarProposer(weights=(4,), node_budget=5_000, validator=V)
    assert plain.generate_candidate_plans(lv, s, 1, 400) == [] and plain.expansions == 5_000
    assert gated.generate_candidate_plans(lv, s, 1, 400) == [] and gated.expansions <= 2
