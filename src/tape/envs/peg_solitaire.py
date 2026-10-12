"""English peg solitaire: 33 holes in a cross, 32 pegs, centre hole empty.

A move jumps a peg over an orthogonal neighbour peg into the empty hole
behind it and removes the jumped peg. The classic goal is a single peg
left in the centre. Every legal move removes exactly one peg, so every
solution is 31 moves long; the difficulty is not length but dead ends.

State is a 33-bit integer (bit i set = peg in cell i), which keeps search
fast and states hashable. Actions are named "<row><col><dir>" for the peg
that jumps, for example "13D" (row 1, column 3, jumps down).
"""
from __future__ import annotations

_CELLS = [(r, c) for r in range(7) for c in range(7) if 2 <= r <= 4 or 2 <= c <= 4]
_INDEX = {p: i for i, p in enumerate(_CELLS)}
_DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
CENTER = (3, 3)


class PegSolitaireLevel:
    def __init__(self):
        self.cells = _CELLS
        self.center = _INDEX[CENTER]
        self.full = (1 << len(_CELLS)) - 1
        self.jumps: list[tuple[int, int, int]] = []  # (from, over, to) cell indices
        self._moves: dict[str, tuple[int, int, int]] = {}  # action -> masks
        for (r, c), i in _INDEX.items():
            for d, (dr, dc) in _DIRS.items():
                over, to = (r + dr, c + dc), (r + 2 * dr, c + 2 * dc)
                if over in _INDEX and to in _INDEX:
                    self.jumps.append((i, _INDEX[over], _INDEX[to]))
                    self._moves[f"{r}{c}{d}"] = (1 << i, 1 << _INDEX[over], 1 << _INDEX[to])
        self.ACTIONS = tuple(self._moves)
        self.initial_state: int = self.full & ~(1 << self.center)
        self._goal = 1 << self.center
        self._dist = {1 << i: abs(r - CENTER[0]) + abs(c - CENTER[1]) for (r, c), i in _INDEX.items()}

    def step(self, state: int, action: str) -> tuple[int, bool]:
        m = self._moves.get(action)
        if m is None:
            return state, False
        f, o, t = m
        if state & f and state & o and not state & t:
            return (state & ~(f | o)) | t, True
        return state, False

    def is_goal(self, state: int) -> bool:
        return state == self._goal

    def heuristic(self, state: int) -> int:
        """Sum of Manhattan distances of every peg to the centre: 0 only
        when the lone peg sits in the centre."""
        h = 0
        while state:
            low = state & -state
            h += self._dist[low]
            state ^= low
        return h

    def complexity(self, state: int) -> int:
        return bin(state).count("1")

    def pegs(self, state: int) -> list[tuple[int, int]]:
        return [p for p, i in _INDEX.items() if state >> i & 1]

    def from_pegs(self, pegs) -> int:
        return sum(1 << _INDEX[tuple(p)] for p in pegs)

    def render(self, state: int) -> str:
        rows = []
        for r in range(7):
            rows.append("".join(
                " " if (r, c) not in _INDEX else ("o" if state >> _INDEX[(r, c)] & 1 else ".") for c in range(7)))
        return "\n".join(rows)


LEVEL_CLASSIC = PegSolitaireLevel()
