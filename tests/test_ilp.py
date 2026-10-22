import math
import random

import pytest

pytest.importorskip("ortools")

from toy import GRAPH
from tapegraph.problems.river import River
from tapegraph.solvers import astar, bfs, ilp


def test_ilp_finds_shortest_on_toy_graph():
    r = ilp.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2


def test_ilp_length_budget():
    assert ilp.solve(GRAPH, "A", budget=1).status == "no_path"


def test_ilp_resource_budget_forces_longer_path():
    r = ilp.solve(GRAPH, "A", res_budget=4)
    assert r.status == "ok" and r.path == ["ac", "cd", "de"] and r.res == 3
    assert ilp.solve(GRAPH, "A", res_budget=2).status == "no_path"


def test_ilp_start_is_goal():
    assert ilp.solve(GRAPH, "E").path == []


def test_ilp_matches_bfs_from_every_river_state():
    p = River(8, 4)
    for s, d in p.dist.items():
        if d == 0:
            continue
        b = bfs.solve(p, s)
        i = ilp.solve(p, s, budget=b.cost + 2)
        assert i.status == "ok" and i.cost == b.cost, s


def test_ilp_matches_constrained_astar_on_river():
    p = River(8, 4)
    checked = 0
    for s, d in sorted(p.dist.items()):
        if d < 4:
            continue
        B = d + 2
        base = astar.solve(p, s, budget=B)
        R = math.floor(0.9 * base.res)
        a = astar.solve(p, s, budget=B, res_budget=R)
        i = ilp.solve(p, s, budget=B, res_budget=R)
        assert a.status == i.status, (s, R)
        if a.status == "ok":
            assert a.cost == i.cost, (s, R)
            checked += 1
    assert checked > 0


def test_ilp_reports_too_large_instead_of_truncating():
    p = River(8, 4)
    s = p.random_start(random.Random(0), 10)
    assert ilp.solve(p, s, budget=20, max_nodes=3).status == "too_large"


def test_ilp_timeout_is_not_no_path():
    p = River(8, 4)
    s = p.random_start(random.Random(0), 10)
    assert ilp.solve(p, s, budget=20, time_limit=0).status == "timeout"
    edges = [(u, a, v, 1, 1) for u in range(30) for a, v in ((f"a{u}", u + 1), (f"b{u}", u + 2))]
    with pytest.raises(ilp.IlpTimeout):
        ilp.solve_graph(0, {31}, edges, time_limit=0)


def test_solve_graph_same_format_as_bfs():
    edges = [("A", "ab", "B", 1, 1), ("B", "be", "E", 1, 5)]
    assert ilp.solve_graph("A", {"E"}, edges) == [("A", "ab", "B"), ("B", "be", "E")]
