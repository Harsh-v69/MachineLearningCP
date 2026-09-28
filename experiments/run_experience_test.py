"""Phase 6: does the experience store (Phase 3) help when failures are
state-dependent? The uniform-slip ablation gave it nothing to learn.

Here a fixed pseudo-random ~`hazard_frac` of (state, action) pairs are
"hazards" that slip with prob `hazard_p`; all other transitions never slip.
Same validator in both arms; only the store differs. The store persists
across episodes within a run, so we compare early vs late episodes: if it
learns, late replans should drop, and only in the store arm.

Usage: python experiments/run_experience_test.py --runs 10 --episodes 40
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.run_ablation import BENCHMARKS
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import MockLLMClient


def make_slip_fn(salt: int, hazard_frac: float, hazard_p: float):
    def slip(state, action) -> float:
        h = hashlib.md5(f"{salt}|{state!r}|{action}".encode()).digest()[0] / 255
        return hazard_p if h < hazard_frac else 0.0
    return slip


def run(bench: str, use_exp: bool, salt: int, episodes: int, frac: float, p: float, cands: int) -> list:
    level, vfactory, depth = BENCHMARKS[bench]
    validator = vfactory()
    store = ExperienceStore() if use_exp else None
    slip = make_slip_fn(salt, frac, p)
    rng = random.Random(salt)
    return [run_episode(level, MockLLMClient(seed=i, validator=validator), n_candidates=cands,
                        max_depth=depth, max_replans=8, rng=rng, validator=validator,
                        experience=store, level_id=bench, path_selection="cp_sat",
                        slip_fn=slip) for i in range(episodes)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--frac", type=float, default=0.25)
    ap.add_argument("--candidates", type=int, default=30)
    ap.add_argument("--p", type=float, default=0.7)
    ap.add_argument("--benchmarks", nargs="+", default=["sokoban-simple", "sokoban-multi", "river-crossing", "rush-hour"])
    a = ap.parse_args()
    half = a.episodes // 2
    lines = [f"# Experience store under state-dependent slip (hazard_frac={a.frac}, hazard_p={a.p}, candidates={a.candidates}, "
             f"{a.runs} runs x {a.episodes} episodes)\n",
             "Mean replans/episode, early half vs late half; success over all episodes.\n",
             "| benchmark | arm | replans early | replans late | success |", "|---|---|---|---|---|"]
    lines[-2:] = ["| benchmark | arm | replans early | replans late | success |", "|---|---|---|---|---|"]
    diffs = ["", "Paired difference (+experience minus validator only), same hazards and seeds per run; negative = store helps.\n",
             "| benchmark | late-replans diff (mean +/- SE) | success diff | runs |", "|---|---|---|---|"]
    for bench in a.benchmarks:
        stats = {}
        for use_exp in (False, True):
            stats[use_exp] = []
            for salt in range(a.runs):
                eps = run(bench, use_exp, salt, a.episodes, a.frac, a.p, a.candidates)
                stats[use_exp].append((sum(e.replans for e in eps[:half]) / half,
                                       sum(e.replans for e in eps[half:]) / (a.episodes - half),
                                       sum(e.success for e in eps) / a.episodes))
            m = [sum(r[i] for r in stats[use_exp]) / a.runs for i in range(3)]
            lines.append(f"| {bench} | {'+experience' if use_exp else 'validator only'} | "
                         f"{m[0]:.2f} | {m[1]:.2f} | {m[2]:.0%} |")
            print(lines[-1], flush=True)
        d = [e[1] - v[1] for v, e in zip(stats[False], stats[True])]
        ds = [e[2] - v[2] for v, e in zip(stats[False], stats[True])]
        mean = sum(d) / len(d)
        se = (sum((x - mean) ** 2 for x in d) / (len(d) - 1) / len(d)) ** 0.5
        diffs.append(f"| {bench} | {mean:+.2f} +/- {se:.2f} | {sum(ds)/len(ds):+.1%} | {a.runs} |")
        print(diffs[-1], flush=True)
    lines += diffs
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "experience_test.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
