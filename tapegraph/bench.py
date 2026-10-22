"""Usage: python -m tapegraph.bench {solvers|agents|constrained|report} --bench river --n 5 --out results"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from functools import partial
from pathlib import Path
from statistics import mean

from .baselines.react_sim import ReActSim
from .baselines.replan import Replan
from .baselines.tape_sim import TapeSim
from .benchmarks import BENCHMARKS, make_instances
from .execute import evaluate
from .solvers import astar, bfs, idastar, ilp

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


def run_solvers(a):
    rows = []
    for inst in make_instances(a.bench, a.n, a.seed):
        B = inst.T + a.slack
        for name in a.solvers:
            if not _usable(name):
                continue
            r = SOLVERS[name](inst.problem, inst.start, budget=B, max_nodes=a.max_nodes)
            rows.append({
                "bench": a.bench, "T": inst.T, "solver": name, "status": r.status, "ok": int(r.status == "ok"),
                "cost_ratio": r.cost / inst.T if r.status == "ok" else "",
                "nodes": r.nodes, "seconds": round(r.seconds, 5),
            })
    _write(Path(a.out) / f"solvers_{a.bench}.csv", rows)


def run_agents(a):
    rows = []
    for inst in make_instances(a.bench, a.n, a.seed):
        p, o, B = inst.problem, inst.oracle, inst.T + a.slack
        makers = {
            "react": lambda: ReActSim(p, o, a.delta),
            "tape": lambda: TapeSim(p, o, a.delta, N=a.N),
            "ours_astar": lambda: Replan(p, astar.solve, max_nodes=a.max_nodes),
        }
        if ilp.ORTOOLS_AVAILABLE:
            makers["ours_ilp"] = lambda: Replan(p, ilp.solve, max_nodes=a.max_nodes)
        for name, mk in makers.items():
            r = evaluate(p, inst.start, mk(), B, a.eta, a.episodes, a.seed)
            rows.append({"bench": a.bench, "T": inst.T, "method": name, **{k: round(v, 5) for k, v in r.items()}})
    _write(Path(a.out) / f"agents_{a.bench}.csv", rows)


def run_constrained(a):
    """min length s.t. length <= T*+slack and resource <= floor(res_frac * resource of the unconstrained optimum).
    Every instance yields a row: solver="skipped" when R cannot be derived (base A* failed) or is proven infeasible."""
    rows, skipped = [], 0
    for inst in make_instances(a.bench, a.n, a.seed):
        p, B = inst.problem, inst.T + a.slack
        head = {"bench": a.bench, "T": inst.T}
        base = astar.solve(p, inst.start, budget=B, max_nodes=a.max_nodes)
        if base.status != "ok":  # cannot derive R
            skipped += 1
            rows.append({**head, "solver": "skipped", "status": base.status, "ok": 0})
            continue
        R = math.floor(a.res_frac * base.res)
        results = {n: SOLVERS[n](p, inst.start, budget=B, res_budget=R, max_nodes=a.max_nodes)
                   for n in ("astar", "ilp") if _usable(n)}
        ra = results["astar"]
        if ra.status == "no_path":  # proven infeasible at this resource budget
            skipped += 1
            rows.append({**head, "solver": "skipped", "status": "infeasible", "ok": 0, "R": R})
            continue
        for n, r in results.items():
            rows.append({
                **head, "solver": n, "status": r.status, "ok": int(r.status == "ok"), "R": R,
                "cost": r.cost if r.status == "ok" else "",
                "agrees_with_astar": int(ra.status == "ok" and r.status == "ok" and r.cost == ra.cost),
                "nodes": r.nodes, "seconds": round(r.seconds, 5),
            })
    print(f"[constrained] skipped {skipped} infeasible/unsolved instances (recorded as solver=skipped rows)")
    _write(Path(a.out) / f"constrained_{a.bench}.csv", rows)


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


STATUSES = ["ok", "no_path", "node_limit", "too_large", "timeout", "infeasible"]


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


def run_report(a):
    out = Path(a.out)
    sections = [
        ("Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)", "solvers_*.csv",
         ["bench", "T", "solver"], ["ok", "cost_ratio", "nodes", "seconds"]),
        ("Agents (success within budget under noise)", "agents_*.csv", ["bench", "T", "method"],
         ["success", "mean_steps", "solves", "seconds"]),
        ("Constrained (length + resource budget; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)",
         "constrained_*.csv", ["bench", "T", "solver"], ["ok", "agrees_with_astar", "cost", "nodes", "seconds"]),
    ]
    md = ["# Results\n"]
    loaded = {}
    for title, pattern, group, metrics in sections:
        rows = []
        for f in sorted(out.glob(pattern)):
            rows += [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(open(f))]
        loaded[pattern] = rows
        md.append(f"## {title}\n\n" + _md(summarize(rows, group, metrics)))
    for title, pattern in (("Failure breakdown: solvers (count of rows per status)", "solvers_*.csv"),
                           ("Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)", "constrained_*.csv")):
        md.append(f"## {title}\n\n" + _md(status_table(loaded[pattern])))
    (out / "results.md").write_text("\n".join(md))
    print(f"[saved] {out / 'results.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["solvers", "agents", "constrained", "report"])
    ap.add_argument("--bench", choices=list(BENCHMARKS), default="river")
    ap.add_argument("--n", type=int, default=5, help="instances per T* bucket")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--slack", type=int, default=2)
    ap.add_argument("--max_nodes", type=int, default=500_000)
    ap.add_argument("--solvers", nargs="+", default=list(SOLVERS))
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--delta", type=float, default=0.16, help="planning error rate (ReAct/TAPE sim)")
    ap.add_argument("--eta", type=float, default=0.04, help="execution noise rate")
    ap.add_argument("--N", type=int, default=16, help="rollouts folded by TAPE-sim")
    ap.add_argument("--res_frac", type=float, default=0.9, help="constrained: resource budget as a fraction of the optimum's")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    {"solvers": run_solvers, "agents": run_agents, "constrained": run_constrained, "report": run_report}[a.cmd](a)


if __name__ == "__main__":
    main()
