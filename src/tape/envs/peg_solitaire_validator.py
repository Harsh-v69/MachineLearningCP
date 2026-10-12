"""Phase 2 checker for peg solitaire.

Hard reject (provable): pagoda functions. A pagoda is a weight w(p) >= 0 per
hole with w(a) + w(b) >= w(c) for every jump a over b into c. A jump removes
pegs at a and b and adds one at c, so the total weight of the pegs never
rises. The goal (one peg in the centre) weighs w(centre). If a position's
total is already below that, the goal is unreachable, whatever is played.
The weights are found by a small linear programme (OR-Tools GLOP), and every
inequality is re-checked after solving, so a bad solution cannot slip in.

Soft tier (a guess, not a proof): a peg with no neighbouring peg is accepted
at confidence 0.5. Other pegs may still jump next to it, so it is not
rejected.
"""
from __future__ import annotations

import random

from ortools.linear_solver import pywraplp

from tape.envs.peg_solitaire import PegSolitaireLevel
from tape.validator import ValidationResult

_EPS = 1e-6
_CHUNK = 11  # 33 bits = 3 chunks of 11, so a weight sum is 3 table lookups


def find_pagodas(level: PegSolitaireLevel, count: int = 12, seed: int = 0) -> list[list[float]]:
    rng = random.Random(seed)
    n, found = len(level.cells), []
    for _ in range(count):
        s = pywraplp.Solver.CreateSolver("GLOP")
        w = [s.NumVar(0, 100, f"w{i}") for i in range(n)]
        s.Add(w[level.center] == 1)
        for f, o, t in level.jumps:
            s.Add(w[f] + w[o] - w[t] >= 0)
        s.Minimize(sum(rng.uniform(0.2, 1.0) * v for v in w))
        if s.Solve() != pywraplp.Solver.OPTIMAL:
            continue
        vals = [v.solution_value() for v in w]
        if all(vals[f] + vals[o] >= vals[t] - 1e-9 for f, o, t in level.jumps) and abs(vals[level.center] - 1) < 1e-9:
            found.append(vals)
    return found


class PegPagodaValidator:
    def __init__(self, level: PegSolitaireLevel | None = None, pagodas: int = 12, soft: bool = True):
        from tape.envs.peg_solitaire import LEVEL_CLASSIC
        lv = level or LEVEL_CLASSIC
        self.soft = soft
        self.pagodas = find_pagodas(lv, pagodas)
        self._tables = []  # per pagoda: 3 lookup tables
        for w in self.pagodas:
            tabs = []
            for chunk in range(3):
                tab = [0.0] * (1 << _CHUNK)
                for v in range(1, 1 << _CHUNK):
                    low = v & -v
                    tab[v] = tab[v ^ low] + w[chunk * _CHUNK + low.bit_length() - 1]
                tabs.append(tab)
            self._tables.append(tabs)
        self._nbr = {}
        cells = {p: i for i, p in enumerate(lv.cells)}
        for (r, c), i in cells.items():
            m = 0
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if (r + dr, c + dc) in cells:
                    m |= 1 << cells[(r + dr, c + dc)]
            self._nbr[1 << i] = m

    def weight(self, k: int, state: int) -> float:
        t = self._tables[k]
        mask = (1 << _CHUNK) - 1
        return t[0][state & mask] + t[1][state >> _CHUNK & mask] + t[2][state >> (2 * _CHUNK) & mask]

    def unsolvable(self, state: int) -> bool:
        return any(self.weight(k, state) < 1 - _EPS for k in range(len(self._tables)))

    def validate(self, level, from_state, action, to_state) -> ValidationResult:
        if self.unsolvable(to_state):
            return ValidationResult(accept=False, confidence=0.0, reason="pagoda bound: goal unreachable")
        if self.soft and to_state & (to_state - 1):  # more than one peg
            s = to_state
            while s:
                low = s & -s
                if not to_state & self._nbr[low]:
                    return ValidationResult(accept=True, confidence=0.5, reason="isolated peg, unverified")
                s ^= low
        return ValidationResult(accept=True, confidence=1.0, reason="ok")
