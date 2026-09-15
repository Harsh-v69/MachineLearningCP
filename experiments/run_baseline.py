"""CLI: run the TAPE baseline (Phase 1) on a Sokoban level.

Usage:
    python experiments/run_baseline.py --level simple --episodes 20 --slip 0.15
    python experiments/run_baseline.py --llm gemini --episodes 5
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tape.envs.sokoban import LEVEL_MULTI, LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import GeminiClient, MockLLMClient
from tape.metrics import aggregate
from tape.validator import CornerDeadlockValidator

LEVELS = {"trivial": LEVEL_TRIVIAL, "simple": LEVEL_SIMPLE, "multi": LEVEL_MULTI}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=LEVELS, default="simple")
    parser.add_argument("--llm", choices=["mock", "gemini"], default="mock")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--max-depth", type=int, default=15)
    parser.add_argument("--max-replans", type=int, default=5)
    parser.add_argument("--slip", type=float, default=0.0, help="probability an action silently fails, forcing a mismatch/replan")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--validator", choices=["none", "corner-deadlock"], default="none", help="Phase 2: reject/downweight structurally unsound transitions before they enter the plan graph")
    parser.add_argument("--experience", action="store_true", help="Phase 3: carry a persistent experience store across all episodes in this run, biasing confidence by past mismatch history (requires --validator)")
    parser.add_argument("--path-selection", choices=["cp_sat", "astar", "adaptive"], default="cp_sat", help="Phase 5: cp_sat (original TAPE solver), astar (Phase 4 score as heuristic), or adaptive (choose per task: astar for single-box, cp_sat for multi-box)")
    args = parser.parse_args()

    level = LEVELS[args.level]
    llm = GeminiClient() if args.llm == "gemini" else MockLLMClient(seed=args.seed)
    rng = random.Random(args.seed)
    validator = CornerDeadlockValidator() if args.validator == "corner-deadlock" else None
    experience = ExperienceStore() if args.experience else None

    episodes = [
        run_episode(
            level,
            llm,
            n_candidates=args.candidates,
            max_depth=args.max_depth,
            max_replans=args.max_replans,
            slip_prob=args.slip,
            rng=rng,
            validator=validator,
            experience=experience,
            level_id=args.level,
            path_selection=args.path_selection,
        )
        for _ in range(args.episodes)
    ]
    print(aggregate(episodes).report())
    methods_used = sorted({m for ep in episodes for m in ep.path_selection_methods})
    print(f"path-selection methods used: {methods_used}")


if __name__ == "__main__":
    main()
