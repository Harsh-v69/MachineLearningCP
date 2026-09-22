"""Phase 2 validator for river crossing: the same pattern as Sokoban's
CornerDeadlockValidator, applied to a completely different game. A
transition is physically legal (the boat can always carry however many
people it holds, if available) but may still leave a bank where cannibals
outnumber missionaries -- an unrecoverable, fatal state no future move
can undo, exactly like a box wedged in a corner off any goal.
"""
from __future__ import annotations

from tape.envs.river_crossing import RiverCrossingLevel, RiverState
from tape.validator import ValidationResult


def _unsafe(missionaries: int, cannibals: int) -> bool:
    return missionaries > 0 and cannibals > missionaries


class RiverSafetyValidator:
    """Rejects any transition that leaves cannibals outnumbering
    missionaries on either bank. There is no "uncertain" middle tier here
    (unlike Sokoban's wall-hug case) -- the puzzle's real rule is a hard
    binary safety constraint, not a heuristic guess."""

    def validate(
        self,
        level: RiverCrossingLevel,
        from_state: RiverState,
        action: str,
        to_state: RiverState,
    ) -> ValidationResult:
        right_m = level.n - to_state.missionaries_left
        right_c = level.n - to_state.cannibals_left
        if _unsafe(to_state.missionaries_left, to_state.cannibals_left) or _unsafe(right_m, right_c):
            return ValidationResult(
                accept=False, confidence=0.0, reason="cannibals outnumber missionaries"
            )
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
