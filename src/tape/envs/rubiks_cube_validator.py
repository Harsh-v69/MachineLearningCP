"""Phase 2 checker for the Rubik's cube: reject any state outside the set the
face turns can reach.

Face turns keep four invariants of the cubie arrangement, and together they
are exactly the condition for a state to be solvable (3x3x3):
  1. every corner and edge slot holds a real cubie, each exactly once;
  2. corner twists add up to 0 mod 3;
  3. edge flips add up to 0 mod 2;
  4. corners and edges are permuted with the same parity.
For the 2x2x2 (U, R, F turns only) rules 1 and 2 apply, and the fixed corner
must stay home.

A legal move never breaks them, so on a solvable cube this never fires. It
exists for a cube that was taken apart or mis-assembled (a twisted corner):
every first move from it is rejected, so a search stops at once.
"""
from __future__ import annotations

from tape.envs.rubiks_cube import RubiksCube
from tape.validator import ValidationResult


def _parity(perm: list[int]) -> int:
    seen, odd = [False] * len(perm), 0
    for i in range(len(perm)):
        if not seen[i]:
            j, length = i, 0
            while not seen[j]:
                seen[j] = True
                j, length = perm[j], length + 1
            odd += length - 1
    return odd % 2


class CubeSolvabilityValidator:
    def __init__(self, cube: RubiksCube):
        self.n = cube.n
        groups: dict[tuple, list[int]] = {}
        for i, (pos, _) in enumerate(cube.slots):
            groups.setdefault(pos, []).append(i)
        ext = cube.n - 1
        self._corners, self._edges = [], []
        for pos, slots in groups.items():
            extreme = sum(1 for c in pos if abs(c) == ext)
            if extreme == 3:
                by_axis = {next(a for a, c in enumerate(cube.slots[i][1]) if c): i for i in slots}
                sx, sy, sz = (1 if c > 0 else -1 for c in pos)
                order = (by_axis[1], by_axis[0], by_axis[2]) if sx * sy * sz > 0 else (by_axis[1], by_axis[2], by_axis[0])
                self._corners.append(order)
            elif extreme == 2 and cube.n == 3:
                by_axis = {next(a for a, c in enumerate(cube.slots[i][1]) if c): i for i in slots}
                primary = by_axis[1] if 1 in by_axis else by_axis[2]
                self._edges.append((tuple(slots), primary))
        solved = cube.solved
        self._corner_home = {frozenset(solved[i] for i in o): k for k, o in enumerate(self._corners)}
        self._edge_home = {frozenset(solved[i] for i in s): k for k, (s, _) in enumerate(self._edges)}
        self._fixed = None
        if cube.n == 2:  # the corner no allowed turn moves
            self._fixed = next(o for o, (pos, _) in ((c, cube.slots[c[0]]) for c in self._corners) if pos == (-1, -1, -1))
        self._solved = solved

    def solvable(self, state) -> bool:
        twist, perm_c = 0, []
        for order in self._corners:
            k = self._corner_home.get(frozenset(state[i] for i in order))
            if k is None:
                return False
            perm_c.append(k)
            twist += next(j for j, i in enumerate(order) if state[i] in (0, 1))
        if sorted(perm_c) != list(range(len(self._corners))) or twist % 3:
            return False
        if self._fixed and any(state[i] != self._solved[i] for i in self._fixed):
            return False
        if self._edges:
            flip, perm_e = 0, []
            for slots, primary in self._edges:
                colours = [state[i] for i in slots]
                k = self._edge_home.get(frozenset(colours))
                if k is None:
                    return False
                perm_e.append(k)
                ref = next((c for c in colours if c in (0, 1)), None)
                if ref is None:
                    ref = next(c for c in colours if c in (2, 3))
                flip += state[primary] != ref
            if sorted(perm_e) != list(range(len(self._edges))) or flip % 2:
                return False
            if _parity(perm_c) != _parity(perm_e):
                return False
        return True

    def validate(self, level, from_state, action, to_state) -> ValidationResult:
        if not self.solvable(to_state):
            return ValidationResult(accept=False, confidence=0.0, reason="unsolvable cube (invariant broken)")
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
