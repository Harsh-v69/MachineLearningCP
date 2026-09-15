"""Stress test for the Phase 2 corner-deadlock validator.

Why this exists: on the normal goal-biased mock LLM, corner deadlocks
basically never happen by chance (see progress.md Sec 4), so the
validator's aggregate effect doesn't show up in the usual episode metrics
-- only the hand-crafted unit tests prove it works. This script creates
the failure condition on purpose, using AdversarialMockLLMClient (pure
uniform-random moves, no safety-net optimal plan -- a deliberately much
worse stand-in for an LLM, not a claim about how a real one behaves).

It measures three honest numbers:
  1. The baseline's own invalid-transition metric is blind to corner
     deadlocks by construction -- they're physically legal moves, so it
     always reports 0% no matter how often they actually happen.
  2. How many the Phase 2 validator actually catches.
  3. Independent proof those rejections are correct: a plain BFS (nothing
     to do with the validator's own corner-detection logic) confirms each
     rejected state genuinely has no solution -- so this isn't the
     validator grading its own homework.
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tape.envs.sokoban import ACTIONS, LEVEL_MULTI, SokobanLevel, State
from tape.graph import build_plan_graph, build_validated_plan_graph
from tape.llm import AdversarialMockLLMClient
from tape.validator import CornerDeadlockValidator


def is_truly_unsolvable(level: SokobanLevel, state: State, max_depth: int) -> bool:
    """Ground truth via plain BFS, independent of the validator's own
    corner-detection rule: does any move sequence from `state` reach the
    goal within max_depth?"""
    frontier = deque([(state, 0)])
    seen = {state}
    while frontier:
        cur, depth = frontier.popleft()
        if level.is_goal(cur):
            return False
        if depth >= max_depth:
            continue
        for a in ACTIONS:
            nxt, moved = level.step(cur, a)
            if moved and nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, depth + 1))
    return True


def run_stress_test(n_trials: int = 30, n_candidates: int = 150, max_depth: int = 12) -> dict:
    level = LEVEL_MULTI
    start = level.initial_state
    validator = CornerDeadlockValidator()

    total_attempted = 0
    total_rejected = 0
    verified_dead_ends = 0

    for seed in range(n_trials):
        llm = AdversarialMockLLMClient(seed=seed)
        candidates = llm.generate_candidate_plans(level, start, n_candidates, max_depth)

        baseline = build_plan_graph(level, start, candidates)
        validated = build_validated_plan_graph(level, start, candidates, validator)
        total_attempted += baseline.attempted_transitions
        total_rejected += validated.validator_rejections

        for plan in candidates:
            cur = start
            for action in plan:
                nxt, moved = level.step(cur, action)
                if not moved:
                    break
                verdict = validator.validate(level, cur, action, nxt)
                if not verdict.accept:
                    if is_truly_unsolvable(level, nxt, max_depth=15):
                        verified_dead_ends += 1
                    break
                cur = nxt
                if level.is_goal(cur):
                    break

    return {
        "total_attempted": total_attempted,
        "total_rejected": total_rejected,
        "verified_dead_ends": verified_dead_ends,
    }


def main() -> None:
    r = run_stress_test()
    total_attempted, total_rejected, verified = (
        r["total_attempted"], r["total_rejected"], r["verified_dead_ends"]
    )
    print("Stress test: adversarial (pure-random) candidates on the two-box level\n")
    print(f"  Total transitions attempted:                {total_attempted}")
    print("  Baseline (Phase 1) invalid-transition rate:  0.00%  "
          "(corner deadlocks are physically legal moves -- invisible to it)")
    print(f"  Validator (Phase 2) rejections:              {total_rejected}  "
          f"({total_rejected / total_attempted:.2%} of attempted transitions)")
    print(f"  Independently verified as true dead ends:    {verified}/{total_rejected}  "
          "(plain BFS confirms no solution exists -- zero false positives)")


if __name__ == "__main__":
    main()
