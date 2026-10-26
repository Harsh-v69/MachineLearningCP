import csv
import sys

from tapegraph import bench
from tapegraph.benchmarks import BENCHMARKS, make_instances
from tapegraph.solvers import astar, bfs, idastar


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
    monkeypatch.setattr(sys, "argv", ["bench", "constrained", "--bench", "river", "--n", "1", "--design", "frac", "--out", str(tmp_path)])
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
    monkeypatch.setattr(sys, "argv", ["bench", "constrained", "--bench", "river", "--n", "1", "--design", "frac", "--out", str(tmp_path), *extra])
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


# ---- Task 2: multi-box Sokoban and --boxoban_file ----------------------------------------------------------------

from dataclasses import replace
from pathlib import Path

import pytest
from toy import assert_solvers_agree

from tapegraph import benchmarks
from tapegraph.problems.boxoban import load_boxoban_file

SAMPLE = Path(__file__).parent / "data" / "boxoban_sample.txt"


@pytest.mark.parametrize("name,boxes,shape", [("sokoban2", 2, (7, 9)), ("sokoban3", 3, (8, 10))])
def test_multibox_sokoban_benches_are_nontrivial_and_astar_idastar_match_bfs(monkeypatch, name, boxes, shape):
    monkeypatch.setitem(BENCHMARKS, name, replace(BENCHMARKS[name], T_targets=[6, 10]))  # BFS-feasible buckets only
    insts = make_instances(name, per_bucket=3, seed=5)
    assert len(insts) == 6
    costs = []
    for i in insts:
        assert (i.problem.H, i.problem.W) == shape and len(i.start[1]) == boxes and i.T > 0  # no already-solved starts
        b = bfs.solve(i.problem, i.start)  # BFS ignores h and prune
        assert b.status == "ok" and b.cost == i.T
        assert_solvers_agree(i.problem, i.start, b)
        costs.append(astar.solve(i.problem, i.start).cost)
    assert sum(c >= 8 for c in costs) >= 3, costs  # actual data: 3 of 6 for each bench; several non-shallow instances


def test_astar_and_idastar_agree_on_sokoban2_high_buckets(monkeypatch):
    monkeypatch.setitem(BENCHMARKS, "sokoban2", replace(BENCHMARKS["sokoban2"], T_targets=[14, 18]))
    insts = make_instances("sokoban2", per_bucket=2, seed=3)
    assert len(insts) == 4 and min(i.T for i in insts) >= 13
    for i in insts:
        a, d = astar.solve(i.problem, i.start), idastar.solve(i.problem, i.start)
        assert a.status == d.status == "ok" and a.cost == d.cost == i.T


def test_multibox_targets_reach_beyond_the_single_box_ones():
    assert max(BENCHMARKS["sokoban2"].T_targets) >= max(BENCHMARKS["sokoban"].T_targets)
    assert max(BENCHMARKS["sokoban3"].T_targets) > max(BENCHMARKS["sokoban2"].T_targets)


def test_boxoban_file_is_not_registered_by_default():
    assert "boxoban_file" not in BENCHMARKS


UNSOLVABLE = ["##########", "#        #", "#.       #", "#        #", "#   @    #", "#        #", "#        #",
              "#        #", "#       $#", "##########"]  # the box sits in a dead corner; goal elsewhere


def _file_with_unsolvable(tmp_path):
    path = tmp_path / "levels.txt"
    path.write_text(SAMPLE.read_text() + "\n; 3\n" + "\n".join(UNSOLVABLE) + "\n")
    return path


def _boxoban_file_run(tmp_path, monkeypatch, cmd, path, *extra):
    monkeypatch.setitem(BENCHMARKS, "boxoban_file", None)  # restored on teardown, so the registry stays clean
    monkeypatch.setattr(sys, "argv", ["bench", cmd, "--bench", "boxoban_file", "--boxoban_file", str(path), "--n", "10",
                                      "--out", str(tmp_path), *extra])
    bench.main()
    return list(csv.DictReader(open(tmp_path / f"{cmd}_boxoban_file.csv")))


def test_solvers_on_boxoban_file_use_oracle_distances_and_record_unsolvable_as_skipped(tmp_path, monkeypatch):
    rows = _boxoban_file_run(tmp_path, monkeypatch, "solvers", _file_with_unsolvable(tmp_path), "--solvers", "bfs", "astar")
    assert {r["bench"] for r in rows} == {"boxoban_file"}
    good = [r for r in rows if r["solver"] != "skipped"]
    assert len(good) == 3 * 2 and all(r["status"] == "ok" for r in good)
    levels = load_boxoban_file(SAMPLE)
    want = sorted(int(bfs.solve(p, s).cost) for p, s in levels)
    assert sorted(int(r["T"]) for r in good if r["solver"] == "bfs") == want
    skipped = [r for r in rows if r["solver"] == "skipped"]
    assert len(skipped) == 1 and skipped[0]["status"] == "no_path" and skipped[0]["ok"] == "0"
    assert skipped[0]["index"] == "3" and skipped[0]["n"] == "10"
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path)])
    bench.main()  # skipped rows must not break the report
    assert "no_path" in (tmp_path / "results.md").read_text()


def test_n_caps_the_number_of_levels_used(tmp_path, monkeypatch):
    rows = _boxoban_file_run(tmp_path, monkeypatch, "solvers", SAMPLE, "--solvers", "astar", "--n", "2")
    assert len(rows) == 2


def test_agents_and_constrained_on_boxoban_file_keep_skipped_levels(tmp_path, monkeypatch):
    path = _file_with_unsolvable(tmp_path)
    rows = _boxoban_file_run(tmp_path / "a", monkeypatch, "agents", path, "--episodes", "2", "--no_ilp")
    assert {r["method"] for r in rows if r["method"] != "skipped"} == {"react", "tape", "ours_astar"}
    assert [(r["status"], r["index"]) for r in rows if r["method"] == "skipped"] == [("no_path", "3")]
    for design in ("bind", "frac"):
        rows = _boxoban_file_run(tmp_path / design, monkeypatch, "constrained", path, "--design", design)
        sk = [r for r in rows if r["solver"] == "skipped" and r["index"] == "3"]
        assert len(sk) == 1 and sk[0]["status"] == "no_path" and sk[0]["ok"] == "0"
        assert {r["T"] for r in rows} >= {"-1"}


def test_oracle_node_limit_gives_skipped_rows_with_that_status(tmp_path, monkeypatch):
    from tapegraph.problem import Result
    monkeypatch.setattr(benchmarks.astar, "solve", lambda *a, **k: Result("node_limit"))
    rows = _boxoban_file_run(tmp_path, monkeypatch, "solvers", SAMPLE)
    assert len(rows) == 3 and {(r["solver"], r["status"], r["ok"]) for r in rows} == {("skipped", "node_limit", "0")}


def test_boxoban_file_cli_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(BENCHMARKS, "boxoban_file", None)
    bad = tmp_path / "bad.txt"
    bad.write_text("; 4\n####\n#@$#\n####\n")  # one box, no goal: rejected by the validator, error names level 4
    for argv in (["solvers", "--bench", "boxoban_file"],  # no file
                 ["solvers", "--bench", "river", "--boxoban_file", str(SAMPLE)],  # file with another bench
                 ["solvers", "--bench", "boxoban_file", "--boxoban_file", str(tmp_path / "nope.txt")],
                 ["solvers", "--bench", "boxoban_file", "--boxoban_file", str(bad)]):
        monkeypatch.setattr(sys, "argv", ["bench", *argv, "--out", str(tmp_path)])
        with pytest.raises(SystemExit):
            bench.main()
    assert "level 4" in capsys.readouterr().err


def test_generated_benches_keep_their_csv_columns(tmp_path, monkeypatch):
    for cmd in ("solvers", "agents", "constrained"):
        monkeypatch.setattr(sys, "argv", ["bench", cmd, "--bench", "river", "--n", "1", "--episodes", "1", "--out", str(tmp_path)])
        bench.main()
    for f in tmp_path.glob("*_river.csv"):
        assert "index" not in open(f).readline()


def test_sokoban2_fills_every_bucket_without_warning(capsys):
    insts = make_instances("sokoban2", per_bucket=5, seed=1)  # sokoban3 takes ~25 s, so it is tuned by hand (README/report)
    assert len(insts) == 5 * len(BENCHMARKS["sokoban2"].T_targets) and capsys.readouterr().err == ""
    assert all(i.T > 0 for i in insts)


SOLVED = ["####", "#@*#", "####"]  # the only box already sits on the only goal


def test_already_solved_loaded_level_is_a_skipped_row_in_every_command(tmp_path, monkeypatch):
    path = tmp_path / "solved.txt"
    path.write_text(SAMPLE.read_text() + "\n; 3\n" + "\n".join(SOLVED) + "\n")
    rows = _boxoban_file_run(tmp_path / "s", monkeypatch, "solvers", path, "--solvers", "astar")  # no ZeroDivisionError
    assert len(rows) == 4 and [r["status"] for r in rows if r["solver"] == "skipped"] == ["already_solved"]
    rows = _boxoban_file_run(tmp_path / "a", monkeypatch, "agents", path, "--episodes", "2", "--no_ilp")
    assert [(r["status"], r["index"], r["T"]) for r in rows if r["method"] == "skipped"] == [("already_solved", "3", "-1")]
    for design in ("bind", "frac"):
        rows = _boxoban_file_run(tmp_path / design, monkeypatch, "constrained", path, "--design", design)
        sk = [r for r in rows if r["solver"] == "skipped" and r["status"] == "already_solved"]
        assert [(r["status"], r["index"], r["ok"], r["T"]) for r in sk] == [("already_solved", "3", "0", "-1")]
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", str(tmp_path / "bind")])
    bench.main()
    assert "already_solved" in (tmp_path / "bind" / "results.md").read_text()
