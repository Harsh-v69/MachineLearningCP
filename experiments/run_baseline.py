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

from tape.envs.sokoban import LEVEL_SIMPLE, LEVEL_TRIVIAL
from tape.executor import run_episode
from tape.llm import GeminiClient, MockLLMClient
from tape.metrics import aggregate

LEVELS = {"trivial": LEVEL_TRIVIAL, "simple": LEVEL_SIMPLE}


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
    args = parser.parse_args()

    level = LEVELS[args.level]
    llm = GeminiClient() if args.llm == "gemini" else MockLLMClient(seed=args.seed)
    rng = random.Random(args.seed)

    episodes = [
        run_episode(
            level,
            llm,
            n_candidates=args.candidates,
            max_depth=args.max_depth,
            max_replans=args.max_replans,
            slip_prob=args.slip,
            rng=rng,
        )
        for _ in range(args.episodes)
    ]
    print(aggregate(episodes).report())


if __name__ == "__main__":
    main()
