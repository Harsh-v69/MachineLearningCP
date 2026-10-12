"""The sliding-tile puzzle family: 8-puzzle (n=3), 15-puzzle (n=4) and the
24-puzzle (n=5, about 7.8e24 states).

State is a tuple of n*n ints in row-major order, 0 for the blank. An action
moves the blank: "U", "D", "L", "R". The goal is 1, 2, ..., n*n-1, 0.

Half of all arrangements can never reach the goal. Moves keep an invariant
(the inversion parity, plus the blank's row when n is even), so whether a
position is solvable is decided by that invariant and never changes during
play.
"""
from __future__ import annotations

import random

_DELTA = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


class SlidingPuzzle:
    ACTIONS = ("U", "D", "L", "R")

    def __init__(self, n: int = 5, start=None):
        self.n = n
        self.goal = tuple(list(range(1, n * n)) + [0])
        self.initial_state = tuple(start) if start is not None else self.goal
        self._to = []  # per blank index: action -> new blank index
        for b in range(n * n):
            r, c = divmod(b, n)
            row = {}
            for a, (dr, dc) in _DELTA.items():
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    row[a] = rr * n + cc
            self._to.append(row)
        goal_pos = {v: divmod(i, n) for i, v in enumerate(self.goal)}
        # manhattan[v][i]: distance of tile v from its home when sitting at index i
        self._man = [[0] * (n * n) for _ in range(n * n)]
        for v in range(1, n * n):
            gr, gc = goal_pos[v]
            for i in range(n * n):
                self._man[v][i] = abs(i // n - gr) + abs(i % n - gc)

    @property
    def solved(self):
        return self.goal

    def inverse(self, action: str) -> str:
        return {"U": "D", "D": "U", "L": "R", "R": "L"}[action]

    def with_start(self, start) -> "SlidingPuzzle":
        return SlidingPuzzle(self.n, start)

    def step(self, state, action):
        b = state.index(0)
        nb = self._to[b].get(action)
        if nb is None:
            return state, False
        s = list(state)
        s[b], s[nb] = s[nb], 0
        return tuple(s), True

    def is_goal(self, state) -> bool:
        return state == self.goal

    def heuristic(self, state) -> int:
        man = self._man
        return sum(man[v][i] for i, v in enumerate(state) if v)

    def complexity(self, state) -> int:
        return 1  # only the blank moves

    def solvable(self, state) -> bool:
        tiles = [v for v in state if v]
        inv = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])
        if self.n % 2:
            return inv % 2 == 0
        blank_row_from_bottom = self.n - state.index(0) // self.n
        return (inv + blank_row_from_bottom) % 2 == 1

    def scramble(self, moves: int, rng: random.Random):
        """A solvable instance: random walk from the goal, never undoing the last move."""
        state, last = self.goal, None
        opposite = {"U": "D", "D": "U", "L": "R", "R": "L"}
        for _ in range(moves):
            choices = [a for a in self.ACTIONS if self.step(state, a)[1] and a != opposite.get(last)]
            last = rng.choice(choices)
            state, _ = self.step(state, last)
        return state

    def unsolvable_twin(self, state):
        """Swap the first two tiles: the classic unsolvable variant."""
        s = list(state)
        i, j = [k for k, v in enumerate(s) if v][:2]
        s[i], s[j] = s[j], s[i]
        return tuple(s)

    def render(self, state) -> str:
        w = len(str(self.n * self.n - 1))
        return "\n".join(" ".join(("." if v == 0 else str(v)).rjust(w) for v in state[r * self.n:(r + 1) * self.n])
                         for r in range(self.n))


LEVEL_24 = SlidingPuzzle(5)
