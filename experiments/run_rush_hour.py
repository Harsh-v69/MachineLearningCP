"""CLI: run the pipeline on Rush Hour, a third benchmark with multi-cell,
oriented pieces instead of Sokoban's single-cell boxes or river
crossing's headcounts.

Usage:
    python experiments/run_rush_hour.py --episodes 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tape.envs.rush_hour import LEVEL_CLASSIC
from tape.envs.rush_hour_validator import RowGridlockValidator
from tape.executor import run_episode
from tape.llm import AdversarialMockLLMClient, MockLLMClient
from tape.metrics import aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--candidates", type=int, default=10)
    parser.add_argument("--max-depth", type=int, default=20)
    parser.add_argument("--llm", choices=["mock", "adversarial"], default="mock")
    parser.add_argument("--path-selection", choices=["cp_sat", "astar", "adaptive"], default="adaptive")
    parser.add_argument("--validator", choices=["none", "row-gridlock"], default="none",
                         help="Phase 2: reject provably-sealed rows, downweight suspicious-but-unproven stuck blockers")
    args = parser.parse_args()

    level = LEVEL_CLASSIC
    validator = RowGridlockValidator() if args.validator == "row-gridlock" else None

    def make_llm(seed: int):
        if args.llm == "adversarial":
            return AdversarialMockLLMClient(seed=seed)
        return MockLLMClient(seed=seed, validator=validator)

    episodes = [
        run_episode(
            level, make_llm(i), n_candidates=args.candidates, max_depth=args.max_depth,
            validator=validator, path_selection=args.path_selection,
        )
        for i in range(args.episodes)
    ]
    print(aggregate(episodes).report())
    methods = sorted({m for ep in episodes for m in ep.path_selection_methods})
    print(f"path-selection methods used: {methods}")


if __name__ == "__main__":
    main()
