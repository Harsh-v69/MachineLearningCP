import random

import numpy as np
import pytest

from tapegraph.problems import cube2, cube3
from tapegraph.problems.cube3 import Cube3
from tapegraph.solvers import astar, bfs, idastar

CUBE = Cube3(pdb=[0])  # moves/tables only; the tests that need h() swap in a heuristic below


def _layers(p, depth):
    """Plain BFS from the goal: {state: distance} up to `depth`."""
    dist, frontier = {p.goal: 0}, [p.goal]
    for d in range(1, depth + 1):
        nxt = []
        for s in frontier:
            for _, v, _ in p.neighbors(s):
                if v not in dist:
                    dist[v] = d
                    nxt.append(v)
        frontier = nxt
    return dist


DIST4 = _layers(CUBE, 4)


def test_full_state_bfs_matches_known_half_turn_counts():
    assert np.bincount(list(DIST4.values())).tolist() == [1, 18, 243, 3240, 43239]


def _parity(p):
    return sum(p[i] > p[j] for i in range(len(p)) for j in range(i + 1, len(p))) % 2


def test_moves_are_inverses_and_cubies_stay_valid():
    rng = random.Random(0)
    s = CUBE.random_start(rng, 30)
    for a, b in (("U", "U'"), ("R", "R'"), ("F", "F'"), ("D", "D'"), ("L", "L'"), ("B", "B'"), ("R2", "R2")):
        assert CUBE.step(CUBE.step(s, a), b) == s
    for f in "UDLRFB":
        x = s
        for _ in range(4):
            x = CUBE.step(x, f)
        assert x == s and CUBE.step(CUBE.step(s, f), f) == CUBE.step(s, f + "2")
    assert CUBE.decode(CUBE.goal) == (list(range(8)), [0] * 8, list(range(12)), [0] * 12)
    for _ in range(100):
        s = CUBE.step(s, rng.choice(CUBE.names))
    cp, co, ep, eo = CUBE.decode(s)
    assert sorted(cp) == list(range(8)) and sorted(ep) == list(range(12))
    assert sum(co) % 3 == 0 and sum(eo) % 2 == 0 and _parity(cp) == _parity(ep)
    assert s != CUBE.goal and not CUBE.is_goal(s) and CUBE.is_goal(CUBE.goal)


def test_resources_match_cube2_convention():
    s = CUBE.goal
    assert CUBE.res(s, "R2", None) == 2 and CUBE.res(s, "R", None) == 1 and CUBE.res(s, "R'", None) == 1
    assert CUBE.res_bind(s, "U2", None) == 1 and CUBE.res_bind(s, "U'", None) == 0


def test_random_start_never_repeats_an_axis_and_stays_within_depth():
    rng = random.Random(1)
    for depth in range(5):
        for _ in range(50):
            assert DIST4[CUBE.random_start(rng, depth)] <= depth
    # with no same-axis repeats, walks of length <= 3 are optimal
    assert all(DIST4[CUBE.random_start(rng, 3)] == 3 for _ in range(50))
