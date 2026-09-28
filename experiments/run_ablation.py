"""Phase 6: ablation study. Every combination of component x benchmark x
LLM condition, N episodes each, results written to results/ablation.{csv,md}.

Components toggled (cumulative story + one isolated):
  baseline      original TAPE: CP-SAT, no validator, no experience
  +validator    Phase 2 domain validator
  +val+exp      + Phase 3 experience store
  +adaptive     Phase 5 A*/CP-SAT selection only (no validator)
  full          validator + experience + adaptive

LLM conditions: "goal-biased" mock (plausible-but-imperfect planner) and
"adversarial" (uniform-random moves, a worst-case stand-in).
Slip probability makes the environment unreliable so replans/experience matter.

Usage: python experiments/run_ablation.py --episodes 40
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tape.envs.river_crossing import LEVEL_CLASSIC as RIVER
from tape.envs.river_crossing_validator import RiverSafetyValidator
from tape.envs.rush_hour import LEVEL_CLASSIC as RUSH
from tape.envs.rush_hour_validator import RowGridlockValidator
from tape.envs.sokoban import LEVEL_HARD, LEVEL_MULTI, LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import AdversarialMockLLMClient, MockLLMClient
from tape.validator import CornerDeadlockValidator

# name -> (level, validator factory, max_depth)
BENCHMARKS = {
    "sokoban-trivial": (LEVEL_TRIVIAL, CornerDeadlockValidator, 15),
    "sokoban-simple": (LEVEL_SIMPLE, CornerDeadlockValidator, 15),
    "sokoban-multi": (LEVEL_MULTI, CornerDeadlockValidator, 20),
    "sokoban-hard": (LEVEL_HARD, CornerDeadlockValidator, 40),
    "river-crossing": (RIVER, RiverSafetyValidator, 20),
    "rush-hour": (RUSH, RowGridlockValidator, 20),
}
# name -> (use_validator, use_experience, path_selection)
CONFIGS = {
    "baseline": (False, False, "cp_sat"),
    "+validator": (True, False, "cp_sat"),
    "+val+exp": (True, True, "cp_sat"),
    "+adaptive": (False, False, "adaptive"),
    "full": (True, True, "adaptive"),
}
LLMS = ("goal-biased", "adversarial")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def run_cell(bench: str, cfg: str, llm_kind: str, episodes: int, slip: float) -> dict:
    level, vfactory, depth = BENCHMARKS[bench]
    use_val, use_exp, sel = CONFIGS[cfg]
    validator = vfactory() if use_val else None
    experience = ExperienceStore() if use_exp else None
    rng = random.Random(0)
    cands = 60 if llm_kind == "adversarial" else 8
    eps = []
    for i in range(episodes):
        llm = (AdversarialMockLLMClient(seed=i) if llm_kind == "adversarial"
               else MockLLMClient(seed=i, validator=validator))
        eps.append(run_episode(level, llm, n_candidates=cands, max_depth=depth, max_replans=5,
                               slip_prob=slip, rng=rng, validator=validator, experience=experience,
                               level_id=bench, path_selection=sel, auditor=vfactory()))
    # "safe success" = reached the goal without ever executing a move the
    # domain auditor rejects, regardless of whether this config used a validator.
    n, k = len(eps), sum(e.success and e.audit_violations == 0 for e in eps)
    lo, hi = wilson(k, n)
    raw = sum(e.success for e in eps) / n
    wins = [e for e in eps if e.success and e.audit_violations == 0]
    return {
        "benchmark": bench, "llm": llm_kind, "config": cfg, "n": n,
        "success": k / n, "raw_success": raw, "ci_lo": lo, "ci_hi": hi,
        "replans": sum(e.replans for e in eps) / n,
        "invalid_rate": sum(e.invalid_transition_rate for e in eps) / n,
        "actions_when_solved": (sum(e.total_actions for e in wins) / len(wins)) if wins else float("nan"),
        "plan_ms": 1000 * sum(e.planning_time_s for e in eps) / n,
    }


def to_markdown(rows: list[dict], slip: float, episodes: int) -> str:
    out = [f"# Phase 6 ablation (episodes/cell={episodes}, slip={slip})\n",
           "Safe success = goal reached AND no executed move rejected by an independent domain auditor (raw = goal reached at all), shown with a 95% Wilson interval. `actions` = mean actions in solved episodes.\n"]
    for llm in LLMS:
        out.append(f"\n## LLM condition: {llm}\n")
        out.append("| benchmark | config | safe success [95% CI] | raw | replans | invalid rate | actions | plan ms |")
        out.append("|---|---|---|---|---|---|---|---|")
        for r in (r for r in rows if r["llm"] == llm):
            out.append(f"| {r['benchmark']} | {r['config']} | {r['success']:.0%} "
                       f"[{r['ci_lo']:.0%}, {r['ci_hi']:.0%}] | {r['raw_success']:.0%} | {r['replans']:.2f} | "
                       f"{r['invalid_rate']:.1%} | {r['actions_when_solved']:.1f} | {r['plan_ms']:.1f} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--slip", type=float, default=0.15)
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    rows = []
    for llm in LLMS:
        for bench in BENCHMARKS:
            for cfg in CONFIGS:
                r = run_cell(bench, cfg, llm, a.episodes, a.slip)
                rows.append(r)
                print(f"{llm:12} {bench:16} {cfg:11} safe={r['success']:.0%} raw={r['raw_success']:.0%} replans={r['replans']:.2f}", flush=True)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    with open(out / "ablation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out / "ablation.md").write_text(to_markdown(rows, a.slip, a.episodes), encoding="utf-8")
    print(f"\nwrote {out / 'ablation.csv'} and {out / 'ablation.md'}")


if __name__ == "__main__":
    main()
