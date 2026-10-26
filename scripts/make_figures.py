"""Write the SVG figures of the report from the committed CSVs under --data (stdlib + numpy only, deterministic).

    python scripts/make_figures.py [--data docs/data] [--out docs/figures]

Directories under --data are discovered by globbing `*/`; files are `<kind>_<bench>.csv` with kind in
solvers | agents | constrained. A figure whose inputs are absent is skipped with a printed note, so directories that
land later (new_agents, agents_ep300, ...) are picked up automatically. A file name carries the directory as a suffix
only when the same (kind, bench) exists in more than one directory (the `main` one stays unsuffixed).
Figures: agents_<bench>, solvers_nodes_<bench>, solvers_seconds_<bench>, ilp_rate_<bench>,
bind_scatter_<bench>_c<c_slack>, bind_cslack_<bench>.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tapegraph.bench import _num, agent_instance_rows  # noqa: E402
from tapegraph.plots import bar_chart, line_chart, scatter  # noqa: E402
from tapegraph.stats import wilson_interval  # noqa: E402

KINDS = ("solvers", "agents", "constrained")
METHOD_ORDER = ["react", "tape", "ours_astar", "ours_ilp"]
SOLVER_ORDER = ["bfs", "astar", "wastar", "idastar", "ilp"]
SEC_FLOOR = 1e-5  # seconds are stored to 5 decimals: a recorded 0.0 means "below 1e-5"; clamped so it can sit on a log axis
LEGACY_C_SLACK = 4  # bind CSVs written before the c_slack column existed (docs/data/bind) used c_slack 4 (README)


def _order(names, preferred):
    return sorted(set(names), key=lambda n: (preferred.index(n) if n in preferred else len(preferred), n))


def load(data):
    """{kind: [(dirname, bench, rows)]} for every `<kind>_<bench>.csv` in every sub-directory of `data`."""
    found = defaultdict(list)
    for d in sorted(p for p in Path(data).glob("*") if p.is_dir()):
        for f in sorted(d.glob("*.csv")):
            kind, _, bench = f.stem.partition("_")
            if kind not in KINDS or not bench:
                continue
            with open(f, newline="") as fh:
                rows = [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(fh)]
            if rows:
                found[kind].append((d.name, bench, rows))
    return found


def _suffixes(entries):
    """Directory suffix per (dirname, bench): only when the same bench exists in several directories (main unsuffixed)."""
    dirs = defaultdict(set)
    for d, b, _ in entries:
        dirs[b].add(d)
    return {(d, b): ("" if len(dirs[b]) == 1 or d == "main" else "_" + d) for d, b, _ in entries}


# ---- (a) agents ------------------------------------------------------------------------------------------------

def agent_series(rows):
    """(series, n_instances, episodes) for one agents CSV: success per (method, T*) pooled over instances
    (successes = sum of round(success * episodes), trials = episodes x instances, via bench.agent_instance_rows)
    with 95% Wilson limits."""
    used = agent_instance_rows(rows)[0]
    cell = defaultdict(lambda: [0, 0])
    for r in used:
        c = cell[(r["method"], r["T"])]
        c[0] += r["k"]
        c[1] += r["ep"]
    series = []
    for m in _order([m for m, _ in cell], METHOD_ORDER):
        ts = sorted(t for mm, t in cell if mm == m)
        ci = [wilson_interval(*cell[(m, t)]) for t in ts]
        series.append({"name": m, "x": ts, "y": [cell[(m, t)][0] / cell[(m, t)][1] for t in ts],
                       "lo": [c[0] for c in ci], "hi": [c[1] for c in ci]})
    return series, len({r["inst"] for r in used}), sorted({r["ep"] for r in used})


def agents_figure(bench, tag, rows):
    series, n, eps = agent_series(rows)
    if not series:
        return None
    title = (f"{bench} agents{tag}: success vs T* (n={n} instances x {'/'.join(map(str, eps))} episodes, 95% Wilson band)")
    return line_chart(series, title=title, xlabel="T* (optimal plan length)", ylabel="success rate", ylim=(0, 1))


# ---- (b) unconstrained solvers: nodes and seconds, (d) ILP solve rate ------------------------------------------

def _n_instances(rows):
    c = defaultdict(int)
    for r in rows:
        c[r["solver"]] += 1
    return max(c.values())  # every instance produces one row per solver


def solver_figures(bench, tag, rows):
    """{"nodes": svg, "seconds": svg, "ilp_rate": svg or None}. Lines are the median over solved (status ok) rows per
    (solver, T*); every non-ok row is shown, as a hollow cross in a strip above the plot (one strip row per
    solver and status, labelled with the count at that T*)."""
    n = _n_instances(rows)
    solvers = _order([r["solver"] for r in rows], SOLVER_ORDER)
    figs = {}
    for metric, floor, ylabel in (("nodes", 1.0, "nodes expanded (median of solved rows)"),
                                  ("seconds", SEC_FLOOR, "seconds (median of solved rows)")):
        series, fails = [], []
        for s in solvers:
            ok = defaultdict(list)
            bad = defaultdict(lambda: defaultdict(int))
            for r in rows:
                if r["solver"] != s:
                    continue
                if r["status"] == "ok" and r.get(metric) not in ("", None):
                    ok[r["T"]].append(max(float(r[metric]), floor))
                elif r["status"] != "ok":
                    bad[r["status"]][r["T"]] += 1
            ts = sorted(ok)
            series.append({"name": s, "x": ts, "y": [median(ok[t]) for t in ts]})
            for st in sorted(bad):
                xs = sorted(bad[st])
                fails.append({"name": f"{s} {st}", "owner": s, "kind": "fail", "x": xs, "labels": [str(bad[st][t]) for t in xs]})
        figs[metric] = line_chart(series + fails, ylog=True, xlabel="T* (optimal plan length)", ylabel=ylabel,
                                  title=f"{bench} solvers{tag}: {metric} vs T* (n={n} instances; crosses = failed rows, count at T*)")
    ilp = [r for r in rows if r["solver"] == "ilp"]
    figs["ilp_rate"] = None
    if ilp:
        cell = defaultdict(lambda: [0, 0])
        for r in ilp:
            cell[r["T"]][0] += r["status"] == "ok"
            cell[r["T"]][1] += 1
        ts = sorted(cell)
        ci = [wilson_interval(*cell[t]) for t in ts]
        ser = [{"name": "ilp", "x": ts, "y": [cell[t][0] / cell[t][1] for t in ts], "lo": [c[0] for c in ci], "hi": [c[1] for c in ci]}]
        figs["ilp_rate"] = line_chart(ser, xlabel="T* (optimal plan length)", ylabel="ILP solve rate (status ok)", ylim=(0, 1),
                                      title=f"{bench} ILP{tag}: solve rate vs T* (n={len(ilp)} ILP runs, 95% Wilson band)")
    return figs


# ---- (c) constrained, design=bind ------------------------------------------------------------------------------

def bind_pairs(rows):
    """[(A* row, ILP row)] for the (instance, level) rows of a bind CSV: an astar row followed by the ilp row of the
    same T* and level (skipped rows carry no timing and are ignored); also the number of unpaired rows."""
    pairs, pend, orphans = [], None, 0
    for r in rows:
        if r.get("solver") == "astar":
            orphans += pend is not None
            pend = r
        elif r.get("solver") == "ilp":
            if pend is not None and (pend["T"], pend["level"]) == (r["T"], r["level"]):
                pairs.append((pend, r))
            else:
                orphans += 1
            pend = None
    return pairs, orphans + (pend is not None)


def _rate(rows, solver):
    rs = [r for r in rows if r.get("solver") == solver and r.get("level") in ("bind", "tight")]
    return sum(r["status"] == "ok" for r in rs), len(rs)


def bind_scatter(bench, c, rows):
    pairs, orphans = bind_pairs(rows)
    usable = [(a, i) for a, i in pairs if a["status"] == "ok"]
    n_inst = sum(a["level"] == "bind" for a, _ in usable)
    series, vals = [], []
    for level in ("bind", "tight"):
        pts = [(max(float(a["seconds"]), SEC_FLOOR), max(float(i["seconds"]), SEC_FLOOR)) for a, i in usable
               if i["level"] == level and i["status"] == "ok"]
        vals += [v for p in pts for v in p]
        series.append({"name": f"{level} level (ILP solved)", "kind": "points", "x": [p[0] for p in pts], "y": [p[1] for p in pts]})
    fails = defaultdict(list)
    for a, i in usable:
        if i["status"] != "ok":
            fails[i["status"]].append(max(float(a["seconds"]), SEC_FLOOR))
            vals.append(fails[i["status"]][-1])
    if not vals:
        return None
    lim = (min(vals), max(vals))
    ref = {"name": "y = x", "kind": "ref", "x": list(lim), "y": list(lim)}
    fs = [{"name": f"ILP {st} ({len(xs)})", "kind": "fail", "owner": series[0]["name"], "x": sorted(xs)} for st, xs in sorted(fails.items())]
    nrows = len(usable)
    title = (f"{bench}, c_slack {c}: ILP vs A* seconds (n={n_inst} instances, {nrows} (instance, level) rows"
             + (f", {orphans} unpaired dropped" if orphans else "") + ")")
    return scatter(series + [ref] + fs, title=title, xlabel="A* seconds", ylabel="ILP seconds",
                   xlog=True, ylog=True, xlim=lim, ylim=lim)


def bind_cslack_bar(bench, by_c):
    cs = sorted(by_c)
    ilp = [_rate(by_c[c], "ilp") for c in cs]
    astar = [_rate(by_c[c], "astar") for c in cs]

    def ser(name, rs):
        ci = [wilson_interval(*r) for r in rs]
        return {"name": name, "y": [r[0] / r[1] if r[1] else None for r in rs], "lo": [c[0] for c in ci], "hi": [c[1] for c in ci]}

    rowsn = ", ".join(f"c{c}: {n[1]}" for c, n in zip(cs, ilp))
    return bar_chart([str(c) for c in cs], [ser("ILP", ilp), ser("A*", astar)], ylim=(0, 1), xlabel="c_slack",
                     ylabel="solve rate (status ok)",
                     title=f"{bench}: solve rate by c_slack (rows per c_slack, {rowsn}; 95% Wilson)")


def bind_by_bench(found):
    """{bench: {c_slack: (dirname, rows)}} for the design=bind constrained CSVs (files with a level column; first
    directory in sorted order wins for a repeated (bench, c_slack))."""
    by_bench = defaultdict(dict)
    for d, bench, rows in found["constrained"]:
        if "level" not in rows[0]:
            continue  # design=frac (no level column): not a bind run
        c = next((r["c_slack"] for r in rows if r.get("c_slack") not in ("", None)), LEGACY_C_SLACK)
        if c in by_bench[bench]:
            print(f"[skip] constrained {d}/{bench} c_slack {c}: already taken from another directory")
            continue
        by_bench[bench][c] = (d, rows)
    return by_bench


# ---- driver -----------------------------------------------------------------------------------------------------

def make_figures(data="docs/data", out="docs/figures"):
    """Write every figure the data supports into `out`; returns the sorted list of file names written."""
    found = load(data)
    written = {}

    def emit(name, svg):
        if svg is not None:
            written[name] = svg

    for kind in ("agents", "solvers"):
        suf = _suffixes(found[kind])
        if not found[kind]:
            print(f"[skip] no {kind}_*.csv under {data}")
        for d, bench, rows in found[kind]:
            tag, sfx = ("" if d == "main" else f" [{d}]"), suf[(d, bench)]
            if kind == "agents":
                svg = agents_figure(bench, tag, rows)
                if svg is None:
                    print(f"[skip] agents {d}/{bench}: no usable rows (skipped rows, or old CSV without episodes and no documented episode count)")
                emit(f"agents_{bench}{sfx}.svg", svg)
            else:
                f = solver_figures(bench, tag, rows)
                emit(f"solvers_nodes_{bench}{sfx}.svg", f["nodes"])
                emit(f"solvers_seconds_{bench}{sfx}.svg", f["seconds"])
                if f["ilp_rate"] is None:
                    print(f"[skip] ILP rate {d}/{bench}: no ilp rows")
                emit(f"ilp_rate_{bench}{sfx}.svg", f["ilp_rate"])
    by_bench = {b: {c: rows for c, (_, rows) in cs.items()} for b, cs in bind_by_bench(found).items()}
    if not by_bench:
        print("[skip] no bind constrained_*.csv (files with a level column)")
    for bench in sorted(by_bench):
        for c in sorted(by_bench[bench]):
            svg = bind_scatter(bench, c, by_bench[bench][c])
            if svg is None:
                print(f"[skip] bind scatter {bench} c_slack {c}: no paired rows")
            emit(f"bind_scatter_{bench}_c{c}.svg", svg)
        emit(f"bind_cslack_{bench}.svg", bind_cslack_bar(bench, by_bench[bench]))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in sorted(written.items()):
        with open(out / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        print(f"[wrote] {out / name}")
    return sorted(written)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "figures"))
    a = ap.parse_args(argv)
    make_figures(a.data, a.out)


if __name__ == "__main__":
    main()
