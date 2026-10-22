from toy import GRAPH
from tapegraph.solvers import idastar


def test_idastar_optimal_on_toy():
    r = idastar.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2


def test_idastar_budget_too_small():
    assert idastar.solve(GRAPH, "A", budget=1).status == "no_path"


def test_idastar_unreachable_goal_terminates():
    assert idastar.solve(GRAPH, "X").status == "no_path"  # infinite budget, must still stop


def test_idastar_from_midpoint():
    r = idastar.solve(GRAPH, "B", budget=10)
    assert r.status == "ok" and r.path == ["be"]


def test_idastar_start_is_goal():
    assert idastar.solve(GRAPH, "E").path == []
