import csv
import sys

from tapegraph import bench
from tapegraph.problem import Result
from tests.toy import GRAPH, GraphProblem


def test_bind_budgets_on_toy_graph():
    d = bench.bind_budgets(GRAPH, "A", 2, 1, 1000)
    assert d == {"B": 3, "r_opt": 6, "r_min": 3, "levels": {"bind": 5, "tight": 3}}
    r = bench.astar.solve(GRAPH, "A", budget=3, res_budget=5)
    assert r.status == "ok" and r.cost == 3 > 2


def test_bind_budgets_single_level_when_levels_coincide():
    g = GraphProblem({"A": [("ab", "B", 1), ("ac", "C", 1)], "B": [("be", "E", 3)], "C": [("cd", "D", 1)],
                      "D": [("de", "E", 1)], "E": []}, goal="E", h={"A": 2, "B": 1, "C": 1, "D": 1, "E": 0})
    assert bench.bind_budgets(g, "A", 2, 1, 1000) == {"B": 3, "r_opt": 4, "r_min": 3, "levels": {"bind": 3}}


def test_bind_budgets_skip_no_tradeoff():
    # the only long route is also resource-hungry: nothing cheaper in resource exists
    g = GraphProblem({"A": [("ab", "B", 1), ("ac", "C", 1)], "B": [("be", "E", 1)],
                      "C": [("cd", "D", 5)], "D": [("de", "E", 5)], "E": []},
                     goal="E", h={"A": 2, "B": 1, "C": 1, "D": 1, "E": 0})
    assert bench.bind_budgets(g, "A", 2, 1, 1000) == {"skip": "no_tradeoff"}


def test_bind_budgets_propagates_base_failure(monkeypatch):
    monkeypatch.setattr(bench.astar, "solve", lambda *a, **k: Result("node_limit"))
    assert bench.bind_budgets(GRAPH, "A", 2, 1, 1000) == {"skip": "node_limit"}


def test_min_resource_aborts_on_failing_status(monkeypatch):
    assert bench.min_resource(GRAPH, "A", 2, 6, 1000) == ("ok", 6)
    monkeypatch.setattr(bench.astar, "solve", lambda *a, **k: Result("node_limit"))
    assert bench.min_resource(GRAPH, "A", 2, 6, 1000) == ("node_limit", None)


def _run(tmp_path, monkeypatch, *extra):
    monkeypatch.setattr(sys, "argv", ["bench", "constrained", "--bench", "river", "--n", "2", "--out", str(tmp_path), *extra])
    bench.main()
    return list(csv.DictReader(open(tmp_path / "constrained_river.csv")))


def test_bind_end_to_end_on_river(tmp_path, monkeypatch):
    rows = _run(tmp_path, monkeypatch, "--design", "bind")
    assert rows
    solved = [r for r in rows if r["solver"] != "skipped"]
    for r in solved:
        assert r["level"] in ("bind", "tight") and int(r["B"]) == int(r["T"]) + 4
    ok_a = [r for r in solved if r["solver"] == "astar" and r["ok"] == "1"]
    assert all(r["forced_longer"] == "1" and float(r["cost"]) > int(r["T"]) for r in ok_a)
    assert all(r["level"] == "-" and r["ok"] == "0" for r in rows if r["solver"] == "skipped")
    if bench.ilp.ORTOOLS_AVAILABLE:
        by = {}
        for r in solved:
            by.setdefault((r["T"], r["r_opt"], r["r_min"], r["level"]), {})[r["solver"]] = r
        for pair in by.values():
            if pair["astar"]["ok"] == pair["ilp"]["ok"] == "1":
                assert pair["ilp"]["agrees_with_astar"] == "1"
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path)])
    bench.main()
    assert "level" in (tmp_path / "results.md").read_text()


def test_frac_design_writes_level_frac(tmp_path, monkeypatch):
    rows = _run(tmp_path, monkeypatch, "--design", "frac")
    assert rows and {r["level"] for r in rows} == {"frac"}


def test_bind_keeps_ilp_row_when_astar_says_no_path(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "bind_budgets", lambda p, s, T, c, m: {"B": T + c, "r_opt": 5, "r_min": 3, "levels": {"bind": 4}})
    monkeypatch.setitem(bench.SOLVERS, "astar", lambda *a, **k: Result("no_path"))
    monkeypatch.setitem(bench.SOLVERS, "ilp", lambda *a, **k: Result("ok", cost=99.0, nodes=0, seconds=0.0))
    monkeypatch.setattr(bench.ilp, "ORTOOLS_AVAILABLE", True)
    rows = [r for r in _run(tmp_path, monkeypatch, "--design", "bind") if r["solver"] != "skipped"]
    assert rows and {r["solver"] for r in rows} == {"astar", "ilp"}
    assert all(r["status"] == "no_path" and r["ok"] == "0" for r in rows if r["solver"] == "astar")


def test_report_accepts_old_format_constrained_csv(tmp_path):
    (tmp_path / "constrained_river.csv").write_text(
        "bench,T,solver,status,ok,R,cost,agrees_with_astar,nodes,seconds\n"
        "river,5,astar,ok,1,3,5.0,1,10,0.1\nriver,5,ilp,ok,1,3,5.0,1,10,0.1\nriver,7,skipped,infeasible,0,,,,,\n")
    bench.run_report(type("A", (), {"out": str(tmp_path)})())
    md = (tmp_path / "results.md").read_text()
    assert "| river | frac | 5 | astar |" in md


def test_bind_rows_on_toy_instance(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(bench, "make_instances", lambda *a: [SimpleNamespace(problem=GRAPH, start="A", T=2)])
    rows = _run(tmp_path, monkeypatch, "--design", "bind", "--c_slack", "1")
    astar_rows = {r["level"]: r for r in rows if r["solver"] == "astar"}
    assert {k: (v["R"], v["B"], v["cost"], v["forced_longer"]) for k, v in astar_rows.items()} == {
        "bind": ("5", "3", "3.0", "1"), "tight": ("3", "3", "3.0", "1")}
    if bench.ilp.ORTOOLS_AVAILABLE:
        assert {r["agrees_with_astar"] for r in rows if r["solver"] == "ilp"} == {"1"}
