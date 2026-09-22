"""The generic environment interface every benchmark implements.

Nothing in the plan graph, validator protocol, scoring, solver, or
adaptive path selection is Sokoban-specific -- they only ever call
`step`, `is_goal`, `heuristic`, `complexity`, and `ACTIONS`. Any class
implementing this protocol drops into the exact same pipeline (Phases
1-5) unchanged. Sokoban, river crossing, and Rush Hour are three
implementations; a fourth benchmark needs only this interface, not a
pipeline change.
"""
from __future__ import annotations

from typing import Hashable, Protocol

State = Hashable


class Environment(Protocol):
    ACTIONS: tuple[str, ...]

    def step(self, state: State, action: str) -> tuple[State, bool]:
        """Apply `action`. Returns (next_state, True) if legal, or
        (state, False) unchanged if not -- illegal moves are data, not
        exceptions, so a validator or graph builder can react to them."""
        ...

    def is_goal(self, state: State) -> bool: ...

    def heuristic(self, state: State) -> int:
        """A rough, non-negative "distance to solved" estimate, 0 at the
        goal. Used both as the A* heuristic (Phase 5) and as the
        regression signal in Phase 4's cost function."""
        ...

    def complexity(self, state: State) -> int:
        """How many independently-movable pieces this puzzle instance
        has (Sokoban: boxes; Rush Hour: vehicles; river crossing: 1, since
        people only ever move via the single boat). Phase 5's adaptive
        rule routes complexity > 1 to CP-SAT (joint constraints) and
        complexity <= 1 to A* (a pure shortest-path problem)."""
        ...

    def render(self, state: State) -> str: ...
