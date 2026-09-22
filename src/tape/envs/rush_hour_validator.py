"""Phase 2 validator for Rush Hour.

Gridlock here is NOT, in general, locally decidable the way Sokoban's
corner deadlock is: a vehicle that has zero legal moves right now can
still be freed several moves later by some unrelated vehicle elsewhere
on the board moving out of the way first. A naive "is anything stuck"
check would be unsound (it would reject perfectly solvable positions --
Rush Hour puzzles routinely START with the target vehicle blocked) or
would have to run a full search, which defeats the point of a cheap
structural check.

So this validator has two tiers, and is honest about which is which:

  - A hard reject, for the one case that IS provably permanent: a
    "sealed row" containing only horizontal vehicles with zero empty
    cells. Nothing in that row can ever move again -- sliding needs an
    empty cell in the same row, none exists, and none ever can (a
    vertical vehicle could vacate a cell by leaving the row, which is
    exactly why a sealed row must contain ONLY horizontal vehicles).
    This is a genuine certificate, not a guess.
  - A soft "uncertain" flag (lower confidence, not a reject) when the
    target is blocked and its immediate blocker also currently has no
    moves of its own. This is a real signal worth distrusting a little,
    but it is NOT proof of a permanent deadlock -- a third vehicle
    might still free the blocker later.
"""
from __future__ import annotations

from tape.envs.rush_hour import RushHourLevel, State
from tape.validator import ValidationResult


def _row_is_sealed(level: RushHourLevel, state: State, row: int) -> bool:
    occupied = level.occupied_cells(state)
    for col in range(level.width):
        vid = occupied.get((row, col))
        if vid is None:
            return False  # a gap -- something could still slide into or through it
        if level.orientation_of(vid) != "H":
            return False  # a vertical vehicle can vacate its cell by leaving the row
    return True


def _blocking_vehicle(level: RushHourLevel, state: State, row: int, col: int) -> str | None:
    return level.occupied_cells(state).get((row, col))


class RowGridlockValidator:
    def validate(
        self, level: RushHourLevel, from_state: State, action: str, to_state: State
    ) -> ValidationResult:
        if level.is_goal(to_state):
            return ValidationResult(accept=True, confidence=1.0, reason="ok")

        _, target_row, target_col = next(p for p in to_state if p[0] == "X")

        if _row_is_sealed(level, to_state, target_row):
            return ValidationResult(
                accept=False, confidence=0.0,
                reason="target's row is fully sealed by horizontal vehicles, permanently stuck",
            )

        front_col = target_col + level.length_of("X")
        if front_col >= level.width:
            return ValidationResult(accept=True, confidence=1.0, reason="ok")
        blocker = _blocking_vehicle(level, to_state, target_row, front_col)
        if blocker is None:
            return ValidationResult(accept=True, confidence=1.0, reason="ok")

        blocker_stuck = (
            not level.step(to_state, f"{blocker}+")[1]
            and not level.step(to_state, f"{blocker}-")[1]
        )
        if blocker_stuck:
            return ValidationResult(
                accept=True, confidence=0.5,
                reason=f"blocked by {blocker}, which has no immediate move either (unverified if rescuable)",
            )
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
