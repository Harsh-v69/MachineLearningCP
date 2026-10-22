import random

from toy import GRAPH
from tapegraph.oracle import Oracle
from tapegraph.problem import INF
from tapegraph.problems.river import River
from tapegraph.solvers import astar, bfs, idastar


def test_oracle_on_toy_graph():
    o = Oracle(GRAPH)
    assert o.dist("A") == 2 and o.dist("E") == 0
    assert o.best_action("A") == "ab" and o.best_action("E") is None
    assert o.viable("A", 2) == ["ab"]  # "ac" leaves dist 2 > rem-1 = 1
    assert sorted(o.viable("A", 3)) == ["ab", "ac"]


def test_classic_missionaries_and_cannibals_needs_11_crossings():
    assert River(3, 2).exact_dist((3, 3, 0)) == 11


def test_river_solvers_agree_with_exact_distance_from_every_state():
    p = River(8, 4)
    for s, d in p.dist.items():
        if d == 0:
            continue
        b = bfs.solve(p, s)
        a = astar.solve(p, s)
        i = idastar.solve(p, s)
        assert b.cost == a.cost == i.cost == d, s


def test_river_heuristic_is_admissible():
    p = River(8, 4)
    assert all(p.h(s) <= d for s, d in p.dist.items())


def test_river_random_start_has_requested_distance():
    p = River(8, 4)
    rng = random.Random(0)
    for depth in (3, 7, 12):
        s = p.random_start(rng, depth)
        assert p.exact_dist(s) == depth
    assert p.random_start(rng, 99) is None


def test_oracle_uses_exact_dist_when_available():
    p = River(8, 4)
    o = Oracle(p)
    s = p.random_start(random.Random(1), 9)
    assert o.dist(s) == 9
    a = o.best_action(s)
    assert p.exact_dist(p.step(s, a)) == 8
    assert o.dist((99, 99, 0)) == INF
