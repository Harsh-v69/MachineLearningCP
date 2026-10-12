"""Phase 6: do other search methods help? BFS, DFS, weighted A* and meet in
the middle, on every game they can run on. No checkers, so only the
algorithm differs. Writes results/search_methods.md and .json.

AO* is not run: it solves AND/OR graphs (actions with several possible
outcomes). Every game here is deterministic, so its graph has no AND nodes
and AO* reduces to A*. See progress.md Sec 19.

Usage: python experiments/compare_search.py [--budget 100000] [--workers 10]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tape.bidirectional import BidirectionalProposer
from tape.envs.boxoban import load_boxoban
from tape.envs.peg_solitaire import LEVEL_CLASSIC as PEG
from tape.envs.river_crossing import LEVEL_CLASSIC as RIVER
from tape.envs.rubiks_cube import CUBE_3
from tape.envs.rush_hour import LEVEL_CLASSIC as RUSH
from tape.envs.sliding_puzzle import LEVEL_24
from tape.envs.sokoban import LEVEL_MULTI
from tape.search_proposer import WeightedAStarProposer
from tape.uninformed import BFSProposer, DFSProposer

ALGS = ["BFS", "DFS", "weighted A*", "meet in the middle"]


def peg_backwards(seed, moves):
    rng = random.Random(seed)
    while True:
        s = 1 << PEG.center
        for _ in range(moves):
            options = [(f, o, t) for f, o, t in PEG.jumps if s >> t & 1 and not s >> f & 1 and not s >> o & 1]
            if not options:
                break
            f, o, t = rng.choice(options)
            s = (s & ~(1 << t)) | (1 << f) | (1 << o)
        else:
            return s


def make_cases():
    """(group, label, level, start, max_depth, weight, can_bidirectional)"""
    cases = [
        ("River Crossing", "classic", RIVER, RIVER.initial_state, 20, 1, False),
        ("Rush Hour", "classic", RUSH, RUSH.initial_state, 20, 1, False),
        ("Sokoban", "two boxes", LEVEL_MULTI, LEVEL_MULTI.initial_state, 30, 2, False),
        ("Peg Solitaire", "real start", PEG, PEG.initial_state, 31, 2, False),
    ]
    for lv in load_boxoban(limit=20):
        cases.append(("Boxoban (20 levels)", "medium", lv, lv.initial_state, 150, 2, False))
    for i in range(20):
        cases.append(("Peg Solitaire, 22 jumps out", "backwards", PEG, peg_backwards(i, 22), 22, 2, False))
    for d in (20, 40):
        for i in range(20):
            s = LEVEL_24.scramble(d, random.Random(i))
            cases.append((f"24-puzzle, {d} move scramble", "random walk", LEVEL_24.with_start(s), s, 150, 3, True))
    for d in (5, 6):
        for i in range(20):
            s = CUBE_3.scramble(d, random.Random(i))
            cases.append((f"Rubik's cube, {d} move scramble", "random walk", CUBE_3.with_start(s), s, 12, 2, True))
    return cases


def run_case(args):
    idx, budget = args
    group, _, level, start, depth, weight, bidir = make_cases()[idx]
    algs = {"BFS": BFSProposer(node_budget=budget), "DFS": DFSProposer(node_budget=budget),
            "weighted A*": WeightedAStarProposer(weights=(weight,), node_budget=budget)}
    if bidir:
        algs["meet in the middle"] = BidirectionalProposer(node_budget=budget)
    out = {}
    for name, p in algs.items():
        plans = p.generate_candidate_plans(level, start, 1, depth)
        out[name] = {"solved": bool(plans), "nodes": p.expansions, "moves": len(plans[0]) if plans else None}
    return group, out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=100_000)
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    n = len(make_cases())
    groups: dict[str, list] = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for group, out in ex.map(run_case, [(i, a.budget) for i in range(n)], chunksize=1):
            groups.setdefault(group, []).append(out)
    R = {"budget": a.budget, "games": {}}
    for group, rows in groups.items():
        R["games"][group] = {"n": len(rows)}
        for alg in ALGS:
            r = [x[alg] for x in rows if alg in x]
            if not r:
                continue
            solved = [x for x in r if x["solved"]]
            R["games"][group][alg] = {
                "solved": len(solved) / len(r),
                "nodes": sum(x["nodes"] for x in solved) / len(solved) if solved else None,
                "moves": sum(x["moves"] for x in solved) / len(solved) if solved else None}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "search_methods.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    L = [f"# Search methods compared (budget {a.budget:,} nodes per search, no checkers)\n",
         "Each cell: share solved, then mean nodes and mean plan length over the solved ones.\n",
         "| game | instances | " + " | ".join(ALGS) + " |", "|---|---|" + "---|" * len(ALGS)]
    for group, g in R["games"].items():
        cells = []
        for alg in ALGS:
            c = g.get(alg)
            cells.append("n/a" if c is None else f"{c['solved']:.0%}" + (f", {c['nodes']:,.0f} nodes, {c['moves']:.1f} moves" if c["nodes"] is not None else ""))
        L.append(f"| {group} | {g['n']} | " + " | ".join(cells) + " |")
    text = "\n".join(L) + "\n"
    (ROOT / "results" / "search_methods.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
