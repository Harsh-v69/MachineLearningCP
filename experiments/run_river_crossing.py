"""CLI: run the pipeline on river crossing (missionaries and cannibals),
proof that Phases 1-5 aren't Sokoban-specific.

Usage:
    python experiments/run_river_crossing.py --episodes 20
    python experiments/run_river_crossing.py --llm adversarial --episodes 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tape.envs.river_crossing import LEVEL_CLASSIC
from tape.envs.river_crossing_validator import RiverSafetyValidator
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import AdversarialMockLLMClient, MockLLMClient
from tape.metrics import aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--max-depth", type=int, default=20)
    parser.add_argument("--llm", choices=["mock", "adversarial"], default="mock",
                         help="mock: knows the safety rule (validator-aware). adversarial: pure random, doesn't")
    parser.add_argument("--no-validator", action="store_true", help="disable RiverSafetyValidator entirely")
    parser.add_argument("--experience", action="store_true")
    parser.add_argument("--path-selection", choices=["cp_sat", "astar", "adaptive"], default="adaptive")
    args = parser.parse_args()

    level = LEVEL_CLASSIC
    validator = None if args.no_validator else RiverSafetyValidator()
    experience = ExperienceStore() if args.experience else None

    def make_llm(seed: int):
        if args.llm == "adversarial":
            return AdversarialMockLLMClient(seed=seed)
        return MockLLMClient(seed=seed, validator=validator)

    episodes = [
        run_episode(
            level, make_llm(i), n_candidates=args.candidates, max_depth=args.max_depth,
            validator=validator, experience=experience, level_id="river",
            path_selection=args.path_selection,
        )
        for i in range(args.episodes)
    ]
    print(aggregate(episodes).report())
    methods = sorted({m for ep in episodes for m in ep.path_selection_methods})
    print(f"path-selection methods used: {methods}")


if __name__ == "__main__":
    main()
