"""Rubik's cube, built from geometry instead of hand-typed move tables.

Every sticker is a (cubie position, outward normal) pair. A face turn
rotates the stickers of one outer layer by 90 degrees about an axis, and
the permutation of sticker slots that results is the move. n=3 is the real
cube (about 4.3e19 states); n=2 is the pocket cube (3,674,160 states) and
only uses the U, R and F faces so that one corner stays fixed and "solved"
has a single orientation.

State: a tuple of 6*n*n colours (ints 0..5, the home face of the sticker).
Face order: 0 U, 1 D, 2 F, 3 B, 4 R, 5 L.  Actions: "U", "U'", "U2", ...
"""
from __future__ import annotations

from operator import itemgetter

FACE_ORDER = "UDFBRL"
_FACE = {"U": (1, 1), "D": (1, -1), "F": (2, 1), "B": (2, -1), "R": (0, 1), "L": (0, -1)}  # axis, sign


def _rot90(v, axis):
    """+90 degrees about the +axis (right-hand rule)."""
    x, y, z = v
    if axis == 0:
        return (x, -z, y)
    if axis == 1:
        return (z, y, -x)
    return (-y, x, z)


def _normal_face(normal) -> int:
    axis = next(i for i, c in enumerate(normal) if c)
    sign = normal[axis]
    return FACE_ORDER.index(next(f for f, (a, s) in _FACE.items() if a == axis and s == sign))


class RubiksCube:
    def __init__(self, n: int = 3, start=None):
        if n not in (2, 3):
            raise ValueError("only the 2x2x2 and 3x3x3 cubes are supported")
        self.n = n
        coords = [2 * i - (n - 1) for i in range(n)]
        ext = n - 1
        self.slots: list[tuple[tuple, tuple]] = []  # (cubie position, normal)
        for x in coords:
            for y in coords:
                for z in coords:
                    for axis in range(3):
                        for sign in (1, -1):
                            pos = (x, y, z)
                            if pos[axis] == sign * ext:
                                normal = tuple(sign if i == axis else 0 for i in range(3))
                                self.slots.append((pos, normal))
        self._slot = {s: i for i, s in enumerate(self.slots)}
        self.solved = tuple(_normal_face(nm) for _, nm in self.slots)
        faces = "URF" if n == 2 else "UDFBRL"
        self._perm: dict[str, object] = {}
        self._inverse: dict[str, str] = {}
        for f in faces:
            axis, sign = _FACE[f]
            quarter = self._quarter(axis, sign)
            half = [quarter[quarter[i]] for i in range(len(quarter))]
            ccw = [quarter[half[i]] for i in range(len(quarter))]
            for name, g in ((f, quarter), (f + "2", half), (f + "'", ccw)):
                self._perm[name] = itemgetter(*g)
            self._inverse.update({f: f + "'", f + "'": f, f + "2": f + "2"})
        self.ACTIONS = tuple(self._perm)
        self.initial_state: tuple = tuple(start) if start is not None else self.solved
        self._faces_slots = [[i for i, (_, nm) in enumerate(self.slots) if _normal_face(nm) == f] for f in range(6)]

    def _quarter(self, axis: int, sign: int) -> list[int]:
        """Gather permutation g with new_state[j] = state[g[j]] for a clockwise
        quarter turn of the outer layer on (axis, sign), seen from outside."""
        ext = self.n - 1
        g = list(range(len(self.slots)))
        for i, (pos, normal) in enumerate(self.slots):
            if pos[axis] != sign * ext:
                continue
            p, nm = pos, normal
            # clockwise seen from outside: -90 about +axis for a + face, +90 for a - face
            turns = 3 if sign == 1 else 1
            for _ in range(turns):
                p, nm = _rot90(p, axis), _rot90(nm, axis)
            g[self._slot[(p, nm)]] = i
        return g

    def inverse(self, action: str) -> str:
        return self._inverse[action]

    def with_start(self, start) -> "RubiksCube":
        return RubiksCube(self.n, start)

    def step(self, state, action):
        f = self._perm.get(action)
        if f is None:
            return state, False
        return f(state), True

    def is_goal(self, state) -> bool:
        return all(len({state[i] for i in slots}) == 1 for slots in self._faces_slots)

    def heuristic(self, state) -> int:
        """Stickers that differ from their face's majority colour, in units of 8
        (one turn moves at most 8 stickers off or onto a face of the 3x3)."""
        bad = 0
        for slots in self._faces_slots:
            counts = {}
            for i in slots:
                counts[state[i]] = counts.get(state[i], 0) + 1
            bad += len(slots) - max(counts.values())
        return (bad + 7) // 8

    def complexity(self, state) -> int:
        return 1

    def scramble(self, moves: int, rng) -> tuple:
        state, last = self.solved, None
        for _ in range(moves):
            a = rng.choice([x for x in self.ACTIONS if not last or x[0] != last[0]])
            state, _ = self.step(state, a)
            last = a
        return state

    def net_layout(self) -> list[list[int]]:
        """Per slot: [face, col, row] in that face's own grid as seen from outside."""
        out = []
        for pos, normal in self.slots:
            x, y, z = pos
            f = _normal_face(normal)
            col, row = {0: (x, z), 1: (x, -z), 2: (x, -y), 3: (-x, -y), 4: (-z, -y), 5: (z, -y)}[f]
            out.append([f, (col + self.n - 1) // 2, (row + self.n - 1) // 2])
        return out

    def render(self, state) -> str:
        return "".join(FACE_ORDER[c] for c in state)


CUBE_3 = RubiksCube(3)
CUBE_2 = RubiksCube(2)
