"""Constrained execution with mismatch-triggered replanning (TAPE Phase 1).

The solved path is executed action-by-action. After each action the real
environment's resulting state is compared against the state the plan graph
predicted; a mismatch (here: simulated by an optional random "slip", since
our Sokoban env is otherwise deterministic) aborts the current plan and
triggers a fresh planning round from the real current state.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from tape.envs.sokoban import SokobanLevel, State
from tape.graph import build_plan_graph
from tape.llm import LLMClient
from tape.solver import select_path


@dataclass
class EpisodeResult:
    success: bool
    total_actions: int = 0
    replans: int = 0
    planning_rounds: int = 0
    planning_time_s: float = 0.0
    attempted_transitions: int = 0
    invalid_transitions: int = 0

    @property
    def invalid_transition_rate(self) -> float:
        if self.attempted_transitions == 0:
            return 0.0
        return self.invalid_transitions / self.attempted_transitions


def run_episode(
    level: SokobanLevel,
    llm: LLMClient,
    start: State | None = None,
    n_candidates: int = 6,
    max_depth: int = 15,
    max_replans: int = 5,
    slip_prob: float = 0.0,
    rng: random.Random | None = None,
) -> EpisodeResult:
    rng = rng or random.Random()
    state = start or level.initial_state
    result = EpisodeResult(success=False)

    for _ in range(max_replans + 1):
        result.planning_rounds += 1
        t0 = time.perf_counter()
        candidates = llm.generate_candidate_plans(level, state, n_candidates, max_depth)
        plan_graph = build_plan_graph(level, state, candidates)
        solution = select_path(plan_graph)
        result.planning_time_s += time.perf_counter() - t0
        result.attempted_transitions += plan_graph.attempted_transitions
        result.invalid_transitions += plan_graph.invalid_transitions

        if solution is None:
            break  # no candidate reached the goal; give up rather than loop forever

        mismatched = False
        for action, predicted_next in zip(solution.actions, solution.node_path[1:]):
            actual_next, moved = level.step(state, action)
            if moved and rng.random() < slip_prob:
                actual_next, moved = state, False  # simulated real-world slip
            result.total_actions += 1
            state = actual_next

            if actual_next != predicted_next:
                mismatched = True
                result.replans += 1
                break
            if level.is_goal(state):
                result.success = True
                break

        if result.success or not mismatched:
            break

    return result
