"""Assemble the paper-style write-up docs/paper.md from the committed CSVs (stdlib + numpy only, deterministic).

    python scripts/make_paper.py [--data docs/data] [--figures docs/figures] [--out docs/paper.md]

Every table and every number inside a generated sentence is computed here from the CSVs under --data, with the helpers
shared with `tapegraph.bench` (report) and `scripts/make_figures.py` (data discovery, bind pairing). The hand-written
prose (method, related work, limitations) carries no measured numbers. Planned agents files that have not landed yet
(PENDING) print one explicit 'pending' line. One agents dataset per benchmark enters the tables (most episodes; the
others are superseded, see `pick_agents`). Text between the INTERPRETATION-7.4 markers of an existing output file is
carried over when the file is regenerated (broken markers raise). Figures are linked only when the SVG exists.
"""
from __future__ import annotations

import argparse
import inspect
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_figures import SEC_FLOOR, _order, _suffixes, best_agents, bind_by_bench, bind_pairs, load  # noqa: E402
from tapegraph.bench import (SOLVERS, _md, agent_instance_rows, build_parser, is_bind_csv, paired_differences, plan,  # noqa: E402
                             pool_success, status_table, summarize)
from tapegraph.benchmarks import BENCHMARKS, _river, make_instances  # noqa: E402
from tapegraph.problems import cube2, cube3  # noqa: E402
from tapegraph.stats import bootstrap_ci  # noqa: E402
from tapegraph.oracle import Oracle  # noqa: E402
from tapegraph.solvers import ilp  # noqa: E402

BENCH_ORDER = ["river", "sokoban", "sokoban2", "sokoban3", "boxoban", "cube2", "cube3"]
METHODS = ["react", "tape", "ours_astar", "ours_ilp"]
LABEL = {"react": "react (simulated)", "tape": "tape (simulated)", "ours_astar": "ours_astar", "ours_ilp": "ours_ilp"}
SOLVER_ORDER = ["bfs", "astar", "wastar", "idastar", "ilp"]
EXACT = ("bfs", "astar", "idastar", "ilp")
PENDING = {  # agents files planned when this generator was written: (dir, bench) -> description of the planned run
    ("new_agents", "sokoban2"): "100 episodes",
    ("new_agents", "sokoban3"): "30 episodes, --no_ilp",
    ("new_agents", "cube3"): "20 episodes, --no_ilp",
    ("agents_ep300", "river"): "300 episodes, ILP enabled",
    ("agents_ep300", "sokoban"): "300 episodes, ILP enabled",
}
ATTEMPTED = {  # planned agents files whose runs were attempted and abandoned: reported instead of "pending"
    ("new_agents", "cube3"): (
        "the cube3 agents run was attempted twice and did not complete. The full run (`--n 5 --episodes 20 --no_ilp "
        "--max_nodes 100000`) was stopped after 3 h (176 CPU-minutes) and a reduced run (`--n 2 --episodes 10`, same "
        "flags) after 54 min (53 CPU-minutes); neither wrote a result file, because the agents CSV is written only "
        "when a benchmark's run ends. The likely cause, not verified, is the exact-distance oracle (A* with a "
        "corner-only pattern database, about 10k nodes/s, 300,000-node cap) that the simulated ReAct and TAPE query "
        "on every off-path state."),
}
# Run configuration the older CSVs do not record (README "Run" and "How the results were produced"; .run_new.sh for
# the newer runs). Newer CSVs carry their parameters as columns and the commands are rebuilt from those.
FRAC_RES = {"main": 0.9, "rf95": 0.95, "rf97": 0.97, "rf100": 1.0}
PLAN_SUB = {("main", "solvers"): "solvers", ("main", "agents"): "agents", ("main", "constrained"): "constrained_frac",
            ("bind", "constrained"): "constrained_bind"}
AGENTS_N = 5  # fallback for agents CSVs without an `n` column (see agents_n); the older runs used --n 5
AGENTS_EXTRA = {("new_agents", "cube3"): " --max_nodes 100000"}  # fallback for agents CSVs without a `max_nodes` column
BYCONS = "A* by construction: instances and budgets are derived with A*"  # qualifies every A*-vs-ILP solve count
THIN = 10  # "thin" = fewer trade-off instances than this at every c_slack run
MARK, END = "<!-- INTERPRETATION-7.4 -->", "<!-- /INTERPRETATION-7.4 -->"
DEFAULTS = vars(build_parser().parse_args(["solvers"]))
ORACLE_CAP = inspect.signature(Oracle).parameters["max_nodes"].default
WORKERS = int(re.search(r"num_search_workers = (\d+)", inspect.getsource(ilp)).group(1))
W = SOLVERS["wastar"].keywords["w"]
TOL = inspect.signature(make_instances).parameters["tol"].default
_BOOT = inspect.signature(bootstrap_ci).parameters
BOOT_B, BOOT_SEED = _BOOT["B"].default, _BOOT["seed"].default
MOVES = {"cube2": len(cube2._moves()[0]), "cube3": len(cube3._moves()[0])}


# ---- formatting -------------------------------------------------------------------------------------------------

def f3(x):
    return "n/a" if x != x else f"{x:.3f}"


def f4(x):
    return "n/a" if x != x else f"{x:.4f}"


def ci(lo, hi):
    return f"[{f3(lo)}, {f3(hi)}]"


def rx(x):
    return f"{x:.0f}x" if x >= 10 else f"{x:.2f}x"


def pl(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def counts(c):
    return ", ".join(f"{n} {s}" for s, n in sorted(c.items())) or "none"


def num(n):
    return f"{n:,}"


def and_list(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else "none"


def benches(names):
    return _order(names, BENCH_ORDER)


def bkey(b):
    return (BENCH_ORDER.index(b) if b in BENCH_ORDER else len(BENCH_ORDER), b)


def sec(r):
    return max(float(r["seconds"]), SEC_FLOOR)


def rel(p, base):
    try:
        return Path(os.path.relpath(p, base)).as_posix()
    except ValueError:  # different drive on Windows
        return Path(p).as_posix()


# ---- analysis: unconstrained solvers ----------------------------------------------------------------------------

def mean_ratio(pairs):
    """Ratio of the mean seconds of the second solver to the first over (first, second) row pairs (the statistic the
    README and REPORT quote), next to the median per-row ratio used as the headline."""
    if not pairs:
        return "n/a"
    return rx(sum(sec(x) for _, x in pairs) / sum(sec(a) for a, _ in pairs))


def solver_instances(rows):
    """[{solver: row}] per instance: rows of one instance are consecutive with distinct solvers and the same T*."""
    out, cur = [], {}
    for r in rows:
        if r["solver"] in cur or (cur and next(iter(cur.values()))["T"] != r["T"]):
            out.append(cur)
            cur = {}
        cur[r["solver"]] = r
    return out + ([cur] if cur else [])


def analyse_solvers(found):
    data = [(d, b, rows) for d, b, rows in found["solvers"]]
    allrows = [r for _, _, rows in data for r in rows]
    per, paired, hardest, inst = [], [], [], {}
    for d, b, rows in sorted(data, key=lambda x: (bkey(x[1]), x[0])):
        insts = solver_instances(rows)
        inst[(d, b)] = len(insts)
        for s in _order({r["solver"] for r in rows}, SOLVER_ORDER):
            rs = [r for r in rows if r["solver"] == s]
            ok = [r for r in rs if r["status"] == "ok"]
            per.append({"dataset": d, "bench": b, "solver": s, "instances": len(rs), "solved": len(ok),
                        "failures": counts(Counter(r["status"] for r in rs if r["status"] != "ok")),
                        "max cost/T*": f4(max(float(r["cost_ratio"]) for r in ok)) if ok else "n/a",
                        "median nodes": f"{median(float(r['nodes']) for r in ok):g}" if ok else "n/a",
                        "median seconds": f"{median(float(r['seconds']) for r in ok):.4g}" if ok else "n/a"})
        for x in ("bfs", "wastar", "idastar", "ilp"):
            both = [(i["astar"], i[x]) for i in insts if "astar" in i and x in i
                    and i["astar"]["status"] == "ok" and i[x]["status"] == "ok"]
            xfail = sum(1 for i in insts if "astar" in i and x in i and i["astar"]["status"] == "ok" and i[x]["status"] != "ok")
            if not both and not xfail:
                continue
            t = sorted(sec(xr) / sec(a) for a, xr in both)
            nd = [float(xr["nodes"]) / max(float(a["nodes"]), 1.0) for a, xr in both]
            paired.append({"dataset": d, "bench": b, "X": x, "both ok": len(both),
                           "same cost": sum(round(float(a["cost_ratio"]), 9) == round(float(xr["cost_ratio"]), 9) for a, xr in both),
                           "X failed, A* ok": xfail,
                           "median X/A* seconds": rx(median(t)) if t else "n/a",
                           "range": f"{rx(t[0])} to {rx(t[-1])}" if t else "n/a",
                           "ratio of mean seconds": mean_ratio(both),
                           "X faster": sum(float(xr["seconds"]) < float(a["seconds"]) for a, xr in both),
                           "median X/A* nodes": f"{median(nd):.3g}" if nd else "n/a",
                           "_both": len(both), "_faster": sum(float(xr["seconds"]) < float(a["seconds"]) for a, xr in both),
                           "_med": median(t) if t else math.nan})
        tmax = max(r["T"] for r in rows)
        hardest += [{"dataset": d, **s} for s in summarize([r for r in rows if r["T"] == tmax], ["bench", "T", "solver"],
                                                         ["ok", "cost_ratio", "nodes", "seconds"])]
    ok_exact = [float(r["cost_ratio"]) for r in allrows if r["solver"] in EXACT and r["status"] == "ok"]
    ok_w = [float(r["cost_ratio"]) for r in allrows if r["solver"] == "wastar" and r["status"] == "ok"]
    solved = lambda s: (sum(r["status"] == "ok" for r in allrows if r["solver"] == s), sum(r["solver"] == s for r in allrows))
    return {"data": data, "rows": allrows, "per": per, "paired": paired, "hardest": hardest, "inst": inst,
            "ilp_solved": solved("ilp"), "astar_solved": solved("astar"),
            "status": status_table(allrows, ("bench", "solver")),
            "exact_n": len(ok_exact), "exact_max": max(ok_exact, default=math.nan),
            "w_n": len(ok_w), "w_max": max(ok_w, default=math.nan), "w_longer": sum(x > 1 + 1e-9 for x in ok_w),
            "fails": Counter((r["solver"], r["status"]) for r in allrows if r["status"] != "ok")}


# ---- analysis: constrained, frac --------------------------------------------------------------------------------

def analyse_frac(found):
    out = []
    for d, b, rows in found["constrained"]:
        if is_bind_csv(rows):
            continue
        sk = Counter(r["status"] for r in rows if r["solver"] == "skipped")
        A = [r for r in rows if r["solver"] == "astar"]
        I = [r for r in rows if r["solver"] == "ilp"]
        a_ok = [r for r in A if r["status"] == "ok"]
        i_ok = [r for r in I if r["status"] == "ok"]
        rf = rows[0].get("res_frac") if rows[0].get("res_frac") not in ("", None) else FRAC_RES.get(d, math.nan)
        out.append({"dataset": d, "res_frac": rf, "bench": b, "instances": sum(sk.values()) + len(A),
                    "skipped": counts(sk), "A* ok": f"{len(a_ok)} / {len(A)}",
                    "A* failures": counts(Counter(r["status"] for r in A if r["status"] != "ok")),
                    "ILP ok": f"{len(i_ok)} / {len(I)}",
                    "ILP failures": counts(Counter(r["status"] for r in I if r["status"] != "ok")),
                    "A* cost > T*": sum(float(r["cost"]) > r["T"] for r in a_ok),
                    "ILP agrees with A*": f"{sum(r.get('agrees_with_astar') == 1 for r in I)} / {len(i_ok)}",
                    "_a_ok": len(a_ok), "_longer": sum(float(r["cost"]) > r["T"] for r in a_ok),
                    "_infeasible": sk.get("infeasible", 0)})
    out.sort(key=lambda r: (r["res_frac"], bkey(r["bench"])))
    return out


# ---- analysis: constrained, bind --------------------------------------------------------------------------------

INSTANCE_KEY = ("an instance's position in generation order within its benchmark (every c_slack run of a benchmark uses "
                "the same seed and n, so make_instances yields the same instances in the same order); the key is accepted "
                "only if the T* sequence and every recorded r_opt (which does not depend on c_slack) agree across the runs")


def bind_instances(rows):
    """Instance records of one bind CSV in generation order. A new instance starts at a skipped row or at the A* row of
    level `bind` (an instance's levels are written bind, then tight). Returns ([{T, r_opt, skip}], {id(row): ordinal})."""
    recs, ords = [], {}
    for r in rows:
        if r.get("solver") == "skipped":
            recs.append({"T": r["T"], "r_opt": None, "skip": r["status"]})
        elif r.get("solver") == "astar" and r.get("level") == "bind":
            recs.append({"T": r["T"], "r_opt": r.get("r_opt"), "skip": None})
        if recs:
            ords[id(r)] = len(recs) - 1
    return recs, ords


def same_instances(runs):
    """True when the instance records of the c_slack runs of one benchmark line up (see INSTANCE_KEY)."""
    first = runs[0]
    return all(len(r) == len(first) and all(a["T"] == b["T"] and (a["r_opt"] in ("", None) or b["r_opt"] in ("", None)
                                                                   or a["r_opt"] == b["r_opt"]) for a, b in zip(first, r))
               for r in runs[1:])


def bind_row(bench, c, d, rows):
    pairs, orphans = bind_pairs(rows)
    recs, ords = bind_instances(rows)
    skips = Counter(r["status"] for r in rows if r.get("solver") == "skipped")
    trade = sum(a["level"] == "bind" for a, _ in pairs)
    a_ok = sum(a["status"] == "ok" for a, _ in pairs)
    i_ok = sum(i["status"] == "ok" for _, i in pairs)
    both = [(a, i) for a, i in pairs if a["status"] == "ok" and i["status"] == "ok"]
    t = sorted(sec(i) / sec(a) for a, i in both)
    incr = Counter(int(round(float(a["cost"]) - a["T"])) for a, _ in pairs if a["status"] == "ok")
    fb = sum(float(i["seconds"]) < float(a["seconds"]) for a, i in both)
    ff = sum(float(i["seconds"]) < float(a["seconds"]) for a, i in pairs if i["status"] != "ok")
    return {"bench": bench, "c_slack": c, "dataset": d, "instances": sum(skips.values()) + trade, "trade-off": trade,
            "skips": counts(skips), "rows": len(pairs), "A* ok": f"{a_ok} / {len(pairs)}", "ILP ok": f"{i_ok} / {len(pairs)}",
            "ILP failures": counts(Counter(i["status"] for _, i in pairs if i["status"] != "ok")),
            "both ok": len(both), "same cost": sum(float(a["cost"]) == float(i["cost"]) for a, i in both),
            "median ILP/A* time": rx(median(t)) if t else "n/a", "range": f"{rx(t[0])} to {rx(t[-1])}" if t else "n/a",
            "ratio of mean seconds": mean_ratio(both),
            "ILP faster (both ok)": fb, "ILP faster (ILP failed)": ff,
            "cost - T* (A* ok rows)": ", ".join(f"+{k}: {v}" for k, v in sorted(incr.items())) or "none",
            "_nodes": {sv: mean(float(r["nodes"]) for r in rows if r.get("solver") == sv and r.get("level") == "bind"
                              and r.get("nodes") not in ("", None))
                       for sv in ("astar", "ilp") if any(r.get("solver") == sv and r.get("level") == "bind"
                                                         and r.get("nodes") not in ("", None) for r in rows)},
            "_orphans": orphans, "_i_ok": i_ok, "_a_ok": a_ok, "_rows": len(pairs), "_med": median(t) if t else math.nan,
            "_recs": recs, "_both_ords": {ords[id(a)] for a, _ in both},
            "_trade_ords": {i for i, r in enumerate(recs) if r["skip"] is None},
            "_ifail": Counter(i["status"] for _, i in pairs if i["status"] != "ok"), "_skips": skips,
            "_max_nodes": sorted({r["max_nodes"] for r in rows if r.get("max_nodes") not in ("", None)})}


def analyse_bind(found):
    """(rows per (bench, c_slack), distinct-instance totals). The c_slack runs of one benchmark re-use the same instances,
    so totals over rows count (instance, level, c_slack) rows; `distinct` counts each instance once (INSTANCE_KEY).
    A benchmark whose runs do not line up is counted per run and listed in `unverified`."""
    bb = bind_by_bench(found)
    rows = [bind_row(b, c, *bb[b][c]) for b in benches(bb) for c in sorted(bb[b])]
    dist = Counter()
    unverified = []
    for b in benches(bb):
        rs = [r for r in rows if r["bench"] == b]
        if same_instances([r["_recs"] for r in rs]):
            dist["instances"] += len(rs[0]["_recs"])
            for k, key in (("trade", "_trade_ords"), ("both", "_both_ords")):
                dist[k] += len(set().union(*(r[key] for r in rs)))
            dist["no_trade_all"] += sum(all(r["_recs"][i]["skip"] == "no_tradeoff" for r in rs) for i in range(len(rs[0]["_recs"])))
            dist["no_trade_any"] += sum(any(r["_recs"][i]["skip"] == "no_tradeoff" for r in rs) for i in range(len(rs[0]["_recs"])))
        else:
            unverified.append(b)
            for r in rs:
                dist["instances"] += len(r["_recs"])
                dist["trade"] += len(r["_trade_ords"])
                dist["both"] += len(r["_both_ords"])
                n = sum(x["skip"] == "no_tradeoff" for x in r["_recs"])
                dist["no_trade_all"] += n
                dist["no_trade_any"] += n
    return rows, {**{k: dist[k] for k in ("instances", "trade", "both", "no_trade_all", "no_trade_any")},
                  "unverified": unverified}


# ---- analysis: agents -------------------------------------------------------------------------------------------

def analyse_agents(found):
    out = []
    for d, b, rows in sorted(found["agents"], key=lambda x: (x[0] != "main", x[0], bkey(x[1]))):
        used = agent_instance_rows(rows)[0]
        if not used:
            continue
        methods = _order({r["method"] for r in used}, METHODS)
        pooled = [{"method": m, **pool_success([r for r in used if r["method"] == m])} for m in methods]
        ts = sorted({r["T"] for r in used})
        buckets = {(m, t): pool_success(rs) for m in methods for t in ts
                   if (rs := [r for r in used if r["method"] == m and r["T"] == t])}
        paired, notes = paired_differences(used)
        succ = defaultdict(dict)
        for r in used:
            succ[r["method"]][r["inst"]] = r["k"] / r["ep"]
        a, tp = succ.get("ours_astar", {}), succ.get("tape", {})
        common = sorted(set(a) & set(tp))
        per_bucket = Counter((r["T"], r["method"]) for r in used)
        out.append({"dataset": d, "bench": b, "used": used, "methods": methods, "pooled": pooled, "buckets": buckets,
                    "ts": ts, "paired": paired, "notes": notes, "ilp": "ours_ilp" in methods,
                    "episodes": sorted({r["ep"] for r in used}), "instances": len({r["inst"] for r in used}),
                    "same": sum(a[i] == tp[i] for i in common), "tape_hi": sum(tp[i] > a[i] for i in common),
                    "tape_lo": sum(tp[i] < a[i] for i in common), "common": len(common),
                    "bucket_sizes": (min(per_bucket.values()), max(per_bucket.values())),
                    "looked_up": any(r["looked_up"] for r in used)})
    return pick_agents(out)


def pick_agents(datasets):
    """One agents dataset per benchmark: the one with the most episodes per instance (ties: a non-main directory, then
    by name). The others are superseded and left out of every table and aggregate: a later run on the same benchmark
    (e.g. agents_ep300 with seed 1 and --n 5) re-uses the same instances and per-instance seeds, so its first episodes
    repeat the earlier run's. Returns (kept, [(superseded, kept_instead)])."""
    best = best_agents(datasets)
    kept = sorted((a for a in datasets if best[a["bench"]] is a), key=lambda a: bkey(a["bench"]))
    return kept, [(a, best[a["bench"]]) for a in datasets if best[a["bench"]] is not a]


# ---- commands behind each dataset -------------------------------------------------------------------------------

def _opt(r0, *keys):
    return "".join(f" --{k} {r0[k]}" for k in keys if r0.get(k) not in ("", None) and r0[k] != DEFAULTS[k])


def _plan_cmd(sub, bench):
    for st in plan("full"):
        if st.sub == sub and "--bench" in st.args and st.args[st.args.index("--bench") + 1] == bench:
            return " ".join(st.args)
    return None


def agents_n(r0, rows):
    """--n of an agents run: the `n` column (CSVs written since it was added); else inferred as distinct instances per T*
    bucket when every bucket holds the same count; else the AGENTS_N fallback (older CSVs carry no n)."""
    if r0.get("n") not in ("", None):
        return r0["n"]
    per_t = Counter()
    for i in {(r["T"], r["inst"]) for r in agent_instance_rows(rows)[0]}:
        per_t[i[0]] += 1
    return next(iter(per_t.values())) if per_t and len(set(per_t.values())) == 1 else AGENTS_N


def command(kind, d, bench, rows):
    """The bench CLI command behind one dataset CSV: the published command (bench.plan('full')) for the CSVs that
    predate the parameter columns, otherwise rebuilt from the parameter columns. None when neither is available."""
    r0 = rows[0]
    cmd = None
    if (d, kind) in PLAN_SUB:
        cmd = _plan_cmd(PLAN_SUB[(d, kind)], bench)
    elif kind == "solvers" and r0.get("n") not in ("", None):
        cmd = f"solvers --bench {bench} --n {r0['n']}" + _opt(r0, "max_nodes", "seed", "slack", "time_limit")
    elif kind == "constrained" and is_bind_csv(rows) and all(r0.get(k) not in ("", None) for k in ("c_slack", "n")):
        cmd = (f"constrained --design bind --c_slack {r0['c_slack']} --bench {bench} --n {r0['n']}"
               + _opt(r0, "max_nodes", "seed", "time_limit"))
    elif kind == "constrained" and not is_bind_csv(rows) and d in FRAC_RES:
        base = _plan_cmd("constrained_frac", bench)
        cmd = base and f"{base} --res_frac {FRAC_RES[d]}"
    elif kind == "agents" and r0.get("episodes") not in ("", None):
        cmd = (f"agents --bench {bench} --n {agents_n(r0, rows)} --episodes {r0['episodes']}"
               + (" --no_ilp" if r0.get("use_ilp") == 0 else "") + _opt(r0, "delta", "eta", "slack", "N", "seed", "max_nodes")
               + ("" if r0.get("max_nodes") not in ("", None) else AGENTS_EXTRA.get((d, bench), "")))
    return f"python -m tapegraph.bench {cmd}" if cmd else None


# ---- rendering helpers ------------------------------------------------------------------------------------------

def table(rows):
    return _md([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])


class Figs:
    def __init__(self, figures_dir, paper_dir):
        self.dir, self.base = Path(figures_dir), paper_dir

    def link(self, name, caption):
        p = self.dir / name
        if not p.is_file():
            return ""
        return f"![{caption}]({rel(p, self.base)})\n"

    def available(self):
        return sorted(p.name for p in self.dir.glob("*.svg"))


# ---- the paper --------------------------------------------------------------------------------------------------

def build_paper(data_dir=ROOT / "docs" / "data", figures_dir=ROOT / "docs" / "figures", paper_dir=ROOT / "docs",
                interpretation=""):
    """Markdown text of the paper. Links are relative to `paper_dir` (where the file will live)."""
    found = load(data_dir)
    S, F = analyse_solvers(found), analyse_frac(found)
    B, BD = analyse_bind(found)
    A, SUP = analyse_agents(found)
    figs = Figs(figures_dir, paper_dir)
    dref = rel(data_dir, ROOT)
    out = []
    w = out.append

    all_benches = benches({b for k in found for _, b, _ in found[k]})
    solver_benches = benches({b for _, b, _ in S["data"]})
    n_inst = sum(S["inst"].values())
    ilp_pairs = [p for p in S["paired"] if p["X"] == "ilp"]
    ilp_both, ilp_faster = sum(p["_both"] for p in ilp_pairs), sum(p["_faster"] for p in ilp_pairs)
    b_both = sum(r["both ok"] for r in B)
    b_same = sum(r["same cost"] for r in B)
    b_fast = sum(r["ILP faster (both ok)"] for r in B)
    b_fastfail = sum(r["ILP faster (ILP failed)"] for r in B)
    b_meds = [r["_med"] for r in B if r["_med"] == r["_med"]]
    b_cs = sorted({r["c_slack"] for r in B})
    b_benches = benches({r["bench"] for r in B})
    react_d = [p["mean_diff"] for a in A for p in a["paired"] if p["comparison"] == "ours_astar - react"]
    tape_p = [(a, p) for a in A for p in a["paired"] if p["comparison"] == "ours_astar - tape"]
    tape_d = [p["mean_diff"] for _, p in tape_p]
    tape_zero = sum(p["ci_lo"] <= 0 <= p["ci_hi"] for _, p in tape_p)
    tape_ahead = [p["mean_diff"] for _, p in tape_p if p["ci_lo"] > 0]  # interval excludes 0, ours_astar higher
    tape_behind = [p["mean_diff"] for _, p in tape_p if p["ci_hi"] < 0]
    tape_excl = (f"; it excludes 0 with ours_astar higher on {len(tape_ahead)}"
                 + (f" (by at most {f3(max(tape_ahead))})" if tape_ahead else "")
                 + f" and with ours_astar lower on {len(tape_behind)}"
                 + (f" (by at most {f3(-min(tape_behind))})" if tape_behind else "")) if tape_p else ""
    exact_text = ("every solved path had length exactly T*" if S["exact_max"] == 1.0
                  else f"the largest cost/T* was {f4(S['exact_max'])}")
    full_grid = all(sum(r["bench"] == b for r in B) == len(b_cs) for b in b_benches)
    cs_text = f"c_slack {and_list(map(str, b_cs))}" + ("" if full_grid else ", not every value on every benchmark")
    a_fail = sum(n for (s, _), n in S["fails"].items() if s == "astar")
    b_rows, b_iok, b_aok = sum(r["_rows"] for r in B), sum(r["_i_ok"] for r in B), sum(r["_a_ok"] for r in B)
    distinct_note = (f"{BD['both']} distinct instances" if not BD["unverified"]
                     else f"{BD['both']} instances, counted per run on {and_list(BD['unverified'])}")
    (iok, iall), (aok_u, aall_u) = S["ilp_solved"], S["astar_solved"]
    unc_text = (f"the ILP solved {iok} of {iall} unconstrained instances (A* {aok_u} of {aall_u}; {BYCONS}) and was faster than A* on "
                f"{ilp_faster} of the {ilp_both} where both solved")
    bind_text = (f"the ILP solved {b_iok} of {b_rows} (instance, level, c_slack) rows (A* {b_aok} of {b_rows}; {BYCONS}); on the "
                 f"{b_both} rows where both solved ({distinct_note}; the c_slack runs of a benchmark re-use the same "
                 f"instances) it returned the same cost as A* on {b_same} and was faster on {b_fast}")
    n_agent_benches = len({a["bench"] for a in A})
    fastfail_text = (f"On {b_fastfail} (instance, level, c_slack) rows the ILP returned before A* but with a failure "
                     "status; a fast failure is not a win. " if b_fastfail else "")

    # ---- title and abstract
    w("# TAPE without the language model: plan, execute and re-plan on exact state graphs\n")
    w("_Generated by `python scripts/make_paper.py` from the CSVs under "
      f"`{dref}/`; every table and every number in a generated sentence is computed from those files. "
      "Do not edit by hand: change the script or the data and regenerate._\n")
    w("## Abstract\n")
    ab = ("TAPE (Jeong, Kim, Lee 2026) lets a language model propose plans, folds them into a graph, picks a path with an "
          "integer program and re-plans when execution deviates. We remove the language model and study what remains: a "
          "plan-execute-replan loop over an implicit state graph whose plan comes from a graph search solver (BFS, A*, "
          "weighted A*, IDA*) or from a CP-SAT edge-flow ILP. ")
    if S["data"]:
        ab += (f"On {len(solver_benches)} generated benchmarks with unconstrained solver data ({n_inst} instances), "
               f"for BFS, A*, IDA* and the ILP {exact_text} ({num(S['exact_n'])} solved rows), and {unc_text}. ")
    if B:
        ab += (f"In a resource-constrained design whose budget always rules out every length-optimal path "
               f"({pl(len(b_benches), 'benchmark')}; {cs_text}), {bind_text}"
               + (f" (median ILP/A* time ratio per benchmark and c_slack from {rx(min(b_meds))} to {rx(max(b_meds))})" if b_meds else "")
               + f". {fastfail_text}")
    if react_d:
        ab += (f"Under the TAPE paper's noise model, re-planning with A* on the true graph "
               f"{'exceeds' if min(react_d) > 0 else 'differs from'} a simulated ReAct by "
               f"{f3(min(react_d))} to {f3(max(react_d))} in mean per-instance success across {pl(n_agent_benches, 'benchmark')}"
               + (f", and differs from a simulated TAPE by {f3(min(tape_d))} to {f3(max(tape_d))}; the bootstrap interval of "
                  f"that difference contains 0 on {tape_zero} of {pl(len(tape_d), 'benchmark')}{tape_excl}" if tape_d else "")
               + ". ")
    ab += ("ReAct and TAPE are simulated with the paper's noise model; no language model was run.")
    w(ab + "\n")

    # ---- 1 introduction
    w("## 1 Introduction\n")
    w("TAPE (Jeong, Kim, Lee 2026) argues that a language-model agent that commits to one action at a time (ReAct; Yao "
      "et al. 2022) accumulates planning errors it never revisits over long horizons. TAPE addresses this by "
      "sampling several plans from the model, merging them into a graph, choosing a feasible path with an integer program "
      "and executing it under constraints, re-planning when the environment deviates. The part of TAPE that is not about "
      "language models is a planning loop over a graph. This report isolates that loop.\n")
    w("We replace the language model by benchmarks whose goal is fixed and whose start is random, so states and their "
      "merging are exact, and we replace the single ILP by a family of graph solvers that share one interface, each with "
      "the graph constraints that suit it. We then ask three questions: (i) do the solvers return optimal plans and at "
      "what cost; (ii) does the ILP, TAPE's solver, have an advantage when a side-resource budget forces a longer path; "
      "(iii) how does the loop compare with ReAct and TAPE under the TAPE paper's noise model. The baselines in (iii) are "
      "simulations of LLM behaviour, not LLM runs, and are labelled as such everywhere.\n")
    w("Contributions: an LLM-free statement of the TAPE loop with a pluggable solver; "
      f"{len(all_benches)} generated benchmarks with a true optimal length T* for every instance "
      f"({and_list(f'`{b}`' for b in all_benches)}); a constrained experiment designed so the resource budget always binds; "
      "and a fully generated write-up whose tables are recomputed from committed CSVs.\n")

    # ---- 2 algorithm
    w("## 2 The algorithm\n")
    w("Problem: given an implicit state graph G (successor function, unit edge costs), a start s0, a goal test and a budget "
      "B, reach a goal within B steps, preferring a minimum-cost path that also respects an optional side-resource budget "
      "R. The loop below (`tapegraph/baselines/replan.py`, class `Replan`) is the whole algorithm; `execute` is the "
      "environment and may return a different state than planned (execution noise).\n")
    w("```text\n"
      "procedure REPLAN(P, s0, B, solve)\n"
      "    s <- s0; plan <- empty; expected <- none\n"
      "    for t = 0 .. B-1:\n"
      "        if P.is_goal(s): return success\n"
      "        if plan is empty or s != expected:            # first step, plan used up, or deviation\n"
      "            r <- solve(P, s, budget = B - t)          # one solve on the true graph\n"
      "            plan <- r.path if r.status = ok else empty  # non-ok solves are counted (solver_fail)\n"
      "        if plan is empty: a <- first legal action of s\n"
      "        else: (a, expected) <- pop front of plan\n"
      "        s <- execute(s, a)                            # may deviate from expected\n"
      "    return P.is_goal(s)\n"
      "```\n")
    w("How TAPE maps onto it:\n")
    w(_md([
        {"TAPE step": "LLM proposes N candidate plans", "here": "none: the solver reads the true successor function (the simulated TAPE baseline keeps N noisy rollouts)"},
        {"TAPE step": "merge the plans into a graph (state abstraction)", "here": "states are exact and hashable, so merging is identity; the ILP builds an explicit bounded subgraph"},
        {"TAPE step": "ILP selects a path under budgets", "here": "`solve` is any of BFS, A*, weighted A*, IDA* or the CP-SAT ILP"},
        {"TAPE step": "constrained execution", "here": "execute the next planned action; illegal actions leave the state unchanged"},
        {"TAPE step": "re-plan on deviation", "here": "re-solve from the observed state whenever it differs from the expected one"},
    ]))
    w("\nSolver interface. Every solver is a function `solve(problem, start, budget, res_budget=None, max_nodes=...) -> "
      "Result(status, path, states, cost, res, nodes, seconds)` with status `ok`, `no_path`, `node_limit`, `too_large` "
      "or `timeout`; a solver depends only on the `Problem` interface of Section 4.1.\n")

    # ---- 3 related work
    w("## 3 Related work\n")
    w("ReAct (Yao et al. 2022) interleaves reasoning and acting: the model chooses one action at a time from its "
      "observations. TAPE (Jeong, Kim, Lee 2026) aggregates several model-proposed plans into a graph, selects a path with "
      "an integer program and constrains execution to it, re-planning on deviation; its noise model (a planning-error rate "
      "and an execution-noise rate) is the one our simulated baselines use. A* (Hart, Nilsson, Raphael 1968) is "
      "best-first search with an admissible heuristic and returns optimal paths; IDA* (Korf 1985) is its depth-first, "
      "iterative-deepening counterpart with memory linear in depth. Pattern databases for the Rubik's cube (Korf 1997) "
      "are the source of the cube heuristics used here. Sokoban is PSPACE-complete (Culberson 1997), which is why "
      "instances are generated by reverse play with a verified optimal length rather than taken at random. Boxoban "
      "(Guez et al. 2019) is a large set of 10x10 four-box Sokoban levels; our Boxoban-style benchmark imitates its format "
      "with locally generated levels. The ILP is solved with the CP-SAT solver of Google OR-Tools.\n")

    # ---- 4 method
    w("## 4 Method\n")
    w("### 4.1 Problem interface\n")
    w(_md([
        {"method": "`neighbors(s)`", "meaning": "yields `(action, next_state, cost)`; all costs are 1"},
        {"method": "`is_goal(s)`", "meaning": "goal test"},
        {"method": "`h(s)`", "meaning": "admissible lower bound on the remaining cost"},
        {"method": "`prune(s)`", "meaning": "`True` only for a provable dead end"},
        {"method": "`random_start(rng, depth)`", "meaning": "a start from which the goal is reachable"},
        {"method": "`res(s, a, s2)`, `res_bind(s, a, s2)`", "meaning": "side resource of an edge for the `frac` and `bind` constrained designs"},
        {"method": "`exact_dist(s)` (optional)", "meaning": "exact distance table (River, Rubik's 2x2x2)"},
    ]))
    w("\n### 4.2 Solvers and their graph constraints\n")
    w(_md([
        {"solver": "BFS", "graph": "implicit", "constraints": "none; ignores `h` and `prune` on purpose, so it is the independent reference"},
        {"solver": "A*", "graph": "implicit", "constraints": "prune dead ends; drop nodes with g + h > budget; with a resource budget, label-setting over (state, g, resource) with dominance (stays exact)"},
        {"solver": f"weighted A* (w = {W:g})", "graph": "implicit", "constraints": f"as A* with f = g + {W:g} h; not guaranteed optimal, reported as cost/T*"},
        {"solver": "IDA*", "graph": "implicit", "constraints": "depth-bounded DFS with a per-iteration transposition table"},
        {"solver": "CP-SAT ILP", "graph": "explicit ball {g + h <= budget}, built by BFS, capped at `max_nodes` (`too_large` beyond)",
         "constraints": f"edge-flow model below; length and optional resource budget; {DEFAULTS['time_limit']:g} s solver limit; {WORKERS} workers"},
    ]))
    w("\n### 4.3 Edge-flow ILP\n")
    w("On the explicit subgraph with edges e = (u, v), cost c_e and resource r_e, one binary x_e per edge and one binary "
      "z_g per goal node g:\n")
    w("```text\n"
      "minimise    sum_e c_e x_e\n"
      "subject to  sum_g z_g = 1\n"
      "            out(n) - in(n) = [n = s] - z_n           for every node n (z_n = 0 for non-goals)\n"
      "            sum_e c_e x_e <= B                       (length budget)\n"
      "            sum_e r_e x_e <= R                       (resource budget, when given)\n"
      "```\n")
    w("Costs are positive, so an optimal solution is a simple path. TAPE uses a time-expanded model, which is needed only "
      "for node-score objectives; this project minimises path length, so the edge-flow model is the smaller equivalent. "
      "The ILP's result counts as `ok` only when CP-SAT proves optimality (or `no_path` when it proves infeasibility); "
      "every other outcome is reported as `timeout`: CP-SAT stopping at the time limit with a non-optimal or no solution, "
      "any other non-OPTIMAL solver status, or a path reconstruction that breaks or cycles. Graph construction and model building count toward the ILP's measured time.\n")
    w("### 4.4 Simulated baselines and the noise model\n")
    w(f"All agents run on the same instances with paired noise (one seed per instance, shared by every method). The "
      f"budget is B = T* + slack with slack {DEFAULTS['slack']}. Planning error rate delta = {DEFAULTS['delta']:g} and "
      f"execution noise eta = {DEFAULTS['eta']:g} (the TAPE paper's values; CLI defaults):\n")
    w(f"- **react (simulated)**: each step takes an exact oracle's next action; with probability delta it is replaced by "
      "an action that breaks the budget if one exists. No recovery.\n"
      f"- **tape (simulated)**: {DEFAULTS['N']} rollouts with the same planning error are folded into a graph; a shortest path "
      "in the folded graph (the CP-SAT ILP, or BFS on the folded graph when the ILP is disabled) is followed, and the "
      "agent re-plans on deviation.\n"
      "- **ours_astar / ours_ilp**: the REPLAN loop of Section 2 with A* or the ILP as `solve`.\n"
      "- Execution noise applies to every method: with probability eta the executed action is a different legal action.\n")
    w(f"The oracle behind both simulations is exact (distance tables, or A* with a {num(ORACLE_CAP)}-node cap). A hypothesis "
      "for why tape (simulated) and ours_astar are close is given in Section 8.\n")
    w("### 4.5 Instances, budgets and metrics\n")
    w(f"Instances are generated per target T* (accepted within {TOL} step{'s' if TOL != 1 else ''} of the target and reported under their true T*, "
      "verified by an exact table or the oracle); River and the cubes draw a start at an exact or scrambled depth, the "
      "Sokoban family by reverse play from a solved layout. The unconstrained budget is T* + slack; the node cap is "
      f"`--max_nodes` (default {num(DEFAULTS['max_nodes'])}). Metrics: success within budget under noise; cost/T*; nodes "
      "expanded (for the ILP: size of the explicit subgraph, so not comparable with the search solvers); wall-clock "
      "seconds; for the constrained runs status counts, cost agreement with A* and the ILP/A* time ratio. Failures are "
      "rows, never dropped; cost statistics are over solved rows only. Success intervals are 95% Wilson intervals; paired "
      f"differences use a 95% percentile bootstrap over instances (B = {BOOT_B}, seed {BOOT_SEED}).\n")

    # ---- 5 benchmarks
    w("## 5 Benchmarks\n")
    size = {}
    for b in ("sokoban", "sokoban2", "sokoban3", "boxoban"):
        p = BENCHMARKS[b].make(random.Random(0))
        size[b] = f"{p.H}x{p.W} grid, {len(p.goals)} box{'es' if len(p.goals) > 1 else ''}"
    rv = _river()
    size["river"] = f"{rv.n} missionaries, {rv.n} cannibals, boat capacity {rv.cap}"
    size["cube2"] = f"{math.factorial(7):,} x {3 ** 6:,} = {math.factorial(7) * 3 ** 6:,} states, {MOVES['cube2']} half-turn-metric moves"
    size["cube3"] = f"{MOVES['cube3']} half-turn-metric moves"
    desc = {
        "river": ("(missionaries left, cannibals left, boat side)", "trip-count lower bound", "none", "exact distance table"),
        "sokoban": ("player + sorted boxes", "sum over boxes of Manhattan distance to the nearest goal", "static dead cells", "reverse play"),
        "boxoban": ("player + sorted boxes", "as Sokoban", "static dead cells", "reverse play (generated locally)"),
        "cube2": ("(corner permutation, corner twist)", "max of two pattern databases (permutation, twist)", "none", "uniform state at exact depth"),
        "cube3": ("corner coordinate + three edge-quad coordinates", f"corner pattern database ({math.factorial(8) * 3 ** 7:,} entries)", "none", "random walk without same-axis repeats"),
    }
    desc["sokoban2"] = desc["sokoban3"] = desc["sokoban"]
    rows = []
    for b in benches(BENCHMARKS):
        if b not in desc:
            continue
        bn = BENCHMARKS[b]
        n = sum(v for (d, bb), v in S["inst"].items() if bb == b)
        ts = sorted({r["T"] for d, bb, rs in S["data"] if bb == b for r in rs})
        st, h, pr, gen = desc[b]
        rows.append({"benchmark": f"`{b}`", "size": size[b], "state": st, "heuristic": h, "dead-end prune": pr,
                     "start": gen + ("" if bn.exact else f", depth {bn.depth[0]} to {bn.depth[1]}"),
                     "T* targets": ", ".join(map(str, bn.T_targets)), "solver instances": n or "none",
                     "observed T*": f"{ts[0]} to {ts[-1]}" if ts else "n/a"})
    w(_md(rows))
    w("\nThe 2x2x2 cube's distance table is one vectorised BFS over the product of its two independent coordinates; the "
      "3x3x3 corner pattern database is built the same way (chunked) and cached under `.cache/`. Resources for the "
      "`bind` design (Section 7.3): pushes only (Sokoban family, Boxoban), passengers squared (River), half-turns only "
      "(cubes).\n")
    w("Real Boxoban levels: `load_boxoban_file` reads a user-supplied file in DeepMind's text format (`--bench boxoban_file "
      "--boxoban_file PATH`; levels the oracle cannot solve are kept as `skipped` rows). Nothing is downloaded, and **no "
      "results on real Boxoban levels exist in this repository**; every table uses generated instances.\n")

    # ---- 6 experiments
    w("## 6 Experiments\n")
    w(f"All runs: seed {DEFAULTS['seed']} unless a command says otherwise, one dataset per `--out` directory, copied to "
      f"`{dref}/<dataset>/<kind>_<bench>.csv`. Commands for the CSVs that predate the parameter columns are the published "
      "ones (`tapegraph all --profile full`, README); for newer CSVs they are rebuilt from the parameter columns of the "
      "CSV itself. Generated summary tables per dataset are in "
      + ", ".join(f"[`{p.name}`]({rel(p, paper_dir)})" for p in sorted(Path(paper_dir).glob("results*.md")))
      + ".\n")
    w("Provenance of the agents commands: agents CSVs written since the `n` and `max_nodes` columns were added carry "
      "both. For older agents CSVs `--n` is inferred as the number of distinct instances per T* bucket when every bucket "
      f"holds the same count, and otherwise the recorded fallback `--n {AGENTS_N}` is used; `--max_nodes` for an older "
      "CSV comes from a hand-typed record ("
      + (", ".join(f"`{d}/{b}`:{x}" for (d, b), x in AGENTS_EXTRA.items()) or "none")
      + "). The commands of such files are therefore reconstructions, not recorded values.\n")
    w("The `bind` c_slack sweep (2 and 8) uses the same `--n` per benchmark as the c_slack 4 runs. This is a deliberate "
      "choice, not a limit: the runs then share the same instances, so rows pair across c_slack; a larger `--n` for the "
      "sweep was not run.\n")
    rows = []
    for kind in ("solvers", "constrained", "agents"):
        for d, b, rs in sorted(found[kind], key=lambda x: (x[0], bkey(x[1]))):
            rows.append({"dataset": f"`{d}`", "kind": kind if kind != "constrained" else ("constrained bind" if is_bind_csv(rs) else "constrained frac"),
                         "bench": f"`{b}`", "rows": len(rs), "command": f"`{command(kind, d, b, rs) or 'not recorded'}`"})
    w(_md(rows))
    have = {(d, b) for d, b, _ in found["agents"]}
    missing = [k for k in PENDING if k not in have]
    if missing:
        w("\nAgents files not yet available are listed in Section 7.4.\n")

    # ---- 7 results
    w("\n## 7 Results\n")
    w("### 7.1 Unconstrained solvers\n")
    if not S["data"]:
        w("_No solvers data._\n")
    else:
        w(f"Budget T* + slack, node cap as in the command. Per benchmark and solver; medians over solved rows; failures "
          f"are counted, not dropped.\n")
        w(table(S["per"]))
        w("\nLargest T* bucket of each benchmark (means as in the generated `results*.md` tables: cost/T* over solved rows; "
          "nodes and seconds over all rows of the bucket, failed rows included):\n")
        w(table(S["hardest"]))
        w("\nFailure counts (rows per status, all solvers datasets):\n")
        w(table(S["status"]))
        w(f"\nPaired comparison against A* on the same instance (rows where both solved; time ratio X/A* with seconds "
          f"clamped below at {SEC_FLOOR:g} s, the CSV resolution):\n")
        w(table(S["paired"]))
        w(f"\n- BFS, A*, IDA* and the ILP: over {num(S['exact_n'])} solved rows, {exact_text}.\n"
          f"- Weighted A* returned a longer path than T* on {S['w_longer']} of {num(S['w_n'])} solved rows "
          f"(largest cost/T* {f4(S['w_max'])}).\n"
          f"- Solve counts: {unc_text}"
          + (f"; per benchmark its median time ratio ranged from {rx(min(p['_med'] for p in ilp_pairs))} to "
             f"{rx(max(p['_med'] for p in ilp_pairs))}" if ilp_pairs else "") + ".\n"
          + "".join(f"- {s} non-ok rows: {counts(Counter({st: n for (s2, st), n in S['fails'].items() if s2 == s}))}.\n"
                    for s in _order({s for s, _ in S["fails"]}, SOLVER_ORDER)))
        suf = _suffixes(found["solvers"])
        for d, b, _ in sorted(S["data"], key=lambda x: (bkey(x[1]), x[0])):
            for m in ("nodes", "seconds"):
                w(figs.link(f"solvers_{m}_{b}{suf[(d, b)]}.svg", f"{b}: solver {m} vs T*"))
        il = [(b, f"ilp_rate_{b}{suf[(d, b)]}.svg") for d, b, _ in sorted(S["data"], key=lambda x: (bkey(x[1]), x[0]))]
        il = [(b, n) for b, n in il if (Path(figures_dir) / n).is_file()]
        if il:
            w("\nILP solve rate by T* (95% Wilson): "
              + ", ".join(f"[{b}]({rel(Path(figures_dir) / n, paper_dir)})" for b, n in il) + ".\n")

    w("\n### 7.2 Constrained, first design (`frac`)\n")
    if not F:
        w("_No `frac` data._\n")
    else:
        w("Length budget T* + slack and resource budget R = floor(res_frac x resource of the unconstrained optimum), with "
          "the original resources (Sokoban family: 3 per push and 1 per move; River: passengers carried; cube: half-turn 2, "
          "quarter-turn 1). `skipped` rows are instances where A* proved the budget infeasible (or could not derive R).\n")
        w(table(F))
        a_main = [r for r in F if r["res_frac"] < 1]
        lg, aok = sum(r["_longer"] for r in a_main), sum(r["_a_ok"] for r in a_main)
        inf, ninst = sum(r["_infeasible"] for r in a_main), sum(r["instances"] for r in a_main)
        rare = aok and lg / aok < 0.25 and ninst and inf / ninst > 0.5
        w(f"\nAcross the runs with res_frac below 1 ({ninst} instance-runs), {inf} were infeasible at the resource budget "
          f"and {lg} of the {aok} solved A* rows had cost above T*"
          + (": this design is mostly infeasible and rarely forces a longer path, so the `bind` design replaces it. "
             "A likely reason (an argument, not a measurement): with these resources a cheaper path within the length "
             "slack needs fewer pushes on the Sokoban family, which almost never exists.\n" if rare else ".\n"))

    w("### 7.3 Constrained, binding design (`bind`)\n")
    w("Design. For each instance, r_opt is the least resource among paths of length <= T* and r_min the least resource "
      "among paths of length <= T* + c_slack (both by bisection over resource-constrained A*). If r_min >= r_opt the "
      "instance has no trade-off and is skipped (`no_tradeoff`). Otherwise level `bind` uses R = r_opt - 1, so every "
      "length-optimal path is infeasible, and level `tight` uses R = r_min when r_min < r_opt - 1. A* and the ILP both run "
      "at (T* + c_slack, R). A row is an (instance, level) pair. Resources: pushes only (Sokoban family, Boxoban), "
      "passengers squared (River), half-turns only (cubes); they were chosen because they create trade-offs.\n")
    if not B:
        w("_No `bind` data._\n")
    else:
        w(f"Time ratio per row = ILP seconds / A* seconds on rows where both solved (seconds clamped below at "
          f"{SEC_FLOOR:g} s). The headline is the median of the per-row ratios; \"ratio of mean seconds\" (mean ILP "
          "seconds / mean A* seconds over the same rows) is the statistic quoted in the README and REPORT. It is pulled "
          "toward the slowest rows, so the two differ wherever the per-row ratios are skewed. \"ILP faster (ILP failed)\" "
          "counts rows where the ILP returned sooner than A* but with a failure status. Rows count (instance, level) "
          "pairs within one c_slack run; the c_slack runs of a benchmark re-use the same instances.\n")
        w(table(B))
        multi = [b for b in b_benches if sum(r["bench"] == b for r in B) > 1]
        if multi:
            w("\nThe c_slack sweep (benchmarks run at more than one c_slack): ILP ok / rows, trade-off instances, and "
              "median ILP/A* time ratio on rows where both solved.\n")
            sw = []
            for b in multi:
                rs = {r["c_slack"]: r for r in B if r["bench"] == b}
                row = {"bench": f"`{b}`"}
                for c in b_cs:
                    r = rs.get(c)
                    row[f"c_slack {c}"] = (f"ILP {r['_i_ok']}/{r['_rows']}, {r['trade-off']} inst., {r['median ILP/A* time']}"
                                           if r else "not run")
                sw.append(row)
            w(_md(sw))
            nd = []
            for b in multi:
                rs = {r["c_slack"]: r["_nodes"] for r in B if r["bench"] == b}
                cs = [c for c in b_cs if c in rs and {"astar", "ilp"} <= set(rs[c])]
                if len(cs) > 1:
                    same = len({round(rs[c]["astar"], 6) for c in cs}) == 1
                    nd.append(f"`{b}` (c_slack {' / '.join(map(str, cs))}) A* " + (f"{rs[cs[0]]['astar']:,.1f} at every c_slack" if same
                                              else " / ".join(f"{rs[c]['astar']:,.1f}" for c in cs))
                              + " and ILP " + " / ".join(f"{rs[c]['ilp']:,.1f}" for c in cs)
                              + ("" if same else " (the A* means differ because the set of trade-off instances differs between "
                                 "runs: " + " / ".join(str(next(r["trade-off"] for r in B if r["bench"] == b and r["c_slack"] == c))
                                                       for c in cs) + " instances)"))
            if nd:
                w("\nWhat the sweep measures. At level `bind` the resource budget R = r_opt - 1 and the constrained optimum do "
                  "not depend on c_slack (r_opt is defined at length T*), so A* has the same search problem on every instance in every run, "
                  "while the ILP's graph is the ball of states within T* + c_slack steps and grows with c_slack. Mean nodes "
                  "over the `bind`-level rows (including rows where a solver failed): "
                  + "; ".join(nd) + ". The sweep therefore mostly shows how the "
                  "edge-flow ILP scales with a slack length budget; it is not a harder trade-off for A*.\n")
        fails = Counter()
        for r in B:
            fails.update(r["_ifail"])
        orph = sum(r["_orphans"] for r in B)
        skips = sum((r["_skips"] for r in B), Counter())
        w(f"\n- Over all benchmarks and c_slack values: {bind_text}"
          + (f"; the per-(benchmark, c_slack) median ILP/A* time ratio lies between {rx(min(b_meds))} and {rx(max(b_meds))}" if b_meds else "")
          + ".\n"
          f"- Distinct instances: {BD['instances']} over all bind runs, {BD['trade']} of them with a trade-off in at least "
          f"one c_slack run. Instance identity across the c_slack runs of a benchmark: {INSTANCE_KEY}."
          + (f" Not verified (counted per run): {and_list(f'`{b}`' for b in BD['unverified'])}." if BD["unverified"] else "")
          + "\n"
          f"- ILP failures: {counts(fails)}. On {b_fastfail} rows the ILP returned before A* with a failure status (a fast "
          "failure, not a win).\n"
          f"- Skipped: {counts(skips)} instance-runs; `no_tradeoff` covers {BD['no_trade_any']} distinct instances "
          f"({BD['no_trade_all']} of them `no_tradeoff` in every c_slack run of their benchmark).\n"
          + (f"- {orph} constrained rows could not be paired (A* row without its ILP row, or the reverse).\n" if orph else ""))
        for b in b_benches:
            w(figs.link(f"bind_cslack_{b}.svg", f"{b}: solve rate by c_slack"))
        sc = [(r["bench"], r["c_slack"]) for r in B if (Path(figures_dir) / f"bind_scatter_{r['bench']}_c{r['c_slack']}.svg").is_file()]
        if sc:
            w("\nILP vs A* seconds per row (log-log, failures marked): " + ", ".join(
                f"[{b} c{c}]({rel(Path(figures_dir) / f'bind_scatter_{b}_c{c}.svg', paper_dir)})" for b, c in sc) + ".\n")

    w("\n### 7.4 Agents under noise\n")
    w(f"Success within budget (B = T* + slack) under planning error delta and execution noise eta (Section 4.4). Pooled "
      "success: successes = sum over instances of round(success x episodes), trials = episodes x instances, 95% Wilson "
      "interval (it treats the trials as independent). Paired differences: mean over instances of the per-instance "
      "success difference, 95% percentile bootstrap over instances. **react and tape are simulated.**\n")
    if SUP:
        w("One agents dataset per benchmark is used: the one with the most episodes per instance. Superseded and left out "
          "of every table and aggregate below: "
          + and_list(f"`{s['dataset']}` on `{s['bench']}` ({max(s['episodes'])} episodes; replaced by `{k['dataset']}`, "
                     f"{max(k['episodes'])} episodes)" for s, k in SUP)
          + ". A later run of the same benchmark with the same seed and `--n` re-uses the same instances and "
          "per-instance noise seeds, so its first episodes repeat the earlier run's; counting both would count the "
          "same episodes twice.\n")
    if not A:
        w("_No agents data._\n")
    else:
        rows = [{"dataset": f"`{a['dataset']}`", "bench": f"`{a['bench']}`", "method": LABEL[p["method"]],
                 "instances": p["instances"], "episodes/instance": ",".join(map(str, a["episodes"])),
                 "successes / trials": f"{p['successes']} / {p['trials']}", "success": f3(p["success"]),
                 "95% Wilson": ci(p["ci_lo"], p["ci_hi"])} for a in A for p in a["pooled"]]
        w(table(rows))
        rows = []
        for a in A:
            for t in (a["ts"][0], a["ts"][-1]) if len(a["ts"]) > 1 else a["ts"]:
                row = {"dataset": f"`{a['dataset']}`", "bench": f"`{a['bench']}`", "T*": t}
                for m in METHODS:
                    p = a["buckets"].get((m, t))
                    row[LABEL[m]] = f"{f3(p['success'])} {ci(p['ci_lo'], p['ci_hi'])}" if p else "not run"
                rows.append(row)
        w("\nSmallest and largest T* bucket per benchmark (success, 95% Wilson):\n")
        w(table(rows))
        rows = [{"dataset": f"`{a['dataset']}`", "bench": f"`{a['bench']}`",
                 "comparison": p["comparison"].replace("react", LABEL["react"]).replace("tape", LABEL["tape"]),
                 "instances": p["instances"], "mean difference": f"{p['mean_diff']:+.4f}",
                 "95% bootstrap CI": f"[{p['ci_lo']:+.4f}, {p['ci_hi']:+.4f}]"} for a in A for p in a["paired"]]
        w("\nPaired differences in success:\n")
        w(table(rows))
        w("")
        for a in A:
            tag = f"`{a['bench']}` (`{a['dataset']}`)"
            for p in a["paired"]:
                other = p["comparison"].split(" - ")[1]
                inc = "contains 0" if p["ci_lo"] <= 0 <= p["ci_hi"] else "excludes 0"
                w(f"- {tag}: ours_astar minus {LABEL[other]}: {p['mean_diff']:+.4f} [{p['ci_lo']:+.4f}, {p['ci_hi']:+.4f}] "
                  f"over {p['instances']} instances; the interval {inc}.")
            if a["common"]:
                w(f"- {tag}: tape (simulated) and ours_astar have identical success on {a['same']} of {a['common']} instances "
                  f"(tape higher on {a['tape_hi']}, lower on {a['tape_lo']}).")
            if not a["ilp"]:
                w(f"- {tag}: ILP disabled in this run (no ours_ilp rows; tape (simulated) used BFS on the folded graph).")
            for note in a["notes"]:
                w(f"- {tag}: {note.strip()}")
        w("")
        suf = _suffixes(found["agents"])
        for a in A:
            w(figs.link(f"agents_{a['bench']}{suf[(a['dataset'], a['bench'])]}.svg",
                        f"{a['bench']} ({a['dataset']}): success vs T*, 95% Wilson band"))
    for k in [k for k in missing if k in ATTEMPTED]:
        w(f"\n_Not completed: {ATTEMPTED[k]} There is no `{dref}/{k[0]}/agents_{k[1]}.csv`, so the agents comparison "
          f"covers {len({a['bench'] for a in A})} benchmarks. Its tables appear here if a future run writes the file._\n")
    missing = [k for k in missing if k not in ATTEMPTED]
    if missing:
        w("\n_pending: data not yet available: "
          + "; ".join(f"`{dref}/{d}/agents_{b}.csv` ({PENDING[(d, b)]})" for d, b in missing)
          + ". Its tables appear here when the file exists._\n")
    w(f"\n{MARK}\n{interpretation.strip()}\n{END}\n" if interpretation.strip() else f"\n{MARK}\n{END}\n")

    # ---- 8 limitations
    w("## 8 Limitations and threats to validity\n")
    lim = []
    lim.append("**The baselines are simulated.** react (simulated) and tape (simulated) use the TAPE paper's noise model and "
               "say nothing about how a real language model behaves."
               + (f" The gap between ours_astar and react (simulated), {f3(min(react_d))} to {f3(max(react_d))} in mean "
                  "per-instance success, comes from the modelling assumption that planning errors are injected unfiltered "
                  "and never corrected." if react_d else ""))
    same = sum(a["same"] for a in A)
    common = sum(a["common"] for a in A)
    excl = [a["bench"] for a, p in tape_p if not p["ci_lo"] <= 0 <= p["ci_hi"]]
    lim.append("**tape (simulated) and ours are close in success.** A hypothesis for why (not tested here): tape's "
               "rollouts come from an exact oracle with injected errors, so a shortest path in the folded graph is (close "
               "to) an optimal path of the true graph, which ours_astar follows."
               + (f" They have identical success on {same} of {common} instances over {pl(n_agent_benches, 'benchmark')} "
                  "(one agents dataset per benchmark, Section 7.4)." if common else "")
               + (f" Measured: ours_astar minus tape (simulated) is {f3(min(tape_d))} to {f3(max(tape_d))} in mean "
                  f"per-instance success; the success difference is small (at most {f3(max(abs(x) for x in tape_d))} in "
                  f"absolute value) but its bootstrap interval excludes 0 on {len(excl)} of {pl(len(tape_d), 'benchmark')}"
                  + (f" ({and_list(f'`{b}`' for b in excl)})" if excl else "")
                  + ", so it is not always indistinguishable from 0." if tape_d else "")
               + " The difference that does not depend on the noise model is cost: ours needs no oracle, no rollouts and "
               "no ILP.")
    thin = [b for b in b_benches if all(r["trade-off"] < THIN for r in B if r["bench"] == b)]
    lim.append("**Constrained evidence is thin on some benchmarks and the resources are unusual.**"
               + (f" Fewer than {THIN} trade-off instances at every c_slack run: "
                  + and_list(f"`{b}` (" + ", ".join(f"c{r['c_slack']}: {r['trade-off']}" for r in B if r["bench"] == b) + ")" for b in thin)
                  + "." if thin else "")
               + " The `bind` resources (pushes only, passengers squared, half-turns only) were chosen because they create "
               "trade-offs, so the experiment tests solver behaviour under a binding budget, not a realistic cost model. "
               "A* `ok` at the `tight` level repeats the bisection's last probe, so A*'s solve rate there is not informative; "
               "the ILP's behaviour is. The c_slack sweep mostly measures the ILP's subgraph growth: at the `bind` level R = "
               "r_opt - 1 and the constrained optimum do not depend on c_slack, so A* expands the same nodes in every run "
               "while the ILP's explicit ball {g + h <= T* + c_slack} grows with the length budget (node means in "
               "Section 7.3). ILP failures at larger c_slack are therefore a statement about the edge-flow ILP's "
               "sensitivity to a slack length budget, not about a harder trade-off. Instances where A* fails during the bisection are skipped, which biases "
               "the sample toward instances A* can handle.")
    lim.append(f"**Fairness between the ILP and A* is approximate.** The ILP's subgraph is the ball {{g + h <= budget}}, i.e. "
               f"{{g + h <= T* + slack}} in the unconstrained runs and {{g + h <= T* + c_slack}} in the `bind` runs (larger "
               f"than the region A* expands, built without resource pruning), its graph build counts toward its time, "
               f"it runs {WORKERS} CP-SAT workers against single-threaded A*, and it has a "
               f"{DEFAULTS['time_limit']:g} s solver limit that A* lacks.")
    if A:
        off = [f"`{a['bench']}` (`{a['dataset']}`)" for a in A if not a["ilp"]]
        eps = ", ".join(f"`{a['bench']}` (`{a['dataset']}`) {','.join(map(str, a['episodes']))}" for a in A)
        bs = [a["bucket_sizes"] for a in A]
        lim.append("**Agents run sizes.** Episodes per instance: " + eps + "."
                   + (f" ILP disabled (no ours_ilp rows; tape used BFS on the folded graph): {and_list(off)}." if off else "")
                   + f" Buckets hold {min(x[0] for x in bs)} to {max(x[1] for x in bs)} instances, so success differences of "
                   "a few points are within noise."
                   + (" Older agents CSVs have no `episodes` column; their episode counts come from the documented lookup "
                      "`tapegraph.bench.DOCUMENTED_EPISODES`." if any(a["looked_up"] for a in A) else ""))
    lim.append("**Timing columns.** Wall-clock `seconds` depend on what else ran on the machine; every agents run (`main`, "
               "`new_agents`, `agents_ep300`) ran as parallel processes next to other work (README), so every agents "
               "`seconds` column is contended and inflated. react and tape `seconds` include "
               "oracle computations and are not comparable to ours_*.")
    caps = sorted({(r["bench"], m) for r in B for m in r["_max_nodes"] if m != DEFAULTS["max_nodes"]}
                  | {(b, r["max_nodes"]) for _, b, rs in S["data"] for r in rs[:1]
                     if r.get("max_nodes") not in ("", None) and r["max_nodes"] != DEFAULTS["max_nodes"]})
    if caps:
        lim.append("**Node caps.** Runs with a node cap below the default: "
                   + and_list(f"`{b}` at {num(m)}" for b, m in caps)
                   + f"; the oracle that fixes T* and drives the simulated baselines has its own {num(ORACLE_CAP)}-node cap "
                   "(an instance it cannot solve is never generated). Solver failures at the cap are failures of that "
                   "configuration, not proofs of infeasibility.")
    lim.append("**Pooled Wilson intervals assume independent episodes.** Episodes of one instance share the level, so the "
               "pooled intervals are optimistic; the paired bootstrap resamples instances and is the more conservative "
               "comparison.")
    w("".join(f"{i}. {t}\n" for i, t in enumerate(lim, 1)))
    w(f"\n**Threats to validity.** The comparison with ReAct and TAPE is a comparison with simulations under one noise "
      "model; a real language model's errors are neither independent nor uniformly harmful, and TAPE's real cost (LLM "
      "calls) is absent. The ILP-vs-A* comparison favours A* in graph size (A* expands only what it needs, the ILP builds "
      f"the whole {{g + h <= T* + slack}} ball, {{g + h <= T* + c_slack}} in the `bind` runs, and counts that build) and "
      f"favours the ILP in parallelism ({WORKERS} workers); the ILP also stops at {DEFAULTS['time_limit']:g} s and reports "
      "`timeout` for any outcome short of proven optimality or infeasibility, while A* runs to its node cap. "
      "The verdicts below are about this edge-flow formulation, these limits and these benchmarks.\n")

    # ---- 9 reproducibility
    w("## 9 Reproducibility\n")
    w("```bash\n"
      "pip install -e \".[test]\"                     # numpy, ortools, pytest\n"
      "python -m pytest -q\n"
      "tapegraph all --profile smoke --out smoke_out   # tiny end-to-end pass (River, Cube2)\n"
      "tapegraph all --profile full  --out full_out    # the published main and bind commands, sequentially\n"
      "python scripts/make_figures.py                  # docs/figures/*.svg from docs/data\n"
      "python scripts/make_paper.py                    # this file from docs/data and docs/figures\n"
      "```\n")
    w("`all --profile full` writes `run_manifest.json` (commands, parameters, seconds per step, git commit, versions). The "
      "other datasets come from the commands in Section 6. Both generators are deterministic: re-running them on the same "
      "data gives byte-identical files. Data layout (`<kind>_<bench>.csv`, kind in solvers | agents | constrained):\n")
    lay = defaultdict(list)
    for k in found:
        for d, b, _ in found[k]:
            lay[d].append(f"{k}_{b}")
    w(_md([{"dataset": f"`{dref}/{d}/`", "files": ", ".join(sorted(v))} for d, v in sorted(lay.items())]))
    avail = figs.available()
    w(f"\nFigures available under `{rel(figures_dir, ROOT)}/` when this file was generated ({len(avail)}): "
      + (", ".join(f"`{n}`" for n in avail) or "none") + ".\n")

    # ---- 10 conclusion
    w("## 10 Conclusion\n")
    con = []
    if S["data"]:
        con.append(f"For BFS, A*, IDA* and the ILP, {exact_text} ({num(S['exact_n'])} solved rows), and A* with a pattern "
                   "database or distance heuristic "
                   + ("solved every unconstrained instance it was given" if a_fail == 0
                      else f"failed on {pl(a_fail, 'unconstrained instance')}")
                   + f". Instances exist only where the oracle (an exact table, or A* with a {num(ORACLE_CAP)}-node cap) "
                   "found T*, so this sample excludes instances that A*-based search could not solve (the node-cap "
                   "limitation in Section 8).")
    if ilp_both or b_both:
        never = ilp_faster == 0 and b_fast == 0
        con.append(("The ILP did not beat A* in any measured regime. " if never else "The ILP beat A* only on some rows. ")
                   + (f"Unconstrained: {unc_text}. " if S["data"] else "")
                   + (f"Binding-constrained ({pl(len(b_benches), 'benchmark')}; {cs_text}): {bind_text}. {fastfail_text}" if B else "")
                   + "This is scoped to the edge-flow formulation, the time limit, the node caps and the resources measured "
                   "here; it does not show that an ILP cannot win with other objectives (e.g. TAPE's node scores), other "
                   "formulations or much larger graphs.")
    if react_d:
        con.append(f"Re-planning on the true graph {'beats' if min(react_d) > 0 else 'differs from'} simulated ReAct by "
                   f"{f3(min(react_d))} to {f3(max(react_d))} in mean success"
                   + (f"; against simulated TAPE the bootstrap interval of the difference contains 0 on {tape_zero} of "
                      f"{pl(len(tape_d), 'benchmark')}{tape_excl}" if tape_d else "")
                   + ". Because both baselines are simulations that share an exact oracle, this supports the claim that "
                   "the loop recovers TAPE's success without a language model only within that model.")
    con.append("What the evidence does not support: anything about real language models, about resources an application "
               "would care about, or about benchmarks beyond the generated ones (no real Boxoban levels were run).")
    w("\n\n".join(con) + "\n")

    # ---- references
    w("## References\n")
    w("- Culberson (1997). Sokoban is PSPACE-complete.\n"
      "- Google OR-Tools, CP-SAT solver.\n"
      "- Guez et al. (2019). An investigation of model-free planning. (Source of Boxoban.)\n"
      "- Hart, Nilsson, Raphael (1968). A Formal Basis for the Heuristic Determination of Minimum Cost Paths (A*). IEEE "
      "Transactions on Systems Science and Cybernetics.\n"
      "- Jeong, Kim, Lee (2026). TAPE. arXiv:2602.19633.\n"
      "- Korf (1985). Depth-first iterative-deepening: An optimal admissible tree search (IDA*). Artificial Intelligence 27.\n"
      "- Korf (1997). Finding optimal solutions to Rubik's Cube using pattern databases. AAAI.\n"
      "- Yao et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models.\n")
    return "\n".join(out)


def read_interpretation(path):
    """Text between the INTERPRETATION-7.4 markers of an existing paper ('' if the file or both markers are absent).
    Raises ValueError when the markers are not exactly one start and one end marker in that order, so hand-written
    text is never overwritten silently."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    ns, ne = text.count(MARK), text.count(END)
    if ns == ne == 0:
        return ""
    if ns != 1 or ne != 1 or text.index(MARK) > text.index(END):
        raise ValueError(f"{path}: expected exactly one '{MARK}' followed by one '{END}' (found {ns} start and {ne} end "
                         "markers); fix the markers by hand so the interpretation text is not lost")
    return text[text.index(MARK) + len(MARK):text.index(END)].strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--figures", default=str(ROOT / "docs" / "figures"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "paper.md"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    text = build_paper(Path(a.data), Path(a.figures), out.parent.resolve(), read_interpretation(out))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"[wrote] {out}")


if __name__ == "__main__":
    main()
