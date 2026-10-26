"""Task 1 (packaging and polish): packaging, `all` subcommand, run-parameter columns, test gaps, solver_fail, probe script."""
import csv
import importlib.util
import json
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from toy import GRAPH, GraphProblem, assert_solvers_agree

import tapegraph
from tapegraph import bench
from tapegraph.baselines.replan import Replan
from tapegraph.benchmarks import BENCHMARKS, make_instances
from tapegraph.execute import evaluate
from tapegraph.problem import Problem, Result
from tapegraph.solvers import astar, bfs, idastar, ilp

ROOT = Path(__file__).resolve().parent.parent


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["bench", *args])
    bench.main()


# ---- 1. packaging ----------------------------------------------------------------------------------------------

def test_version_string():
    assert tapegraph.__version__ == "1.0.0"


def test_pyproject_declares_package_and_console_script():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert cfg["build-system"]["build-backend"].startswith("setuptools")
    assert cfg["project"]["name"] == "tapegraph"
    assert cfg["project"]["scripts"]["tapegraph"] == "tapegraph.bench:main"
    assert {d.split(">")[0].split("=")[0].strip().lower() for d in cfg["project"]["dependencies"]} == {"numpy", "ortools"}
    assert "pytest" in " ".join(cfg["project"]["optional-dependencies"]["test"])
    assert cfg["tool"]["setuptools"]["packages"]["find"]["include"] == ["tapegraph*"]


def test_python_dash_m_tapegraph_runs_the_cli(tmp_path):
    r = subprocess.run([sys.executable, "-m", "tapegraph", "solvers", "--bench", "river", "--n", "1", "--out", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "solvers_river.csv").exists()


# ---- 2. `all` subcommand ---------------------------------------------------------------------------------------

BENCHES = ["river", "sokoban", "boxoban", "cube2"]
FULL_ARGS = (
    [f"solvers --bench {b} --n 5" for b in BENCHES]
    + [f"agents --bench {b} --n 5 --episodes 100" for b in ("river", "sokoban")]
    + ["agents --bench boxoban --n 5 --episodes 20 --no_ilp", "agents --bench cube2 --n 5 --episodes 30 --no_ilp"]
    + [f"constrained --design frac --bench {b} --n 5" for b in BENCHES]
    + [f"constrained --design bind --c_slack 4 --bench {b} --n {n}" for b, n in
       (("river", 20), ("sokoban", 20), ("boxoban", 10), ("cube2", 4))]
)


def _experiments(steps):
    return [s for s in steps if s.args[0] != "report"]


def test_full_plan_is_exactly_the_readme_commands():
    steps = bench.plan("full")
    exp = _experiments(steps)
    assert [" ".join(s.args) for s in exp] == FULL_ARGS
    # each experiment kind has its own output subdirectory; frac and bind must differ (both write constrained_<bench>.csv)
    assert {s.sub for s in exp} == {"solvers", "agents", "constrained_frac", "constrained_bind"}
    # every experiment subdirectory gets exactly one report, after its last experiment
    reports = [(i, s.sub) for i, s in enumerate(steps) if s.args[0] == "report"]
    assert sorted(sub for _, sub in reports) == sorted({s.sub for s in exp})
    for i, sub in reports:
        assert i > max(j for j, s in enumerate(steps) if s.sub == sub and s.args[0] != "report")


def test_full_plan_matches_the_readme_text():
    readme = (ROOT / "README.md").read_text()
    for a in FULL_ARGS:
        cmd = "python -m tapegraph.bench " + a
        if "--design bind" in a:
            n = a.split("--n ")[1]
            b = a.split("--bench ")[1].split()[0]
            assert "constrained --design bind --c_slack 4" in readme and f"{b} --n {n}`" in readme, a
        else:
            b = a.split("--bench ")[1].split()[0]
            assert cmd in readme or cmd.replace(f"--bench {b} ", "--bench B ") in readme, a


def test_smoke_plan_covers_river_and_cube2_and_report():
    steps = bench.plan("smoke")
    kinds = Counter((s.args[0], s.args[s.args.index("--bench") + 1]) for s in steps if "--bench" in s.args)
    assert kinds == {(k, b): 1 for k in ("solvers", "agents", "constrained") for b in ("river", "cube2")}
    assert any(s.args[0] == "report" for s in steps)
    assert all("--n" in s.args and s.args[s.args.index("--n") + 1] == "1" for s in steps if "--bench" in s.args)
    assert all(s.args[s.args.index("--design") + 1] == "bind" for s in steps if s.args[0] == "constrained")


def test_dry_run_prints_manifest_skeleton_and_executes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bench, "run_solvers", lambda a: pytest.fail("dry run executed a step"))
    _argv(monkeypatch, "all", "--profile", "full", "--out", str(tmp_path / "o"), "--dry_run")
    man = json.loads(capsys.readouterr().out)
    cmds = [s["command"] for s in man["steps"] if " report " not in s["command"]]
    assert [c.split(" --out ")[0].removeprefix("python -m tapegraph.bench ") for c in cmds] == FULL_ARGS
    assert all(s["seconds"] is None and s["parameters"]["seed"] == 1 for s in man["steps"])
    assert not (tmp_path / "o").exists()


def test_all_runs_steps_sequentially_into_subdirs_and_writes_manifest(tmp_path, monkeypatch):
    small = [bench.Step("solvers", ["solvers", "--bench", "river", "--n", "1"]),
             bench.Step("agents", ["agents", "--bench", "river", "--n", "1", "--episodes", "1", "--no_ilp"]),
             bench.Step("constrained_bind", ["constrained", "--design", "bind", "--bench", "river", "--n", "1"]),
             bench.Step("solvers", ["report"])]
    monkeypatch.setattr(bench, "plan", lambda profile: small)
    out = tmp_path / "o"
    _argv(monkeypatch, "all", "--profile", "smoke", "--out", str(out))
    assert (out / "solvers" / "solvers_river.csv").exists() and (out / "solvers" / "results.md").exists()
    assert (out / "agents" / "agents_river.csv").exists()
    assert (out / "constrained_bind" / "constrained_river.csv").exists()
    man = json.loads((out / "run_manifest.json").read_text())
    assert man["profile"] == "smoke" and len(man["steps"]) == 4
    assert all(isinstance(s["seconds"], float) and s["seconds"] > 0 for s in man["steps"])
    assert man["steps"][0]["command"].endswith(f"--out {out / 'solvers'}") or str(out / "solvers") in man["steps"][0]["command"]
    assert man["steps"][2]["parameters"]["design"] == "bind" and man["steps"][2]["parameters"]["c_slack"] == 4
    assert man["python"].startswith("3.") and man["numpy"] and man["ortools"]
    assert "git_commit" in man  # a commit hash inside a checkout, None otherwise


def test_manifest_is_written_after_every_step(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(bench, "plan", lambda profile: [bench.Step("a", ["solvers", "--bench", "river", "--n", "1"]),
                                                       bench.Step("b", ["solvers", "--bench", "river", "--n", "1"])])
    real = bench.run_solvers

    def spy(a):
        mf = Path(tmp_path / "run_manifest.json")
        seen.append(json.loads(mf.read_text())["steps"][0]["seconds"] if mf.exists() else "absent")
        real(a)
    monkeypatch.setattr(bench, "run_solvers", spy)
    _argv(monkeypatch, "all", "--profile", "smoke", "--out", str(tmp_path))
    assert seen[0] == "absent" and isinstance(seen[1], float)  # step 1's timing is on disk before step 2 starts


# ---- 3. run parameters on every row ----------------------------------------------------------------------------

def _rows(path):
    return list(csv.DictReader(open(path)))


def test_solvers_rows_carry_run_parameters(tmp_path, monkeypatch):
    _argv(monkeypatch, "solvers", "--bench", "river", "--n", "1", "--max_nodes", "1234", "--slack", "3", "--seed", "5",
          "--time_limit", "7", "--out", str(tmp_path))
    rows = _rows(tmp_path / "solvers_river.csv")
    assert rows and all((r["seed"], r["slack"], r["max_nodes"], r["n"], r["time_limit"]) == ("5", "3", "1234", "1", "7.0")
                        for r in rows)


def test_time_limit_reaches_only_the_ilp(tmp_path, monkeypatch):
    got = {}
    monkeypatch.setitem(bench.SOLVERS, "ilp", lambda *a, **k: got.update(k) or Result("timeout"))
    monkeypatch.setattr(bench.ilp, "ORTOOLS_AVAILABLE", True)
    _argv(monkeypatch, "solvers", "--bench", "river", "--n", "1", "--time_limit", "3", "--out", str(tmp_path))
    assert got["time_limit"] == 3.0


def test_default_time_limit_is_the_ilp_default():
    assert bench.build_parser().parse_args(["solvers"]).time_limit == 10.0 == ilp.solve.__defaults__[-1]


def test_constrained_frac_rows_carry_run_parameters_including_skipped(tmp_path, monkeypatch):
    monkeypatch.setitem(bench.SOLVERS, "astar", lambda *a, **k: Result("no_path"))  # forces skipped rows
    _argv(monkeypatch, "constrained", "--design", "frac", "--bench", "river", "--n", "1", "--out", str(tmp_path))
    rows = _rows(tmp_path / "constrained_river.csv")
    assert rows and {r["solver"] for r in rows} == {"skipped"}
    assert all((r["seed"], r["slack"], r["max_nodes"], r["n"], r["time_limit"], r["res_frac"]) ==
               ("1", "2", "500000", "1", "10.0", "0.9") for r in rows)


def test_constrained_bind_rows_carry_run_parameters(tmp_path, monkeypatch):
    _argv(monkeypatch, "constrained", "--design", "bind", "--bench", "river", "--n", "2", "--c_slack", "3", "--seed", "2",
          "--out", str(tmp_path))
    rows = _rows(tmp_path / "constrained_river.csv")
    assert {r["solver"] for r in rows} >= {"skipped"} and {r["solver"] for r in rows} - {"skipped"}  # both row kinds
    assert all((r["seed"], r["c_slack"], r["max_nodes"], r["n"], r["time_limit"]) == ("2", "3", "500000", "2", "10.0")
               for r in rows)
    assert "slack" not in rows[0]  # bind has c_slack, not slack


def test_report_still_reads_old_solvers_and_agents_csvs(tmp_path):
    (tmp_path / "solvers_river.csv").write_text("bench,T,solver,status,ok,cost_ratio,nodes,seconds\n"
                                                "river,4,astar,ok,1,1.0,10,0.1\n")
    (tmp_path / "agents_river.csv").write_text("bench,T,method,success,mean_steps,solves,seconds\n"
                                               "river,4,tape,1.0,4.0,1.0,0.1\n")
    bench.run_report(type("A", (), {"out": str(tmp_path)})())
    md = (tmp_path / "results.md").read_text()
    assert "| river | 4 | astar |" in md and "| river | 4 | tape |" in md
    assert "solver_fail" in md and "| river | 4 | tape | 1 | 1.0 | 4.0 | 1.0 |  | 0.1 |" in md  # old CSV: blank, not a crash


def test_report_agents_table_shows_solver_fail(tmp_path):
    (tmp_path / "agents_river.csv").write_text("bench,T,method,success,mean_steps,solves,solver_fail,seconds\n"
                                               "river,4,ours_astar,1.0,4.0,2.0,0.5,0.1\n")
    bench.run_report(type("A", (), {"out": str(tmp_path)})())
    assert "| river | 4 | ours_astar | 1 | 1.0 | 4.0 | 2.0 | 0.5 | 0.1 |" in (tmp_path / "results.md").read_text()


# ---- 4. closing known test gaps (each one fails if the logic it pins is broken) ----------------------------------

def _chain(n):
    adj = {i: [(f"a{i}", i + 1, 0)] for i in range(n)}
    adj[n] = []
    return GraphProblem(adj, goal=n)


def test_bfs_node_limit():
    p = _chain(10)
    r = bfs.solve(p, 0, max_nodes=3)
    assert r.status == "node_limit" and r.nodes == 4  # fails on the first expansion past the cap
    assert bfs.solve(p, 0, max_nodes=10).status == "ok"  # exactly enough nodes: the cap is not off by one
    assert bfs.solve(p, 0, max_nodes=9).status == "node_limit"


class _CountsStartH(GraphProblem):
    """h = 0 (underestimates everything); counts h(start) calls = 1 initial bound + one per IDA* iteration."""
    start_h_calls = 0

    def h(self, s):
        self.start_h_calls += s == "A"
        return 0.0


def test_idastar_iterative_deepening_raises_the_bound_repeatedly():
    p = _CountsStartH(GRAPH.adj, goal="E")
    r = idastar.solve(p, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2  # still optimal with a useless h
    iterations = p.start_h_calls - 1
    assert iterations - 1 >= 2, "bound must increase at least twice (0 -> 1 -> 2)"
    assert iterations == 3


class _Inadmissible(Problem):
    """A->M->G is shortest (2) but h(M) = 10 overestimates, so A* prefers the 3-step detour A->P->Q->G."""
    adj = {"A": [("m", "M"), ("p", "P")], "M": [("g", "G")], "P": [("q", "Q")], "Q": [("g", "G")], "G": []}
    H = {"M": 10.0}

    def neighbors(self, s):
        return [(a, v, 1.0) for a, v in self.adj[s]]

    def is_goal(self, s):
        return s == "G"

    def h(self, s):
        return self.H.get(s, 0.0)


class _Admissible(_Inadmissible):
    H = {"M": 1.0}


def test_negative_control_inadmissible_h_is_detected():
    assert bfs.solve(_Inadmissible(), "A").cost == 2
    assert astar.solve(_Inadmissible(), "A").cost == 3  # A* is fooled
    with pytest.raises(AssertionError, match="inadmissible h"):
        assert_solvers_agree(_Inadmissible(), "A")
    assert assert_solvers_agree(_Admissible(), "A").cost == 2  # the same check passes with an admissible h


def test_make_instances_warns_on_stderr_when_a_bucket_underfills(monkeypatch, capsys):
    monkeypatch.setitem(BENCHMARKS, "river", replace(BENCHMARKS["river"], T_targets=[4, 999]))
    insts = make_instances("river", 2, 1, max_tries=30)
    err = capsys.readouterr().err
    assert [i.T for i in insts] == [4, 4]  # the reachable bucket filled, the impossible one did not
    assert "[make_instances] river T*=999: only 0/2 instances after 30 tries" in err
    assert "T*=4" not in err  # a filled bucket does not warn


def test_weighted_astar_weight_changes_the_path():
    # Optimal route via X has a large (admissible) h; the 5-step route via Y has h = 0. w = 1 finds the optimum, w = 2 is lured.
    adj = {"A": [("x", "X", 1), ("y", "Y", 1)], "X": [("x1", "X1", 1)], "X1": [("x2", "X2", 1)], "X2": [("g", "G", 1)],
           "Y": [("y1", "Y1", 1)], "Y1": [("y2", "Y2", 1)], "Y2": [("y3", "Y3", 1)], "Y3": [("g", "G", 1)], "G": []}
    p = GraphProblem(adj, goal="G", h={"A": 4, "X": 3, "X1": 2, "X2": 1})
    assert astar.solve(p, "A", w=1.0).cost == 4
    assert astar.solve(p, "A", w=2.0).cost == 5
    assert astar.solve(p, "A", w=2.0).path == ["y", "y1", "y2", "y3", "g"]


def test_min_resource_aborts_in_the_middle_of_the_bisection(monkeypatch):
    real, probed = astar.solve, []

    def flaky(problem, start, budget=None, res_budget=None, **k):
        probed.append(res_budget)
        return Result("timeout") if res_budget == 2 else real(problem, start, budget=budget, res_budget=res_budget, **k)

    monkeypatch.setattr(bench.astar, "solve", flaky)
    # hi=6 ok; mid 3 ok (hi=3); mid 1 no_path (lo=2); mid 2 -> timeout: abort, no bogus answer
    assert bench.min_resource(GRAPH, "A", 3, 6, 1000) == ("timeout", None)
    assert probed == [6, 3, 1, 2]


# ---- 5. solver_fail --------------------------------------------------------------------------------------------

def test_replan_counts_solver_failures_and_falls_back():
    p = GRAPH
    statuses = iter(["timeout", "ok"])

    def solver(problem, s, **k):
        st = next(statuses)
        return astar.solve(problem, s, **k) if st == "ok" else Result(st)

    pol = Replan(p, solver)
    assert pol.solver_fail == 0
    a = pol.act("A", 5)  # failing solve: plays the first legal action, counts the failure
    assert a == "ab" and pol.solves == 1 and pol.solver_fail == 1
    pol.act("C", 4)  # state differs from the one expected -> re-solve, now ok
    assert pol.solves == 2 and pol.solver_fail == 1


def test_evaluate_reports_solver_fail_per_episode():
    pol = Replan(GRAPH, lambda *a, **k: Result("node_limit"))
    r = evaluate(GRAPH, "A", pol, B=4, eta=0.0, episodes=4, seed=0)
    assert r["solver_fail"] == pol.solver_fail / 4 > 0
    ok = evaluate(GRAPH, "A", Replan(GRAPH, astar.solve), B=4, eta=0.0, episodes=4, seed=0)
    assert ok["solver_fail"] == 0.0


def test_agents_csv_has_a_solver_fail_column(tmp_path, monkeypatch):
    monkeypatch.setattr(bench.astar, "solve", lambda *a, **k: Result("node_limit"))
    _argv(monkeypatch, "agents", "--bench", "river", "--n", "1", "--episodes", "2", "--no_ilp", "--out", str(tmp_path))
    by = {}
    for r in _rows(tmp_path / "agents_river.csv"):
        by.setdefault(r["method"], []).append(float(r["solver_fail"]))
    assert set(by) == {"react", "tape", "ours_astar"}
    assert all(v > 0 for v in by["ours_astar"]) and set(by["react"]) == {0.0}  # silent fallbacks are now visible


def test_ilp_docstring_no_longer_claims_the_same_ball_as_astar():
    assert "same ball A* would expand" not in ilp.solve.__doc__
    assert "g + h <= budget" in ilp.solve.__doc__


# ---- 6. scripts/probe_resources.py -----------------------------------------------------------------------------

def _load_probe():
    spec = importlib.util.spec_from_file_location("probe_resources", ROOT / "scripts" / "probe_resources.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_probe_import_has_no_side_effects(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["probe_resources.py"])  # no bench argument: used to crash at import
    mod = _load_probe()
    assert capsys.readouterr().out == "" and callable(mod.main)
    with pytest.raises(SystemExit):
        mod.main([])  # the bench argument is required, so argparse (not an IndexError) complains


def test_probe_runs_one_benchmark_through_bench_min_resource(monkeypatch, capsys):
    mod = _load_probe()
    calls = []
    real = bench.min_resource
    monkeypatch.setattr(bench, "min_resource", lambda *a, **k: calls.append(a) or real(*a, **k))
    mod.main(["river", "--n", "1"])
    out = capsys.readouterr().out
    assert "== river: 6 instances" in out and "load^2" in out and "slack2:" in out
    assert calls, "the probe must reuse bench.min_resource, not its own bisection"
    assert not hasattr(mod, "min_res")


# ---- 7. CI -----------------------------------------------------------------------------------------------------

def test_ci_workflow_is_valid_and_runs_the_documented_steps():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    for needle in ("jobs:", "runs-on:", "steps:", "python-version", "3.12", 'pip install -e ".[test]"', "pytest -q",
                   "tapegraph all --profile smoke"):  # structural checks that need no YAML parser
        assert needle in text, needle
    assert chr(9) not in text, "tabs are not allowed in YAML indentation"
    yaml = pytest.importorskip("yaml")
    wf = yaml.safe_load(text)
    steps = next(iter(wf["jobs"].values()))["steps"]
    assert any("pytest -q" in s.get("run", "") for s in steps)
    assert any("tapegraph all --profile smoke" in s.get("run", "") for s in steps)
