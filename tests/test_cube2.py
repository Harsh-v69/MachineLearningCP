import random

import numpy as np

from tapegraph.problems.cube2 import Cube2
from tapegraph.solvers import astar, idastar

CUBE = Cube2.shared()


def test_distance_distribution_matches_known_2x2x2_counts():
    counts = np.bincount(CUBE.dist.astype(np.int64))
    assert counts.tolist() == [1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644]


def test_heuristic_is_admissible_and_goal_is_zero():
    rng = random.Random(0)
    for _ in range(2000):
        i = rng.randrange(len(CUBE.dist))
        s = divmod(i, CUBE.NT)
        assert CUBE.h(s) <= CUBE.exact_dist(s)
    assert CUBE.h((0, 0)) == 0 and CUBE.is_goal((0, 0))


def test_random_start_has_exact_requested_depth():
    rng = random.Random(1)
    for depth in (1, 5, 9, 11):
        assert CUBE.exact_dist(CUBE.random_start(rng, depth)) == depth


def test_solvers_find_optimal_solutions():
    rng = random.Random(2)
    for depth in (4, 6, 7):
        s = CUBE.random_start(rng, depth)
        a = astar.solve(CUBE, s)
        i = idastar.solve(CUBE, s)
        assert a.status == i.status == "ok"
        assert a.cost == i.cost == depth


def test_moves_are_inverses():
    s = CUBE.random_start(random.Random(3), 8)
    for name, inv in (("U", "U'"), ("R", "R'"), ("F", "F'"), ("U2", "U2")):
        assert CUBE.step(CUBE.step(s, name), inv) == s


def test_half_turns_cost_two_resource_units():
    s = CUBE.random_start(random.Random(4), 5)
    assert CUBE.res(s, "R2", CUBE.step(s, "R2")) == 2 and CUBE.res(s, "R", CUBE.step(s, "R")) == 1
