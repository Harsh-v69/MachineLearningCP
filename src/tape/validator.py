"""Phase 2: validate a proposed transition against domain rules the raw
environment step doesn't enforce, before it's accepted into the plan graph.

`level.step()` only enforces physical legality (no walls, no double boxes).
It happily reports success for a push that wedges a box into a corner off
any goal -- a state no sequence of further moves can ever fix. TAPE's own
gap analysis is exactly this: "plan-graph accuracy still depends on the LM
correctly structuring... states", i.e. a structurally legal transition can
still be a planning error the baseline only discovers much later (or not at
all, if the solver just fails to find a path). A validator that rejects
these outright, and flags merely-suspicious ones with lower confidence
instead of a hard reject, is Phase 2's contribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tape.envs.sokoban import SokobanLevel, State


@dataclass
class ValidationResult:
    accept: bool
    confidence: float  # meaningful only when accept=True; 1.0 = fully trusted
    reason: str


class GraphValidator(Protocol):
    def validate(
        self, level: SokobanLevel, from_state: State, action: str, to_state: State
    ) -> ValidationResult: ...


def _is_corner(level: SokobanLevel, pos: tuple[int, int]) -> bool:
    r, c = pos
    vertical_wall = (r - 1, c) in level.walls or (r + 1, c) in level.walls
    horizontal_wall = (r, c - 1) in level.walls or (r, c + 1) in level.walls
    return vertical_wall and horizontal_wall


def _against_wall(level: SokobanLevel, pos: tuple[int, int]) -> bool:
    r, c = pos
    return any(
        n in level.walls for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
    )


class CornerDeadlockValidator:
    """Rejects transitions that push a box into a corner off any goal
    (unrecoverable). Flags a box merely resting against one wall, off any
    goal, as uncertain rather than rejecting it outright -- it may or may
    not still be solvable depending on the rest of the level."""

    def validate(
        self, level: SokobanLevel, from_state: State, action: str, to_state: State
    ) -> ValidationResult:
        moved_boxes = to_state.boxes - from_state.boxes
        for box in moved_boxes:
            if box in level.goals:
                continue
            if _is_corner(level, box):
                return ValidationResult(
                    accept=False, confidence=0.0, reason="corner deadlock"
                )
            if _against_wall(level, box):
                return ValidationResult(
                    accept=True, confidence=0.5, reason="box against wall, unverified"
                )
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
