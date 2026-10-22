from toy import GRAPH
from tapegraph.solvers import astar, bfs


def test_bfs_finds_shortest():
    r = bfs.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2 and r.res == 6


def test_bfs_budget_too_small():
    assert bfs.solve(GRAPH, "A", budget=1).status == "no_path"


def test_astar_matches_bfs():
    r = astar.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.states == ["A", "B", "E"]


def test_astar_budget_too_small():
    assert astar.solve(GRAPH, "A", budget=1).status == "no_path"


def test_astar_resource_budget_forces_longer_path():
    r = astar.solve(GRAPH, "A", res_budget=4)
    assert r.status == "ok" and r.path == ["ac", "cd", "de"] and r.cost == 3 and r.res == 3
    assert astar.solve(GRAPH, "A", res_budget=2).status == "no_path"


def test_resource_budget_and_length_budget_interact():
    # res_budget=4 needs length 3, so a length budget of 2 makes it infeasible.
    assert astar.solve(GRAPH, "A", budget=2, res_budget=4).status == "no_path"


def test_weighted_astar_never_beats_optimal():
    r = astar.solve(GRAPH, "A", w=2.0)
    assert r.status == "ok" and r.cost >= 2


def test_start_is_goal():
    r = astar.solve(GRAPH, "E")
    assert r.status == "ok" and r.path == [] and r.cost == 0


def test_node_limit():
    assert astar.solve(GRAPH, "A", max_nodes=0).status == "node_limit"


def test_unreachable_goal_is_no_path():
    assert bfs.solve(GRAPH, "X").status == "no_path"
    assert astar.solve(GRAPH, "X").status == "no_path"
