"""Boxoban benchmark (Phase 6): standard external Sokoban levels, no LLM.

Proposer: weighted A* under a node budget (tape.search_proposer). Two arms:
  plain  the search knows nothing about dead corners
  prune  the Phase 2 corner-deadlock checker prunes the search
Then the pipeline merges the surviving plans and picks the cheapest path.

Reported per node budget: solve rate (any plan found). At the full budget:
mean nodes expanded, and how much the merged path improves on the best
single plan. Budgets below the full one are read off the same run, since
a search solves within budget b exactly when it used at most b expansions.

Usage: python experiments/run_boxoban.py --levels 100
"""
from __future__ import annotations

import argparse
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tape.envs.boxoban import load_boxoban
from tape.graph import build_validated_plan_graph
from tape.path_selector import select_path_adaptive
from tape.search_proposer import WeightedAStarProposer
from tape.validator import CornerDeadlockValidator

BUDGETS = [2_000, 5_000, 10_000, 20_000, 30_000]
FULL = BUDGETS[-1]


def one_level(args):
    idx, path = args
    level = load_boxoban(path)[idx]
    start, val = level.initial_state, CornerDeadlockValidator()
    out = {"idx": idx}
    for arm, v in (("plain", None), ("prune", val)):
        prop = WeightedAStarProposer(node_budget=FULL, validator=v)
        plans = prop.generate_candidate_plans(level, start, 4, 400)
        rec = {"log": prop.log, "expansions": prop.expansions, "best": None, "merged": None}
        if plans:
            g = build_validated_plan_graph(level, start, plans, val, max_depth=max(map(len, plans)))
            sol, _ = select_path_adaptive(level, g)
            rec["best"], rec["merged"] = min(map(len, plans)), (len(sol.actions) if sol else None)
        out[arm] = rec
    return out


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def solved_within(rec, b):
    return any(pl is not None and e <= b for _, e, pl in rec["log"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--levels", type=int, default=100)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default="boxoban.md")
    ap.add_argument("--workers", type=int, default=10)  # each search holds large state sets; 40 workers ran out of resources
    a = ap.parse_args()
    from tape.envs.boxoban import DEFAULT_FILE
    path = a.file or str(DEFAULT_FILE)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(one_level, [(i, path) for i in range(a.levels)], chunksize=2))
    n = len(rows)
    L = [f"# Boxoban benchmark ({n} levels, 10x10, 4 boxes, {Path(path).stem})\n",
         "Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.\n",
         "## Solve rate by node budget (any of the four searches finds a plan)\n",
         "| budget | plain | prune | levels only prune solves | levels only plain solves |", "|---|---|---|---|---|"]
    for b in BUDGETS:
        sp = [solved_within(r["plain"], b) for r in rows]
        sq = [solved_within(r["prune"], b) for r in rows]
        lp, hp = wilson(sum(sp), n); lq, hq = wilson(sum(sq), n)
        L.append(f"| {b:,} | {sum(sp)/n:.0%} [{lp:.0%}, {hp:.0%}] | {sum(sq)/n:.0%} [{lq:.0%}, {hq:.0%}] | "
                 f"{sum(q and not p for p, q in zip(sp, sq))} | {sum(p and not q for p, q in zip(sp, sq))} |")
    exp_p = sum(r["plain"]["expansions"] for r in rows) / n
    exp_q = sum(r["prune"]["expansions"] for r in rows) / n
    L += ["", f"Mean nodes expanded per level at the full budget: plain {exp_p:,.0f}, prune {exp_q:,.0f} "
              f"({1 - exp_q / exp_p:.0%} fewer).\n", "## Merging plans (prune arm)\n"]
    solved = [r["prune"] for r in rows if r["prune"]["best"] is not None]
    better = [(r["best"] - r["merged"]) for r in solved if r["merged"] is not None and r["merged"] < r["best"]]
    worse = sum(1 for r in solved if r["merged"] is not None and r["merged"] > r["best"])
    saved = f" (mean {sum(better) / len(better):.1f} moves saved)" if better else ""
    L.append(f"Levels solved: {len(solved)}. The merged path is shorter than the best single plan on "
             f"{len(better)} levels{saved} and longer on {worse}.")
    text = "\n".join(L) + "\n"
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
