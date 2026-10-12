import random

from tape.envs.peg_solitaire import LEVEL_CLASSIC as L
from tape.envs.peg_solitaire_validator import PegPagodaValidator
from tape.executor import run_episode
from tape.search_proposer import WeightedAStarProposer

V = PegPagodaValidator()


def _solvable(state, memo):
    """Exhaustive check, only used on positions with few pegs."""
    if L.is_goal(state):
        return True
    if state in memo:
        return memo[state]
    memo[state] = any(_solvable(n, memo) for a in L.ACTIONS for n, ok in [L.step(state, a)] if ok)
    return memo[state]


def test_start_position_and_moves():
    assert L.complexity(L.initial_state) == 32 and len(L.ACTIONS) == 76
    legal = [a for a in L.ACTIONS if L.step(L.initial_state, a)[1]]
    assert len(legal) == 4  # the four pegs next to the centre hole
    nxt, _ = L.step(L.initial_state, legal[0])
    assert L.complexity(nxt) == 31
    assert L.step(L.initial_state, "00U") == (L.initial_state, False)


def test_every_pagoda_is_valid_and_the_start_clears_the_bound():
    assert len(V.pagodas) >= 8
    for w in V.pagodas:
        assert all(w[f] + w[o] >= w[t] - 1e-9 for f, o, t in L.jumps)
    assert not V.unsolvable(L.initial_state)


def test_search_solves_and_checker_never_rejects_the_solution():
    prop = WeightedAStarProposer(weights=(2,), node_budget=300_000, validator=V)
    (plan,) = prop.generate_candidate_plans(L, L.initial_state, 1, 60)
    assert len(plan) == 31
    cur = L.initial_state
    for a in plan:
        nxt, moved = L.step(cur, a)
        assert moved and V.validate(L, cur, a, nxt).accept
        cur = nxt
    assert L.is_goal(cur)


def test_rejected_positions_really_are_unsolvable():
    rng, checked = random.Random(3), 0
    for _ in range(400):
        s = L.initial_state
        for _ in range(40):
            moves = [(a, n) for a in L.ACTIONS for n, ok in [L.step(s, a)] if ok]
            if not moves:
                break
            s = rng.choice(moves)[1]
            if L.complexity(s) <= 7 and V.unsolvable(s):
                assert not _solvable(s, {}), L.render(s)
                checked += 1
                break
    assert checked >= 20


def test_pipeline_solves_from_a_midgame_position():
    s, moved = L.step(L.initial_state, "13D")
    assert moved
    prop = WeightedAStarProposer(weights=(2,), node_budget=300_000, validator=V)
    r = run_episode(L, prop, start=s, n_candidates=1, max_depth=60, validator=V, path_selection="adaptive")
    assert r.success
