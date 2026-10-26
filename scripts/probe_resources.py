"""Probe: which candidate side-resource definitions make the resource constraint bind?

For each benchmark and resource definition, counts instances where allowing a longer path (length <= T*+slack) lowers
the minimal resource below that of the length-T* optimum (r_min < r_opt, see bench.bind_budgets), for slack 2/4/8
(cube2/boxoban: 2/4). Output per resource: "slackK: <instances with a trade-off>/<instances evaluated>".
The `current*` / `passengers` / `QTM(1/2)` rows are the original Problem.res; the others are candidates, and the ones
adopted as Problem.res_bind are pushes_only (sokoban/boxoban), load^2 (river), halves (cube2).

Run from the repo root, one benchmark at a time (n instances per T* bucket, seed 1; --n defaults to the value behind
the README's probe table: 5 river/sokoban, 4 cube2, 3 boxoban):
    python scripts/probe_resources.py sokoban|river|cube2|boxoban [--n N]
"""
import argparse
import sys
import time
from pathlib import Path

try:
    from tapegraph import bench
except ImportError:  # not pip-installed: fall back to the repo checkout
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tapegraph import bench
from tapegraph.benchmarks import make_instances
from tapegraph.solvers import astar


def probe(name, n, resdefs, slacks=(2, 4, 8), cap=300_000, Ts=None):
    insts = make_instances(name, n, 1)
    if Ts: insts = [i for i in insts if i.T in Ts]
    print(f"== {name}: {len(insts)} instances")
    for rname, rfn in resdefs.items():
        stats = {k: [0, 0] for k in slacks}  # tradeoff count, evaluated
        t0 = time.time()
        for inst in insts:
            p = inst.problem
            old = p.__dict__.get("res")
            p.res = rfn(p)
            try:
                base = astar.solve(p, inst.start, budget=inst.T, max_nodes=cap)
                if base.status != "ok": continue
                _, ropt = bench.min_resource(p, inst.start, inst.T, int(round(base.res)), cap)
                if ropt is None: continue
                for k in slacks:
                    _, rm = bench.min_resource(p, inst.start, inst.T + k, ropt, cap)
                    if rm is None: continue
                    stats[k][1] += 1
                    stats[k][0] += int(rm < ropt)
            finally:
                if old is None: del p.__dict__["res"]
                else: p.res = old
        print(f"  res={rname:14s} " + "  ".join(f"slack{k}: {a}/{b}" for k, (a, b) in stats.items()) + f"   ({time.time()-t0:.0f}s)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bench", choices=["sokoban", "river", "cube2", "boxoban"])
    ap.add_argument("--n", type=int, help="instances per T* bucket (default: 5 river/sokoban, 4 cube2, 3 boxoban)")
    a = ap.parse_args(argv)
    which = a.bench
    if which == "sokoban":
        push = lambda p: (lambda s, a, s2: 1.0 if s2[1] != s[1] else 0.0)
        cur = lambda p: (lambda s, a, s2: 3.0 if s2[1] != s[1] else 1.0)
        probe("sokoban", a.n or 5, {"current(1/3)": cur, "pushes_only": push})
    elif which == "river":
        cur = lambda p: (lambda s, a, s2: float(abs(s[0]-s2[0]) + abs(s[1]-s2[1])))
        wt = lambda p: (lambda s, a, s2: float(abs(s[0]-s2[0]) * 3 + abs(s[1]-s2[1])))      # missionaries cost 3
        sq = lambda p: (lambda s, a, s2: float((abs(s[0]-s2[0]) + abs(s[1]-s2[1])) ** 2))   # crowded boats cost more
        probe("river", a.n or 5, {"passengers": cur, "mission*3": wt, "load^2": sq})
    elif which == "cube2":
        cur = lambda p: (lambda s, a, s2: 2.0 if a.endswith("2") else 1.0)
        quarter_only_cost = lambda p: (lambda s, a, s2: 0.0 if a.endswith("2") else 1.0)  # count quarter-turns only
        half_only = lambda p: (lambda s, a, s2: 1.0 if a.endswith("2") else 0.0)           # count half-turns only
        probe("cube2", a.n or 4, {"QTM(1/2)": cur, "quarters": quarter_only_cost, "halves": half_only}, slacks=(2, 4), cap=200_000, Ts={5, 7, 8})
    else:
        push = lambda p: (lambda s, a, s2: 1.0 if s2[1] != s[1] else 0.0)
        cur = lambda p: (lambda s, a, s2: 3.0 if s2[1] != s[1] else 1.0)
        probe("boxoban", a.n or 3, {"current(1/3)": cur, "pushes_only": push}, slacks=(2, 4), cap=200_000, Ts={8, 12, 16})


if __name__ == "__main__":
    main()
