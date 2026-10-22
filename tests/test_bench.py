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
