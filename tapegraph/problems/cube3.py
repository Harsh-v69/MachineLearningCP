from __future__ import annotations

from itertools import permutations, product
from pathlib import Path

import numpy as np

from ..problem import Problem

# Standard cubie model. Corners URF UFL ULB UBR DFR DLF DBL DRB = 0..7; edges UR UF UL UB DR DF DL DB FR FL BL BR = 0..11.
# Quarter turns in "replaced-by" form: (cp, co, ep, eo) with cp[i] = cubie moved into position i and co/eo the twist/flip
# it picks up there (Kociemba's convention: only F and B flip edges).
_FACES = {
    "U": ([3, 0, 1, 2, 4, 5, 6, 7], [0] * 8, [3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11], [0] * 12),
    "D": ([0, 1, 2, 3, 5, 6, 7, 4], [0] * 8, [0, 1, 2, 3, 5, 6, 7, 4, 8, 9, 10, 11], [0] * 12),
    "L": ([0, 2, 6, 3, 4, 1, 5, 7], [0, 1, 2, 0, 0, 2, 1, 0], [0, 1, 10, 3, 4, 5, 9, 7, 8, 2, 6, 11], [0] * 12),
    "R": ([4, 1, 2, 0, 7, 5, 6, 3], [2, 0, 0, 1, 1, 0, 0, 2], [8, 1, 2, 3, 11, 5, 6, 7, 4, 9, 10, 0], [0] * 12),
    "F": ([1, 5, 2, 3, 0, 4, 6, 7], [1, 2, 0, 0, 2, 1, 0, 0], [0, 9, 2, 3, 4, 8, 6, 7, 1, 5, 10, 11],
          [0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0]),
    "B": ([0, 1, 3, 7, 4, 5, 2, 6], [0, 0, 1, 2, 0, 0, 2, 1], [0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7],
          [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1]),
}
NT = 3 ** 7  # corner twist coordinate size; corner index = perm * NT + twist (8! * 3^7 = 88,179,840)
_Q = 1 << 18  # an edge-quad coordinate (4 tracked edges: positions x flips = 11880 * 16 = 190080) fits in 18 bits
_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "cube3_corner_pdb.npy"


def _mul(a, b):
    """Apply b after a (replaced-by composition)."""
    return ([a[0][j] for j in b[0]], [(a[1][j] + o) % 3 for j, o in zip(b[0], b[1])],
            [a[2][j] for j in b[2]], [(a[3][j] + o) % 2 for j, o in zip(b[2], b[3])])


def _moves():
    names, tabs = [], []
    for n, m in _FACES.items():  # order U D L R F B, so the axis of move k is k // 6
        m2 = _mul(m, m)
        names += [n, n + "2", n + "'"]
        tabs += [m, m2, _mul(m2, m)]
    return names, tabs


def _rank(a, n):
    """Lexicographic rank of each row of `a` (distinct values in range(n)) among the k-permutations of range(n)."""
    r = np.zeros(len(a), dtype=np.int64)
    for i in range(a.shape[1]):
        r = r * (n - i) + a[:, i] - (a[:, :i] < a[:, i:i + 1]).sum(1)
    return r


def _tables(mv):
    """Move tables (rows = coordinate, columns = the 18 moves) plus the decoding arrays.

    PM: corner permutation = positions of corners 0..7, ranked (40320). Cubie at position j goes to inv(cp)[j].
    TM: corner twist per position, base 3 over positions 0..6 (2187); position 7 is fixed by the sum.
    QM: an edge quad = positions of 4 tracked edges (ranked, 11880) * 16 + their flips; one table serves every quad.
    """
    inv = [(np.argsort(m[0]), np.argsort(m[2])) for m in mv]
    perm8 = np.array(list(permutations(range(8))), dtype=np.int64)
    twist = np.array(list(product(range(3), repeat=7)), dtype=np.int64)
    twist = np.hstack([twist, (-twist.sum(1) % 3)[:, None]])
    qpos = np.repeat(np.array(list(permutations(range(12), 4)), dtype=np.int64), 16, axis=0)
    qflip = (np.arange(len(qpos))[:, None] >> np.arange(4)) & 1
    w3 = 3 ** np.arange(6, -1, -1)
    PM = np.stack([_rank(ci[perm8], 8) for ci, _ in inv], 1)
    TM = np.stack([((twist[:, m[0]] + m[1]) % 3)[:, :7] @ w3 for m in mv], 1)
    QM = []
    for m, (_, ei) in zip(mv, inv):
        pos = ei[qpos]
        flip = (qflip + np.array(m[3])[pos]) % 2
        QM.append(_rank(pos, 12) * 16 + flip @ (1 << np.arange(4)))
    return PM.astype(np.int32), TM.astype(np.int32), np.stack(QM, 1).astype(np.int32), (perm8, twist, qpos, qflip)


def build_pdb(PM, TM, chunk=1 << 20, block=1 << 23):
    """Distance from index 0 over the product space (PM coordinate) x (TM coordinate), index p * len(TM) + t.

    Layered BFS with no frontier list: layer d is re-read from `dist == d` in blocks of `block` entries and expanded in
    chunks of `chunk` states (memory beyond `dist` <= ~17 * block + ~40 * chunk bytes; duplicate writes are harmless).
    """
    nt = len(TM)
    dist = np.full(len(PM) * nt, -1, dtype=np.int8)
    dist[0] = 0
    PMT, TMT = (np.ascontiguousarray(X.T, dtype=np.int32) for X in (PM, TM))  # row m = move m, contiguous
    d, grew = 0, True
    while grew:
        grew = False
        for lo in range(0, len(dist), block):
            idx = np.flatnonzero(dist[lo:lo + block] == d).astype(np.int32) + lo
            for c in range(0, len(idx), chunk):
                p, t = np.divmod(idx[c:c + chunk], nt)
                for m in range(len(PMT)):
                    y = PMT[m][p] * nt + TMT[m][t]
                    y = y[dist[y] < 0]
                    if len(y):
                        dist[y] = d + 1
                        grew = True
        d += 1
    return dist


def load_or_build(PM, TM, max_depth=11):
    """Corner pattern database, cached in .cache/ (rebuilt when missing, stale or corrupt)."""
    n = len(PM) * len(TM)
    if _CACHE.exists():
        cached = np.load(_CACHE)
        if cached.shape == (n,) and cached.dtype == np.int8 and cached[0] == 0 and cached.max() == max_depth:
            return cached
    dist = build_pdb(PM, TM)
    _CACHE.parent.mkdir(exist_ok=True)
    np.save(_CACHE, dist)
    return dist


class Cube3(Problem):
    """3x3x3 cube in half-turn metric (18 moves, unit cost).

    State: one Python int (hashable, ~36 bytes, so search dictionaries stay small)
        corner << 54 | quad0 << 36 | quad1 << 18 | quad2
    corner = perm * 2187 + twist (the corner pattern-database index); quad k = positions and flips of edges 4k..4k+3.
    Every coordinate evolves independently under a move, so a neighbour is five table lookups (see `_tables`).
    """

    _shared = None

    def __init__(self, pdb=None):
        self.names, mv = _moves()
        self.PM, self.TM, self.QM, self._dec = _tables(mv)
        qid = {tuple(map(int, p)): i for i, p in enumerate(self._dec[2][::16])}  # quad positions -> rank
        self.goal = sum(qid[tuple(range(4 * k, 4 * k + 4))] * 16 << (36 - 18 * k) for k in range(3))
        self._rows = [(n, memoryview(self.PM[:, m].copy()), memoryview(self.TM[:, m].copy()),
                       memoryview(self.QM[:, m].copy())) for m, n in enumerate(self.names)]
        # pdb: anything indexable by corner index; tests pass a small stand-in instead of the 88M-entry table
        self.pdb = memoryview(load_or_build(self.PM, self.TM)) if pdb is None else pdb

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def neighbors(self, s):
        q0, q1, q2 = (s >> 36) & (_Q - 1), (s >> 18) & (_Q - 1), s & (_Q - 1)
        p, t = divmod(s >> 54, NT)
        for name, P, T, Q in self._rows:
            yield name, (P[p] * NT + T[t]) << 54 | Q[q0] << 36 | Q[q1] << 18 | Q[q2], 1.0

    def is_goal(self, s):
        return s == self.goal

    def h(self, s):
        return float(self.pdb[s >> 54])

    def res(self, s, a, s2):
        return 2.0 if a.endswith("2") else 1.0

    def res_bind(self, s, a, s2):
        """Binding experiment: count half-turns only (quarter-turns free), as for cube2."""
        return 1.0 if a.endswith("2") else 0.0

    def decode(self, s):
        """(cp, co, ep, eo) in replaced-by form (cubie / twist / flip at each position)."""
        perm8, twist, qpos, qflip = self._dec
        p, t = divmod(s >> 54, NT)
        cp = [0] * 8
        for c, j in enumerate(perm8[p]):
            cp[j] = c
        ep, eo = [0] * 12, [0] * 12
        for k in range(3):
            q = (s >> (36 - 18 * k)) & (_Q - 1)
            for i in range(4):
                ep[qpos[q, i]], eo[qpos[q, i]] = 4 * k + i, int(qflip[q, i])
        return cp, twist[t].tolist(), ep, eo

    def random_start(self, rng, depth):
        """Random walk of `depth` moves; consecutive moves never share an axis (no reversals or same-axis repeats),
        so T* <= depth. T* itself comes from the Oracle."""
        s, axis = self.goal, None
        for _ in range(depth):
            m = rng.choice([k for k in range(18) if k // 6 != axis])
            axis = m // 6
            s = list(self.neighbors(s))[m][1]
        return s
