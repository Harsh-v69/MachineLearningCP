"""Phase 2 checker for the sliding-tile puzzles: reject any move whose
resulting arrangement can never be solved (parity rule).

Every legal move keeps solvability, so on a solvable start this never fires.
Its job is the unsolvable start: every first move from it is rejected, so a
plan search stops at once instead of spending its whole budget.
"""
from __future__ import annotations

from tape.validator import ValidationResult


class SlidingParityValidator:
    def validate(self, level, from_state, action, to_state) -> ValidationResult:
        if not level.solvable(to_state):
            return ValidationResult(accept=False, confidence=0.0, reason="unsolvable arrangement (parity)")
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
