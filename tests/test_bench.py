import csv
import sys

from tapegraph import bench
from tapegraph.benchmarks import BENCHMARKS, make_instances


def test_make_instances_fills_buckets_with_true_distances():
    insts = make_instances("river", per_bucket=2, seed=0)
    assert len(insts) == 2 * len(BENCHMARKS["river"].T_targets)
    for i in insts:
        assert i.oracle.dist(i.start) == i.T


def test_cli_end_to_end_on_river(tmp_path, monkeypatch):
    out = str(tmp_path)
    for cmd in ("solvers", "agents", "constrained"):
        monkeypatch.setattr(sys, "argv", ["bench", cmd, "--bench", "river", "--n", "1", "--episodes", "3", "--out", out])
        bench.main()
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", out])
    bench.main()
    rows = list(csv.DictReader(open(tmp_path / "solvers_river.csv")))
    assert {r["solver"] for r in rows} >= {"bfs", "astar", "wastar", "idastar"}
    assert all(r["status"] == "ok" for r in rows if r["solver"] == "astar")
    agents = {r["method"] for r in csv.DictReader(open(tmp_path / "agents_river.csv"))}
    assert agents >= {"react", "tape", "ours_astar"}
    assert "river" in (tmp_path / "results.md").read_text()


def test_constrained_records_ilp_timeout(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setitem(bench.SOLVERS, "ilp", lambda *a, **k: Result("timeout", nodes=0, seconds=0.0))
    monkeypatch.setattr(bench.ilp, "ORTOOLS_AVAILABLE", True)
    monkeypatch.setattr(sys, "argv", ["bench", "constrained", "--bench", "river", "--n", "1", "--out", str(tmp_path)])
    bench.main()
    rows = [r for r in csv.DictReader(open(tmp_path / "constrained_river.csv")) if r["solver"] == "ilp"]
    assert rows and all(r["status"] == "timeout" and r["ok"] == "0" and r["agrees_with_astar"] == "0" for r in rows)
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path)])
    bench.main()
    md = (tmp_path / "results.md").read_text()
    section = md[md.index("Failure breakdown: constrained"):]
    header, ilp = None, None
    for l in section.splitlines():
        cells = [c.strip() for c in l.strip("|").split("|")]
        header = cells if cells[0] == "bench" else header
        ilp = dict(zip(header, cells)) if cells[:2] == ["river", "ilp"] else ilp
    assert ilp["timeout"] == ilp["n"] != "0" and ilp["ok"] == "0"


def _run_constrained(tmp_path, monkeypatch, *extra):
    monkeypatch.setattr(sys, "argv", ["bench", "constrained", "--bench", "river", "--n", "1", "--out", str(tmp_path), *extra])
    bench.main()
    return list(csv.DictReader(open(tmp_path / "constrained_river.csv")))


def test_summarize_keeps_failure_groups():
    rows = [{"bench": "b", "T": 5, "solver": "s", "ok": 0, "cost": ""}]
    assert bench.summarize(rows, ["bench", "T", "solver"], ["ok", "cost"]) == [
        {"bench": "b", "T": 5, "solver": "s", "n": 1, "ok": 0, "cost": ""}]


def test_constrained_writes_skipped_row_when_infeasible(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setitem(bench.SOLVERS, "astar", lambda *a, **k: Result("no_path"))
    rows = _run_constrained(tmp_path, monkeypatch)
    assert len(rows) == 6 and {(r["solver"], r["status"], r["ok"]) for r in rows} == {("skipped", "infeasible", "0")}


def test_constrained_writes_skipped_row_when_base_fails(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setattr(bench.astar, "solve", lambda *a, **k: Result("node_limit"))
    rows = _run_constrained(tmp_path, monkeypatch)
    assert len(rows) == 6 and {(r["solver"], r["status"], r["ok"]) for r in rows} == {("skipped", "node_limit", "0")}


def test_constrained_failed_astar_keeps_both_rows_with_zero_agreement(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setitem(bench.SOLVERS, "astar", lambda *a, **k: Result("node_limit"))
    rows = _run_constrained(tmp_path, monkeypatch)
    assert {r["solver"] for r in rows} >= {"astar"}
    assert all(r["agrees_with_astar"] == "0" for r in rows)
    assert all(r["cost"] == "" for r in rows if r["solver"] == "astar")


def test_agents_use_distinct_seed_per_instance_shared_across_methods(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(bench, "evaluate", lambda p, s, pol, B, eta, eps, seed: calls.append((id(s), type(pol).__name__, seed))
                        or {"success": 1.0, "mean_steps": 1.0, "solves": 0.0, "seconds": 0.0})
    monkeypatch.setattr(sys, "argv", ["bench", "agents", "--bench", "river", "--n", "1", "--episodes", "1", "--out", str(tmp_path)])
    bench.main()
    seeds = [seed for _, _, seed in calls]
    runs = [seeds[0]] + [b for a, b in zip(seeds, seeds[1:]) if a != b]  # consecutive calls = methods of one instance
    assert len(runs) == len(set(runs)) == len(BENCHMARKS["river"].T_targets) > 1  # one seed per instance, all distinct
    assert len(seeds) == len(runs) * (len(seeds) // len(runs))  # same number of methods share each instance's seed


def _run_agents(tmp_path, monkeypatch, *extra):
    monkeypatch.setattr(sys, "argv", ["bench", "agents", "--bench", "river", "--n", "1", "--episodes", "2",
                                      "--out", str(tmp_path), *extra])
    bench.main()
    return list(csv.DictReader(open(tmp_path / "agents_river.csv")))


def test_agents_no_ilp_flag_and_parameter_columns(tmp_path, monkeypatch):
    rows = _run_agents(tmp_path / "no", monkeypatch, "--no_ilp")
    assert {r["method"] for r in rows} == {"react", "tape", "ours_astar"}
    assert {r["use_ilp"] for r in rows} == {"0"}
    r0 = rows[0]
    assert (r0["delta"], r0["eta"], r0["slack"], r0["episodes"], r0["N"], r0["seed"]) == ("0.16", "0.04", "2", "2", "16", "1")
    rows = _run_agents(tmp_path / "yes", monkeypatch)
    if bench.ilp.ORTOOLS_AVAILABLE:
        assert "ours_ilp" in {r["method"] for r in rows} and {r["use_ilp"] for r in rows} == {"1"}
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path / "yes")])
    bench.main()  # extra columns must not break the report
    assert "river" in (tmp_path / "yes" / "results.md").read_text()


def test_no_ilp_makes_tape_sim_use_graph_bfs(tmp_path, monkeypatch):
    made = []
    real = bench.TapeSim
    monkeypatch.setattr(bench, "TapeSim", lambda *a, **k: made.append(k.get("use_ilp")) or real(*a, **k))
    _run_agents(tmp_path, monkeypatch, "--no_ilp")
    assert made and set(made) == {False}


def test_constrained_skipped_row_records_ilp_status_and_report_counts_it(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setitem(bench.SOLVERS, "astar", lambda *a, **k: Result("no_path"))
    monkeypatch.setitem(bench.SOLVERS, "ilp", lambda *a, **k: Result("ok", nodes=0, seconds=0.0))  # a disagreement
    monkeypatch.setattr(bench.ilp, "ORTOOLS_AVAILABLE", True)
    rows = _run_constrained(tmp_path, monkeypatch)
    assert rows and all(r["solver"] == "skipped" and r["ilp_status"] == "ok" for r in rows)
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path)])
    bench.main()
    assert "{'ok': 6}" in (tmp_path / "results.md").read_text()
