"""Phase 6: three harder games, no LLM. Writes results/hard_games.md and .json.

Peg Solitaire    solve rate within a node budget, no checker vs pagoda checker,
                 on the start position and on positions built backwards from
                 the goal, so every one is known to be solvable.
24-puzzle        solve rate by scramble depth (weighted A*), and the nodes a
                 search wastes on an unsolvable start with and without the
                 parity gate.
Rubik's cube     solve rate and nodes by scramble depth (meet-in-the-middle
                 search), and the nodes wasted on a twisted, unsolvable cube
                 with and without the invariant gate.

Usage: python experiments/run_hard_games.py [--n 60] [--workers 10]
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
from tape.envs.peg_solitaire import LEVEL_CLASSIC as PEG
from tape.envs.peg_solitaire_validator import PegPagodaValidator
from tape.envs.rubiks_cube import CUBE_3
from tape.envs.rubiks_cube_validator import CubeSolvabilityValidator
from tape.envs.sliding_puzzle import LEVEL_24
from tape.envs.sliding_puzzle_validator import SlidingParityValidator
from tape.search_proposer import WeightedAStarProposer

PEG_BUDGET, PEG_DEPTHS = 60_000, (12, 18, 22, 26)
PUZ_BUDGET, PUZ_DEPTHS = 60_000, (20, 40, 60, 80)
CUBE_BUDGET, CUBE_DEPTHS = 400_000, (4, 5, 6, 7, 8)


def peg_position(args):
    """A solvable position needing exactly `moves` jumps: play jumps backwards from the goal."""
    seed, moves = args
    rng = random.Random(seed)
    while True:  # a backwards walk can corner itself; start over then
        s = 1 << PEG.center
        for _ in range(moves):
            options = [(f, o, t) for f, o, t in PEG.jumps if s >> t & 1 and not s >> f & 1 and not s >> o & 1]
            if not options:
                break
            f, o, t = rng.choice(options)
            s = (s & ~(1 << t)) | (1 << f) | (1 << o)
        else:
            break
    out, v = {}, PegPagodaValidator()
    for arm, val in (("plain", None), ("checker", v)):
        p = WeightedAStarProposer(weights=(2,), node_budget=PEG_BUDGET, validator=val)
        plans = p.generate_candidate_plans(PEG, s, 1, 60)
        out[arm] = {"solved": bool(plans), "nodes": p.expansions}
    return out


def peg_start(weight):
    out, v = {}, PegPagodaValidator()
    for arm, val in (("plain", None), ("checker", v)):
        p = WeightedAStarProposer(weights=(weight,), node_budget=400_000, validator=val)
        plans = p.generate_candidate_plans(PEG, PEG.initial_state, 1, 60)
        out[arm] = {"solved": bool(plans), "nodes": p.expansions}
    return out


def puzzle_case(args):
    seed, depth = args
    s = LEVEL_24.scramble(depth, random.Random(seed))
    out = {}
    for kind, start in (("solvable", s), ("unsolvable", LEVEL_24.unsolvable_twin(s))):
        lv = LEVEL_24.with_start(start)
        for arm, val in (("plain", None), ("gate", SlidingParityValidator())):
            p = WeightedAStarProposer(weights=(3,), node_budget=PUZ_BUDGET, validator=val)
            plans = p.generate_candidate_plans(lv, start, 1, 600)
            out[f"{kind}_{arm}"] = {"solved": bool(plans), "nodes": p.expansions, "moves": len(plans[0]) if plans else None}
    return out


def cube_case(args):
    seed, depth = args
    s = CUBE_3.scramble(depth, random.Random(seed))
    v = CubeSolvabilityValidator(CUBE_3)
    o = v._corners[0]
    t = list(s)
    t[o[0]], t[o[1]], t[o[2]] = s[o[1]], s[o[2]], s[o[0]]
    out = {}
    for kind, start in (("solvable", s), ("unsolvable", tuple(t))):
        lv = CUBE_3.with_start(start)
        for arm, val in (("plain", None), ("gate", v)):
            p = BidirectionalProposer(node_budget=CUBE_BUDGET, validator=val)
            plans = p.generate_candidate_plans(lv, start, 1, 12)
            out[f"{kind}_{arm}"] = {"solved": bool(plans), "nodes": p.expansions, "moves": len(plans[0]) if plans else None}
    return out


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    R: dict = {"n": a.n}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        R["peg_start"] = {str(w): r for w, r in zip((2, 4), ex.map(peg_start, (2, 4)))}
        R["peg"] = {}
        for k in PEG_DEPTHS:
            rows = list(ex.map(peg_position, [(i, k) for i in range(a.n)], chunksize=2))
            R["peg"][str(k)] = {arm: {"solved": mean(r[arm]["solved"] for r in rows),
                                      "nodes": mean(r[arm]["nodes"] for r in rows)} for arm in ("plain", "checker")}
            R["peg"][str(k)]["only_checker"] = sum(r["checker"]["solved"] and not r["plain"]["solved"] for r in rows)
            R["peg"][str(k)]["only_plain"] = sum(r["plain"]["solved"] and not r["checker"]["solved"] for r in rows)
        R["puzzle"] = {}
        for d in PUZ_DEPTHS:
            rows = list(ex.map(puzzle_case, [(i, d) for i in range(a.n)], chunksize=2))
            R["puzzle"][str(d)] = {
                "solved": mean(r["solvable_plain"]["solved"] for r in rows),
                "gate_same": all(r["solvable_plain"]["solved"] == r["solvable_gate"]["solved"] for r in rows),
                "moves": mean(r["solvable_plain"]["moves"] for r in rows if r["solvable_plain"]["moves"]),
                "waste_plain": mean(r["unsolvable_plain"]["nodes"] for r in rows),
                "waste_gate": mean(r["unsolvable_gate"]["nodes"] for r in rows)}
        R["cube"] = {}
        for d in CUBE_DEPTHS:
            rows = list(ex.map(cube_case, [(i, d) for i in range(max(10, a.n // 2))], chunksize=1))
            R["cube"][str(d)] = {
                "solved": mean(r["solvable_plain"]["solved"] for r in rows),
                "nodes": mean(r["solvable_plain"]["nodes"] for r in rows),
                "moves": mean(r["solvable_plain"]["moves"] for r in rows if r["solvable_plain"]["moves"]),
                "gate_same": all(r["solvable_plain"]["solved"] == r["solvable_gate"]["solved"] for r in rows),
                "waste_plain": mean(r["unsolvable_plain"]["nodes"] for r in rows),
                "waste_gate": mean(r["unsolvable_gate"]["nodes"] for r in rows)}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "hard_games.json").write_text(json.dumps(R, indent=1), encoding="utf-8")

    L = [f"# Harder games ({a.n} instances per row, no LLM)\n",
         f"## Peg Solitaire (weighted A*, weight 2, budget {PEG_BUDGET:,} nodes per search)\n",
         "Start position, nodes until the first plan (weight 2 / weight 4):\n",
         "| | no checker | pagoda checker |", "|---|---|---|"]
    L.append("| nodes | " + " / ".join(f"{R['peg_start'][w]['plain']['nodes']:,}" for w in ("2", "4")) + " | "
             + " / ".join(f"{R['peg_start'][w]['checker']['nodes']:,}" for w in ("2", "4")) + " |")
    L += ["", "Positions built by playing k jumps backwards from the goal (every one is solvable in k moves):\n",
          "| moves to goal | solved, no checker | solved, checker | mean nodes, no checker | mean nodes, checker | solved only with checker | only without |",
          "|---|---|---|---|---|---|---|"]
    for k, r in R["peg"].items():
        L.append(f"| {k} | {r['plain']['solved']:.0%} | {r['checker']['solved']:.0%} | {r['plain']['nodes']:,.0f} | {r['checker']['nodes']:,.0f} | {r['only_checker']} | {r['only_plain']} |")
    L += ["", f"## 24-puzzle (weighted A*, weight 3, budget {PUZ_BUDGET:,} nodes)\n",
          "| scramble moves | solved | mean solution moves | gate changes any result | nodes wasted on unsolvable start, no gate | with gate |",
          "|---|---|---|---|---|---|"]
    for d, r in R["puzzle"].items():
        L.append(f"| {d} | {r['solved']:.0%} | {r['moves']:.0f} | {'no' if r['gate_same'] else 'YES'} | {r['waste_plain']:,.0f} | {r['waste_gate']:,.0f} |")
    L += ["", f"## Rubik's cube 3x3x3 (meet in the middle, budget {CUBE_BUDGET:,} nodes)\n",
          "| scramble moves | solved | mean nodes | mean solution moves | gate changes any result | nodes wasted on twisted cube, no gate | with gate |",
          "|---|---|---|---|---|---|---|"]
    for d, r in R["cube"].items():
        L.append(f"| {d} | {r['solved']:.0%} | {r['nodes']:,.0f} | {r['moves']:.1f} | {'no' if r['gate_same'] else 'YES'} | {r['waste_plain']:,.0f} | {r['waste_gate']:,.0f} |")
    text = "\n".join(L) + "\n"
    (ROOT / "results" / "hard_games.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
