"""Phase 4: a per-transition reachability/utility score.

Phase 2's validator asks a binary-ish question: is this transition legal
by domain rules (yes, no, or uncertain)? Phase 4 asks a different,
continuous question: given the transitions we DO trust, how promising is
each one -- how much closer does it get us to the goal, how much of the
planning budget has it used, and how confident are we in it (folding in
Phase 2/3's confidence)?

The combined score becomes each edge's cost in the plan graph, so the
same CP-SAT solver from Phase 1 (still completely unmodified) naturally
prefers paths that make real progress toward the goal, stay within
budget, and are well-trusted, instead of every legal/trusted edge simply
costing a flat 1. Phase 5 will reuse this same score as an A* heuristic.
"""
from __future__ import annotations

from dataclasses import dataclass

from tape.env_base import Environment, State


@dataclass
class ScoreWeights:
    step: float = 1.0
    regression_penalty: float = 1.5  # per unit of goal-distance regression
    confidence_penalty: float = 4.0  # scaled by (1 - confidence)
    budget_penalty: float = 2.0  # scaled by (fraction of max_depth used) squared


@dataclass
class TransitionScore:
    goal_distance_before: int
    goal_distance_after: int
    regression: int  # > 0 means this move increased distance to the goal
    budget_used_fraction: float
    confidence: float
    cost: int  # combined edge weight (integer -- CP-SAT requires integer coefficients)


def goal_distance(level: Environment, state: State) -> int:
    """Back-compat wrapper: every environment now owns its own heuristic
    (Sokoban's is Manhattan distance of boxes to goals; other benchmarks
    define their own notion of "distance to solved")."""
    return level.heuristic(state)


def score_transition(
    level: Environment,
    from_state: State,
    to_state: State,
    step_index: int,
    max_depth: int,
    confidence: float,
    weights: ScoreWeights = ScoreWeights(),
) -> TransitionScore:
    before = level.heuristic(from_state)
    after = level.heuristic(to_state)
    regression = max(0, after - before)
    budget_used_fraction = min(1.0, (step_index + 1) / max_depth) if max_depth > 0 else 1.0

    raw_cost = (
        weights.step
        + weights.regression_penalty * regression
        + weights.confidence_penalty * (1.0 - confidence)
        + weights.budget_penalty * (budget_used_fraction ** 2)
    )
    # CP-SAT coefficients must be integers; scale by 10 to keep one decimal
    # of resolution instead of collapsing every fractional cost to 1.
    cost = max(1, round(raw_cost * 10))

    return TransitionScore(
        goal_distance_before=before,
        goal_distance_after=after,
        regression=regression,
        budget_used_fraction=budget_used_fraction,
        confidence=confidence,
        cost=cost,
    )
