"""Phase 6: tune Phase 4's ScoreWeights instead of trusting hand-picked defaults.

Setting: the state-dependent-slip test (validator + experience store, CP-SAT),
the one scenario where the weights can matter (confidence penalty needs
learned distrust; regression/budget shape route choice).
Objective (lower is better): mean replans + 3 * (1 - success), averaged over
4 benchmarks. Grid search on TRAIN hazard seeds; the top config and the
defaults are then compared on HELD-OUT seeds so a lucky grid point can't
pass as an improvement.

Usage: python experiments/tune_weights.py
"""
from __future__ import annotations

import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.run_experience_test import run
from tape.scoring import ScoreWeights

BENCHES = ["sokoban-simple", "sokoban-multi", "river-crossing", "rush-hour"]
REG, CONF, BUD = [0.0, 0.75, 1.5, 3.0], [0.0, 2.0, 4.0, 8.0, 16.0], [0.0, 1.0, 2.0, 4.0]
DEFAULT = (1.5, 4.0, 2.0)
EPISODES, FRAC, P, CANDS = 20, 0.25, 0.7, 30


def evaluate(args):
    """-> per-salt objective list for one weight triple over the given salts."""
    (reg, conf, bud), salts = args
    w = ScoreWeights(regression_penalty=reg, confidence_penalty=conf, budget_penalty=bud)
    out = []
    for salt in salts:
        obj = 0.0
        for b in BENCHES:
            eps = run(b, True, salt, EPISODES, FRAC, P, CANDS, weights=w)
            replans = sum(e.replans for e in eps) / len(eps)
            succ = sum(e.success for e in eps) / len(eps)
            obj += (replans + 3 * (1 - succ)) / len(BENCHES)
        out.append(obj)
    return out


def main() -> None:
    train, held = list(range(8)), list(range(100, 116))
    grid = list(itertools.product(REG, CONF, BUD))
    with ProcessPoolExecutor(max_workers=20) as ex:
        res = list(ex.map(evaluate, [(g, train) for g in grid]))
        mean = {g: sum(r) / len(r) for g, r in zip(grid, res)}
        ranked = sorted(grid, key=mean.get)
        top = ranked[:3]
        held_res = dict(zip(top + [DEFAULT], ex.map(evaluate, [(g, held) for g in top + [DEFAULT]])))

    lines = ["# ScoreWeights tuning (objective = replans + 3*(1-success), lower is better)\n",
             f"Grid {len(grid)} points on train seeds {train[0]}..{train[-1]}; held-out seeds {held[0]}..{held[-1]}.\n",
             "## Top 5 on train\n", "| regression | confidence | budget | train objective |", "|---|---|---|---|"]
    lines += [f"| {g[0]} | {g[1]} | {g[2]} | {mean[g]:.3f} |" for g in ranked[:5]]
    lines += [f"\nDefault {DEFAULT}: train objective {mean[DEFAULT]:.3f} (rank {ranked.index(DEFAULT) + 1}/{len(grid)}); "
              f"worst grid point {mean[ranked[-1]]:.3f}.\n",
              "## Held-out: candidate vs default (paired over seeds; negative diff = candidate better)\n",
              "| regression | confidence | budget | held-out objective | diff vs default (mean +/- SE) |", "|---|---|---|---|---|"]
    dflt = held_res[DEFAULT]
    for g in top:
        d = [a - b for a, b in zip(held_res[g], dflt)]
        m = sum(d) / len(d)
        se = (sum((x - m) ** 2 for x in d) / (len(d) - 1) / len(d)) ** 0.5
        lines.append(f"| {g[0]} | {g[1]} | {g[2]} | {sum(held_res[g])/len(held):.3f} | {m:+.3f} +/- {se:.3f} |")
    lines.append(f"| default {DEFAULT} | | | {sum(dflt)/len(held):.3f} | 0 |")
    (ROOT / "results").mkdir(exist_ok=True)
    text = "\n".join(lines) + "\n"
    (ROOT / "results" / "weight_tuning.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
