"""Phase 6: pipeline benefit as a function of proposer quality (no LLM).

For each benchmark and each proposer quality q (fraction of guided vs
random candidates, see tape.llm.QualityProposer), compare:
  baseline  TAPE baseline: plan graph + CP-SAT, no validator/experience
  full      validator + experience store + adaptive solver
under state-dependent slip (25% of transitions slip w.p. 0.7).
Metric: safe success (goal reached, no move rejected by an independent
auditor) and replans. Reported as the paired full-minus-baseline difference
over hazard seeds, with standard error.

Modes: guided (mix of goal-biased/random walks) or corrupt (optimal plan with each step
randomized w.p. 1-quality). Usage: python experiments/run_proposer_sweep.py [guided|corrupt]
"""
from __future__ import annotations

import itertools
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.run_ablation import BENCHMARKS
from experiments.run_experience_test import make_slip_fn
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import QualityProposer

MODE = sys.argv[1] if len(sys.argv) > 1 else "guided"
QUALITIES = [0.0, 0.25, 0.5, 0.75, 1.0] if MODE == "guided" else [0.5, 0.7, 0.8, 0.9, 0.95]
SALTS, EPISODES, CANDS = 10, 20, 30


def cell(args):
    bench, q, cfg, salt = args
    level, vfactory, depth = BENCHMARKS[bench]
    full = cfg == "full"
    validator = vfactory() if full else None
    store = ExperienceStore() if full else None
    slip, rng = make_slip_fn(salt, 0.25, 0.7), random.Random(salt)
    eps = [run_episode(level, QualityProposer(q, seed=salt * 1000 + i, mode=MODE), n_candidates=CANDS,
                       max_depth=depth, max_replans=8, rng=rng, validator=validator,
                       experience=store, level_id=bench, slip_fn=slip, auditor=vfactory(),
                       path_selection="adaptive" if full else "cp_sat")
           for i in range(EPISODES)]
    safe = sum(e.success and e.audit_violations == 0 for e in eps) / EPISODES
    return args, safe, sum(e.replans for e in eps) / EPISODES


def paired(a, b):
    d = [x - y for x, y in zip(a, b)]
    m = sum(d) / len(d)
    se = (sum((x - m) ** 2 for x in d) / (len(d) - 1) / len(d)) ** 0.5
    return m, se


def main() -> None:
    jobs = list(itertools.product(BENCHMARKS, QUALITIES, ["baseline", "full"], range(SALTS)))
    with ProcessPoolExecutor(max_workers=20) as ex:
        res = {a: (s, r) for a, s, r in ex.map(cell, jobs, chunksize=4)}
    lines = [f"# Proposer-quality sweep, mode={MODE} ({SALTS} hazard seeds x {EPISODES} episodes, {CANDS} candidates)\n",
             "Safe success per arm; last two columns are the paired full-minus-baseline difference (mean +/- SE).\n",
             "| benchmark | quality | baseline safe | full safe | safe diff | replans diff |", "|---|---|---|---|---|---|"]
    for b in BENCHMARKS:
        for q in QUALITIES:
            get = lambda cfg, i: [res[(b, q, cfg, s)][i] for s in range(SALTS)]
            sm, sse = paired(get("full", 0), get("baseline", 0))
            rm, rse = paired(get("full", 1), get("baseline", 1))
            lines.append(f"| {b} | {q} | {sum(get('baseline',0))/SALTS:.0%} | {sum(get('full',0))/SALTS:.0%} | "
                         f"{sm:+.1%} +/- {sse:.1%} | {rm:+.2f} +/- {rse:.2f} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"proposer_sweep_{MODE}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
