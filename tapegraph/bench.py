"""Usage: python -m tapegraph.bench {solvers|agents|constrained|report} --bench river --n 5 --out results"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
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
    use_ilp = ilp.ORTOOLS_AVAILABLE and not a.no_ilp
    rows = []
    for idx, inst in enumerate(make_instances(a.bench, a.n, a.seed)):
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
                         "use_ilp": int(use_ilp), "seed": a.seed, "inst_seed": seed})
    _write(Path(a.out) / f"agents_{a.bench}.csv", rows)


def _constrained_frac(a):
    """min length s.t. length <= T*+slack and resource <= floor(res_frac * resource of the unconstrained optimum).
    Every instance yields a row: solver="skipped" when R cannot be derived (base A* failed) or is proven infeasible."""
    rows, skipped = [], 0
    for inst in make_instances(a.bench, a.n, a.seed):
        p, B = inst.problem, inst.T + a.slack
        head = {"bench": a.bench, "T": inst.T, "level": "frac"}
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
            # ilp_status makes a disagreement visible (ILP found a path where A* proved none)
            rows.append({**head, "solver": "skipped", "status": "infeasible", "ok": 0, "R": R,
                         "ilp_status": results["ilp"].status if "ilp" in results else "not_run"})
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
        p = ResView(inst.problem)
        d = bind_budgets(p, inst.start, inst.T, a.c_slack, a.max_nodes)
        if "skip" in d:
            skipped += 1
            rows.append({"bench": a.bench, "T": inst.T, "level": "-", "solver": "skipped", "status": d["skip"], "ok": 0})
            continue
        for level, R in d["levels"].items():
            results = {n: SOLVERS[n](p, inst.start, budget=d["B"], res_budget=R, max_nodes=a.max_nodes)
                       for n in ("astar", "ilp") if _usable(n)}
            ra = results["astar"]
            for n, r in results.items():
                ok = r.status == "ok"
                rows.append({
                    "bench": a.bench, "T": inst.T, "level": level, "solver": n, "status": r.status, "ok": int(ok),
                    "R": R, "B": d["B"], "r_opt": d["r_opt"], "r_min": d["r_min"],
                    "cost": r.cost if ok else "",
                    "forced_longer": int(r.cost > inst.T) if ok else "",  # "" (not 0) so the report mean is over ok rows
                    "agrees_with_astar": int(ra.status == "ok" and ok and r.cost == ra.cost),
                    "nodes": r.nodes, "seconds": round(r.seconds, 5),
                })
    print(f"[constrained] skipped {skipped} instances with no binding feasible budget (recorded as solver=skipped rows): "
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


def run_report(a):
    out = Path(a.out)
    sections = [
        ("Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)", "solvers_*.csv",
         ["bench", "T", "solver"], ["ok", "cost_ratio", "nodes", "seconds"]),
        ("Agents (success within budget under noise)", "agents_*.csv", ["bench", "T", "method"],
         ["success", "mean_steps", "solves", "seconds"]),
        ("Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)",
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
    ap.add_argument("--design", choices=["bind", "frac"], default="bind",
                    help="constrained: bind = resource budget always binds (needs --c_slack); frac = res_frac of the optimum's")
    ap.add_argument("--c_slack", type=int, default=4, help="constrained bind: length budget is T*+c_slack")
    ap.add_argument("--no_ilp", action="store_true",
                    help="agents: skip ours_ilp and make TapeSim use BFS on the folded graph instead of the ILP")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    {"solvers": run_solvers, "agents": run_agents, "constrained": run_constrained, "report": run_report}[a.cmd](a)


if __name__ == "__main__":
    main()
