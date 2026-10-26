"""Usage: python -m tapegraph {solvers|agents|constrained|report|all} --bench river --n 5 --out results
(`tapegraph all --profile smoke|full --out DIR` runs the whole pipeline; see README)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import shlex
import subprocess
import time
from collections import Counter, defaultdict
from functools import partial
from importlib import metadata
from pathlib import Path
from statistics import mean
from typing import NamedTuple

from . import __version__
from .baselines.react_sim import ReActSim
from .baselines.replan import Replan
from .baselines.tape_sim import TapeSim
from .benchmarks import BENCHMARKS, make_instances, use_boxoban_file
from .execute import evaluate
from .solvers import astar, bfs, idastar, ilp
from .stats import bootstrap_ci, wilson_interval

SOLVERS = {
    "bfs": bfs.solve,
    "astar": astar.solve,
    "wastar": partial(astar.solve, w=2.0),
    "idastar": idastar.solve,
    "ilp": ilp.solve,
}


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"[saved] {path} ({len(rows)} rows)")


def _usable(name):
    return name != "ilp" or ilp.ORTOOLS_AVAILABLE


def _params(a, *extra):
    """Run parameters stamped on every solvers/constrained row; `extra` names further args (slack, c_slack, res_frac)."""
    return {"seed": a.seed, "max_nodes": a.max_nodes, "n": a.n, "time_limit": a.time_limit,
            **{k: getattr(a, k) for k in extra}}


def _solve(a, name, *args, **kw):
    """SOLVERS[name](...); only the ILP takes a time limit."""
    if name == "ilp":
        kw["time_limit"] = a.time_limit
    return SOLVERS[name](*args, **kw)


def _idx(inst):
    """`index` column (position in a user-supplied file) only for those levels, so generated benches' CSVs are unchanged."""
    i = getattr(inst, "index", -1)  # tests build bare namespaces
    return {"index": i} if i >= 0 else {}


def _skip_row(inst, **head):
    """Row for a user-supplied level the oracle could not solve (T = -1): kept, with the oracle's status, never dropped."""
    return {"bench": head.pop("bench"), "T": -1, **_idx(inst), **head, "status": inst.skip, "ok": 0}


def run_solvers(a):
    rows = []
    for inst in make_instances(a.bench, a.n, a.seed):
        if inst.T < 0:  # unsolved user-supplied level
            rows.append({**_skip_row(inst, bench=a.bench, solver="skipped"), **_params(a, "slack")})
            continue
        B = inst.T + a.slack
        for name in a.solvers:
            if not _usable(name):
                continue
            r = _solve(a, name, inst.problem, inst.start, budget=B, max_nodes=a.max_nodes)
            rows.append({
                "bench": a.bench, "T": inst.T, "solver": name, "status": r.status, "ok": int(r.status == "ok"),
                "cost_ratio": r.cost / inst.T if r.status == "ok" else "",
                "nodes": r.nodes, "seconds": round(r.seconds, 5), **_idx(inst), **_params(a, "slack"),
            })
    _write(Path(a.out) / f"solvers_{a.bench}.csv", rows)


def run_agents(a):
    use_ilp = ilp.ORTOOLS_AVAILABLE and not a.no_ilp
    rows = []
    for idx, inst in enumerate(make_instances(a.bench, a.n, a.seed)):
        if inst.T < 0:  # unsolved user-supplied level
            rows.append(_skip_row(inst, bench=a.bench, method="skipped"))
            continue
        p, o, B = inst.problem, inst.oracle, inst.T + a.slack
        seed = a.seed + 7919 * idx  # per-instance noise; shared by all methods of one instance (paired comparison)
        makers = {
            "react": lambda: ReActSim(p, o, a.delta),
            "tape": lambda: TapeSim(p, o, a.delta, N=a.N, use_ilp=use_ilp),
            "ours_astar": lambda: Replan(p, astar.solve, max_nodes=a.max_nodes),
        }
        if use_ilp:
            makers["ours_ilp"] = lambda: Replan(p, ilp.solve, max_nodes=a.max_nodes)
        for name, mk in makers.items():
            r = evaluate(p, inst.start, mk(), B, a.eta, a.episodes, seed)
            rows.append({"bench": a.bench, "T": inst.T, "method": name, **{k: round(v, 5) for k, v in r.items()},
                         "delta": a.delta, "eta": a.eta, "slack": a.slack, "episodes": a.episodes, "N": a.N,
                         "use_ilp": int(use_ilp), "seed": a.seed, "inst_seed": seed, **_idx(inst)})
    _write(Path(a.out) / f"agents_{a.bench}.csv", rows)


def _constrained_frac(a):
    """min length s.t. length <= T*+slack and resource <= floor(res_frac * resource of the unconstrained optimum).
    Every instance yields a row: solver="skipped" when R cannot be derived (base A* failed) or is proven infeasible."""
    rows, skipped = [], 0
    for inst in make_instances(a.bench, a.n, a.seed):
        if inst.T < 0:  # unsolved user-supplied level
            skipped += 1
            rows.append({**_skip_row(inst, bench=a.bench, level="frac", solver="skipped"), **_params(a, "slack", "res_frac")})
            continue
        p, B = inst.problem, inst.T + a.slack
        head = {"bench": a.bench, "T": inst.T, "level": "frac", **_idx(inst)}
        tail = _params(a, "slack", "res_frac")
        base = astar.solve(p, inst.start, budget=B, max_nodes=a.max_nodes)
        if base.status != "ok":  # cannot derive R
            skipped += 1
            rows.append({**head, "solver": "skipped", "status": base.status, "ok": 0, **tail})
            continue
        R = math.floor(a.res_frac * base.res)
        results = {n: _solve(a, n, p, inst.start, budget=B, res_budget=R, max_nodes=a.max_nodes)
                   for n in ("astar", "ilp") if _usable(n)}
        ra = results["astar"]
        if ra.status == "no_path":  # proven infeasible at this resource budget
            skipped += 1
            # ilp_status makes a disagreement visible (ILP found a path where A* proved none)
            rows.append({**head, "solver": "skipped", "status": "infeasible", "ok": 0, "R": R,
                         "ilp_status": results["ilp"].status if "ilp" in results else "not_run", **tail})
            continue
        for n, r in results.items():
            rows.append({
                **head, "solver": n, "status": r.status, "ok": int(r.status == "ok"), "R": R,
                "cost": r.cost if r.status == "ok" else "",
                "agrees_with_astar": int(ra.status == "ok" and r.status == "ok" and r.cost == ra.cost),
                "nodes": r.nodes, "seconds": round(r.seconds, 5), **tail,
            })
    print(f"[constrained] skipped {skipped} infeasible/unsolved/already-solved instances (recorded as solver=skipped rows)")
    _write(Path(a.out) / f"constrained_{a.bench}.csv", rows)


class ResView:
    """Read-through proxy of a problem whose `res` is the problem's `res_bind` (the binding experiment's resource)."""

    def __init__(self, problem):
        self.problem = problem

    def __getattr__(self, name):  # only called for attributes not defined here
        return getattr(self.problem, name)

    def res(self, s, a, s2):
        return self.problem.res_bind(s, a, s2)


def _int_res(x):
    r = int(round(x))
    assert abs(x - r) < 1e-9, f"non-integer resource {x}"
    return r


def min_resource(problem, start, budget, hi, max_nodes):
    """Smallest integer R in [0, hi] with a feasible path (length <= budget, resource <= R), by bisection.
    hi must be feasible. Returns ("ok", R), or (status, None) as soon as any probe is neither ok nor no_path."""
    def probe(R):
        return astar.solve(problem, start, budget=budget, res_budget=R, max_nodes=max_nodes).status
    st = probe(hi)
    if st != "ok":
        return st, None
    lo = 0
    while lo < hi:
        mid = (lo + hi) // 2
        st = probe(mid)
        if st == "ok":
            hi = mid
        elif st == "no_path":
            lo = mid + 1
        else:
            return st, None
    return "ok", lo


def bind_budgets(problem, start, T, c_slack, max_nodes):
    """Budgets making the resource constraint bind yet stay feasible: R < r_opt (the length-T* optimum's minimal
    resource) forces a path longer than T*, and R >= r_min keeps one within T*+c_slack. {"skip": reason} otherwise."""
    base = astar.solve(problem, start, budget=T, max_nodes=max_nodes)
    if base.status != "ok":
        return {"skip": base.status}
    st, r_opt = min_resource(problem, start, T, _int_res(base.res), max_nodes)
    if r_opt is not None:
        st, r_min = min_resource(problem, start, T + c_slack, r_opt, max_nodes)
    if st != "ok":
        return {"skip": st}
    if r_min >= r_opt:  # also covers r_opt == 0, where no cheaper resource level exists
        return {"skip": "no_tradeoff"}
    levels = {"bind": r_opt - 1, "tight": r_min} if r_min < r_opt - 1 else {"bind": r_opt - 1}
    return {"B": T + c_slack, "r_opt": r_opt, "r_min": r_min, "levels": levels}


def _constrained_bind(a):
    """Resource budget that always binds: A* (and ILP) at B = T*+c_slack with R in {r_opt-1, r_min}; see bind_budgets."""
    rows, skipped = [], 0
    for inst in make_instances(a.bench, a.n, a.seed):
        if inst.T < 0:  # unsolved user-supplied level
            skipped += 1
            rows.append({**_skip_row(inst, bench=a.bench, level="-", solver="skipped"), **_params(a, "c_slack")})
            continue
        p = ResView(inst.problem)
        d = bind_budgets(p, inst.start, inst.T, a.c_slack, a.max_nodes)
        tail = _params(a, "c_slack")
        if "skip" in d:
            skipped += 1
            rows.append({"bench": a.bench, "T": inst.T, **_idx(inst), "level": "-", "solver": "skipped",
                         "status": d["skip"], "ok": 0, **tail})
            continue
        for level, R in d["levels"].items():
            results = {n: _solve(a, n, p, inst.start, budget=d["B"], res_budget=R, max_nodes=a.max_nodes)
                       for n in ("astar", "ilp") if _usable(n)}
            ra = results["astar"]
            for n, r in results.items():
                ok = r.status == "ok"
                rows.append({
                    "bench": a.bench, "T": inst.T, **_idx(inst), "level": level, "solver": n, "status": r.status, "ok": int(ok),
                    "R": R, "B": d["B"], "r_opt": d["r_opt"], "r_min": d["r_min"],
                    "cost": r.cost if ok else "",
                    "forced_longer": int(r.cost > inst.T) if ok else "",  # "" (not 0) so the report mean is over ok rows
                    "agrees_with_astar": int(ra.status == "ok" and ok and r.cost == ra.cost),
                    "nodes": r.nodes, "seconds": round(r.seconds, 5), **tail,
                })
    print(f"[constrained] skipped {skipped} instances with no binding feasible budget or no oracle solution (T=-1: oracle status or already_solved) (recorded as solver=skipped rows): "
          f"{dict(Counter(r['status'] for r in rows if r['solver'] == 'skipped'))}")
    _write(Path(a.out) / f"constrained_{a.bench}.csv", rows)


def run_constrained(a):
    {"bind": _constrained_bind, "frac": _constrained_frac}[a.design](a)


def _num(v):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def summarize(rows, group, metrics):
    buckets = defaultdict(list)
    for r in rows:
        buckets[tuple(r[k] for k in group)].append(r)
    out = []
    for key, rs in sorted(buckets.items(), key=lambda kv: kv[0]):  # each key position has one type: bench str, T int, name str
        row = dict(zip(group, key), n=len(rs))
        for m in metrics:
            vals = [float(r[m]) for r in rs if r.get(m) not in ("", None)]
            row[m] = round(mean(vals), 4) if vals else ""
        out.append(row)
    return out


STATUSES = ["ok", "no_path", "node_limit", "too_large", "timeout", "infeasible", "no_tradeoff"]


def status_table(rows, group=("bench", "solver")):
    """Per group: n and the count of each status value (canonical statuses first, then any others seen)."""
    seen = list(dict.fromkeys(r["status"] for r in rows))
    cols = [s for s in STATUSES if s in seen] + [s for s in seen if s not in STATUSES]
    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        counts[tuple(r[k] for k in group)][r["status"]] += 1
    return [{**dict(zip(group, key)), "n": sum(c.values()), **{s: c[s] for s in cols}}
            for key, c in sorted(counts.items())]


def _md(rows):
    if not rows:
        return "_no data_\n"
    keys = list(rows[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    return "\n".join(lines) + "\n"

# Episodes per instance of the published agents runs (README "How the results were produced"); only used for CSVs
# without an `episodes` column (written before that column existed).
DOCUMENTED_EPISODES = {"river": 100, "sokoban": 100, "boxoban": 20, "cube2": 30}


def _f4(x):
    return "" if x != x else f"{x:.4f}"


def agents_ci_sections(rows):
    """Three markdown sections (Wilson per bucket, pooled per benchmark, paired differences) from agents rows.
    successes = round(success * episodes) per instance row, trials = episodes per row; skipped rows (T < 0 or no
    success) are excluded and counted. An instance is a run of rows with distinct methods: `inst_seed` if the CSV has
    it, else the position of the cycle react/tape/ours_astar/... (rows of one instance are consecutive in the CSV)."""
    used, excluded, pos, unknown, dups, seen_keys = [], 0, {}, set(), 0, set()
    for r in rows:
        if r.get("method") == "skipped" or r.get("success") in ("", None) or r.get("T", 0) < 0:
            excluded += 1
            continue
        ep = r.get("episodes")
        looked_up = ep in ("", None)
        if looked_up and r["bench"] not in DOCUMENTED_EPISODES:  # old CSV of a benchmark with no documented episode count
            excluded += 1
            unknown.add(r["bench"])
            continue
        ep = DOCUMENTED_EPISODES[r["bench"]] if looked_up else int(ep)
        b = pos.setdefault(r["bench"], {"n": 0, "seen": set()})
        inst = r["inst_seed"] if r.get("inst_seed") not in ("", None) else None
        if inst is None:
            if r["method"] in b["seen"]:
                b["n"], b["seen"] = b["n"] + 1, set()
            b["seen"].add(r["method"])
            inst = b["n"]
        if (r["bench"], r["method"], inst) in seen_keys:  # e.g. concatenated CSVs: keep the first row, never overwrite silently
            dups += 1
            continue
        seen_keys.add((r["bench"], r["method"], inst))
        # success is stored to 5 decimals, so success * episodes is within 1e-5 * episodes of an integer: round() is exact for episodes < ~1e4
        used.append({**r, "inst": inst, "ep": ep, "k": round(float(r["success"]) * ep), "looked_up": looked_up})

    def pool(rs, extra):
        k, n = sum(r["k"] for r in rs), sum(r["ep"] for r in rs)
        lo, hi = wilson_interval(k, n)
        return {**extra, "instances": len({r["inst"] for r in rs}), "successes": k, "trials": n,
                "success": _f4(k / n), "ci_lo": _f4(lo), "ci_hi": _f4(hi)}

    def group(keys):
        g = defaultdict(list)
        for r in used:
            g[tuple(r[k] for k in keys)].append(r)
        return sorted(g.items(), key=lambda kv: kv[0])

    notes = f"Excluded from the intervals: {excluded} skipped rows (T = -1, no success value, or unknown episodes).\n"
    if unknown:
        notes += (f"Benchmarks without an `episodes` column and no documented episode count ({', '.join(sorted(unknown))}): "
                  "episodes unknown, their rows are excluded from these sections (counted above).\n")
    if dups:
        notes += f"{dups} duplicate rows (same bench, method and instance) dropped, first occurrence kept.\n"
    lk = sorted({r["bench"] for r in used if r["looked_up"]})
    if lk:
        notes += (f"Benchmarks without an `episodes` column ({', '.join(lk)}): episodes per instance taken from the documented "
                  f"lookup {DOCUMENTED_EPISODES} (README, how the results were produced).\n")
    pooling = "successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval"
    bucket = (f"## Agents: success per (bench, T*, method) with 95% Wilson intervals ({pooling})\n\n"
              + _md([pool(rs, dict(zip(("bench", "T", "method"), key))) for key, rs in group(("bench", "T", "method"))])
              + "\n" + notes)
    pooled = (f"## Agents: pooled per benchmark ({pooling}; the interval treats the trials as independent, "
              "although the episodes of one instance share a level)\n\n"
              + _md([{**pool(rs, dict(zip(("bench", "method"), key))), "episodes": ",".join(map(str, sorted({r["ep"] for r in rs})))}
                     for key, rs in group(("bench", "method"))])
              + "\n" + notes)
    prow, palign = [], []
    for bn in dict.fromkeys(r["bench"] for r in used):
        succ = defaultdict(dict)  # method -> instance -> success rate of that instance
        for r in used:
            if r["bench"] == bn:
                succ[r["method"]][r["inst"]] = r["k"] / r["ep"]
        for other in ("tape", "react"):
            a, o = succ.get("ours_astar", {}), succ.get(other, {})
            if not a or not o:
                continue
            if set(a) != set(o):
                palign.append(f"{bn}: instance sets of ours_astar ({len(a)}) and {other} ({len(o)}) do not align; "
                              "no paired difference reported.\n")
                continue
            d = [a[i] - o[i] for i in sorted(a)]
            lo, hi = bootstrap_ci(d)
            prow.append({"bench": bn, "comparison": f"ours_astar - {other}", "instances": len(d),
                         "mean_diff": _f4(sum(d) / len(d)), "ci_lo": _f4(lo), "ci_hi": _f4(hi)})
    paired = ("## Paired differences in success (mean over instances of success_ours_astar - success_other; "
              "95% percentile bootstrap, B = 2000, resampled over instances, paired by instance)\n\n"
              + _md(prow) + "\n" + "".join(palign) + notes)
    return [bucket, pooled, paired]


def run_report(a):
    out = Path(a.out)
    sections = [
        ("Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)", "solvers_*.csv",
         ["bench", "T", "solver"], ["ok", "cost_ratio", "nodes", "seconds"]),
        ("Agents (success within budget under noise)", "agents_*.csv", ["bench", "T", "method"],
         ["success", "mean_steps", "solves", "solver_fail", "seconds"]),
        ("Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R, or (T=-1) a user-supplied level skipped by the oracle: status = the oracle status or already_solved; cost means are over solved instances only)",
         "constrained_*.csv", ["bench", "level", "T", "solver"], ["ok", "forced_longer", "agrees_with_astar", "cost", "nodes", "seconds"]),
    ]
    md = ["# Results\n"]
    loaded = {}
    for title, pattern, group, metrics in sections:
        rows = []
        for f in sorted(out.glob(pattern)):
            rows += [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(open(f))]
        for r in rows:
            if pattern.startswith("constrained"):
                r.setdefault("level", "frac")  # CSVs written before the bind design have no level column
        loaded[pattern] = rows
        md.append(f"## {title}\n\n" + _md(summarize(rows, group, metrics)))
    for title, pattern in (("Failure breakdown: solvers (count of rows per status)", "solvers_*.csv"),
                           ("Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)", "constrained_*.csv")):
        md.append(f"## {title}\n\n" + _md(status_table(loaded[pattern])))
    skipped = [r for r in loaded["constrained_*.csv"] if r.get("solver") == "skipped" and r.get("status") == "infeasible"]
    rec = [r for r in skipped if r.get("ilp_status") not in ("", None)]
    counts = {st: sum(1 for r in rec if r["ilp_status"] == st) for st in sorted({r["ilp_status"] for r in rec})}
    md.append("ILP status on skipped-infeasible constrained rows (ilp_status recorded for "
              f"{len(rec)} of {len(skipped)}; ilp_status = ok would mean the ILP found a path where A* proved none): "
              f"{counts if counts else 'none recorded'}\n")
    md += agents_ci_sections(loaded["agents_*.csv"])  # appended after every older section
    (out / "results.md").write_text("\n".join(md))
    print(f"[saved] {out / 'results.md'}")


class Step(NamedTuple):
    sub: str  # output subdirectory of --out
    args: list  # bench CLI arguments without --out


def _steps(sub, *cmds):
    return [Step(sub, c.split()) for c in cmds]


def plan(profile):
    """The commands behind `all`. `full` = the published commands (README "Run" table, seed = CLI default 1);
    `smoke` = a tiny pass over River and Cube2 that exercises every code path (solvers, agents, constrained bind, report).
    Each experiment kind writes to its own subdirectory (frac and bind both write constrained_<bench>.csv) and gets one
    report, after its last experiment."""
    B = ["river", "sokoban", "boxoban", "cube2"]
    if profile == "full":
        agents = {"river": "--episodes 100", "sokoban": "--episodes 100", "boxoban": "--episodes 20 --no_ilp",
                  "cube2": "--episodes 30 --no_ilp"}
        bind_n = {"river": 20, "sokoban": 20, "boxoban": 10, "cube2": 4}
        groups = [
            ("solvers", [f"solvers --bench {b} --n 5" for b in B]),
            ("agents", [f"agents --bench {b} --n 5 {agents[b]}" for b in B]),
            ("constrained_frac", [f"constrained --design frac --bench {b} --n 5" for b in B]),
            ("constrained_bind", [f"constrained --design bind --c_slack 4 --bench {b} --n {bind_n[b]}" for b in B]),
        ]
    else:  # smoke: cube2 gets a small node cap so BFS/ILP fail fast instead of grinding
        cap = "--max_nodes 20000"
        groups = [
            ("solvers", ["solvers --bench river --n 1", f"solvers --bench cube2 --n 1 {cap}"]),
            ("agents", ["agents --bench river --n 1 --episodes 3", f"agents --bench cube2 --n 1 --episodes 2 --no_ilp {cap}"]),
            ("constrained_bind", ["constrained --design bind --bench river --n 1",
                                  f"constrained --design bind --bench cube2 --n 1 {cap}"]),
        ]
    return [st for sub, cmds in groups for st in _steps(sub, *cmds) + _steps(sub, "report")]


def _version(pkg):
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def _git_commit():
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _step_argv(st, out):
    return [*st.args, "--out", str(Path(out) / st.sub)]


def run_all(a):
    steps = plan(a.profile)
    parser = build_parser()
    man = {"profile": a.profile, "out": str(a.out), "python": platform.python_version(), "numpy": _version("numpy"),
           "ortools": _version("ortools"), "tapegraph": __version__, "git_commit": _git_commit(),
           "steps": [{"command": "python -m tapegraph.bench " + shlex.join(argv), "parameters": vars(parser.parse_args(argv)),
                      "seconds": None} for argv in (_step_argv(st, a.out) for st in steps)]}
    if a.dry_run:
        print(json.dumps(man, indent=2))
        return
    path = Path(a.out) / "run_manifest.json"
    for st, entry in zip(steps, man["steps"]):
        print(f"[all] {entry['command']}")
        t0 = time.perf_counter()
        main(_step_argv(st, a.out))
        entry["seconds"] = round(time.perf_counter() - t0, 3)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(man, indent=2))  # rewritten after every step: a long run leaves a usable partial manifest
    print(f"[saved] {path}")


def build_parser():
    ap = argparse.ArgumentParser(prog="tapegraph")
    ap.add_argument("cmd", choices=["solvers", "agents", "constrained", "report", "all"])
    ap.add_argument("--bench", choices=[*BENCHMARKS, "boxoban_file"], default="river")
    ap.add_argument("--boxoban_file", metavar="PATH",
                    help="solvers/agents/constrained, with --bench boxoban_file: DeepMind-format Boxoban text file; "
                         "--n then caps the number of levels used (first n)")
    ap.add_argument("--n", type=int, default=5, help="instances per T* bucket (with --boxoban_file: max levels)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--slack", type=int, default=2)
    ap.add_argument("--max_nodes", type=int, default=500_000)
    ap.add_argument("--solvers", nargs="+", default=list(SOLVERS))
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--delta", type=float, default=0.16, help="planning error rate (ReAct/TAPE sim)")
    ap.add_argument("--eta", type=float, default=0.04, help="execution noise rate")
    ap.add_argument("--N", type=int, default=16, help="rollouts folded by TAPE-sim")
    ap.add_argument("--res_frac", type=float, default=0.9, help="constrained: resource budget as a fraction of the optimum's")
    ap.add_argument("--design", choices=["bind", "frac"], default="bind",
                    help="constrained: bind = resource budget always binds (needs --c_slack); frac = res_frac of the optimum's")
    ap.add_argument("--c_slack", type=int, default=4, help="constrained bind: length budget is T*+c_slack")
    ap.add_argument("--no_ilp", action="store_true",
                    help="agents: skip ours_ilp and make TapeSim use BFS on the folded graph instead of the ILP")
    ap.add_argument("--time_limit", type=float, default=10.0, help="solvers/constrained: ILP time limit per solve, seconds")
    ap.add_argument("--profile", choices=["smoke", "full"], default="smoke",
                    help="all: smoke = tiny River+Cube2 pass; full = the published commands (hours)")
    ap.add_argument("--dry_run", action="store_true", help="all: print the commands and manifest skeleton, run nothing")
    ap.add_argument("--out", default="results")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if (a.bench == "boxoban_file") != bool(a.boxoban_file) or (a.boxoban_file and a.cmd == "all"):
        ap.error("--boxoban_file PATH and --bench boxoban_file go together (not valid with the 'all' subcommand)")
    if a.boxoban_file:
        try:
            use_boxoban_file(a.boxoban_file)
        except (OSError, ValueError) as e:
            ap.error(f"--boxoban_file {a.boxoban_file}: {e}")
    {"solvers": run_solvers, "agents": run_agents, "constrained": run_constrained, "report": run_report,
     "all": run_all}[a.cmd](a)


if __name__ == "__main__":
    main()
