from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np

from ..problem import INF, Problem

# Corners URF UFL ULB UBR DFR DLF DBL DRB = 0..7. Corner 6 (DBL) is fixed by U, R, F, which removes cube rotations.
# Quarter-turn data: (corner permutation, corner orientation twist).
_QUARTER = {
    "U": ([3, 0, 1, 2, 4, 5, 6, 7], [0] * 8),
    "R": ([4, 1, 2, 0, 7, 5, 6, 3], [2, 0, 0, 1, 1, 0, 0, 2]),
    "F": ([1, 5, 2, 3, 0, 4, 6, 7], [1, 2, 0, 0, 2, 1, 0, 0]),
}
_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "cube2_dist.npy"


def _mul(a, b):
    cp = [a[0][b[0][i]] for i in range(8)]
    co = [(a[1][b[0][i]] + b[1][i]) % 3 for i in range(8)]
    return cp, co


def _moves():
    names, tabs = [], []
    for n, m in _QUARTER.items():
        m2 = _mul(m, m)
        m3 = _mul(m2, m)
        names += [n, n + "2", n + "'"]
        tabs += [m, m2, m3]
    return names, tabs


def _enumerate(start, step):
    idx, lst, q = {start: 0}, [start], deque([start])
    while q:
        x = q.popleft()
        for m in range(9):
            y = step(x, m)
            if y not in idx:
                idx[y] = len(lst)
                lst.append(y)
                q.append(y)
    return idx, lst


def _bfs_1d(table):
    d = np.full(len(table), -1, dtype=np.int16)
    d[0] = 0
    q = deque([0])
    while q:
        x = q.popleft()
        for m in range(table.shape[1]):
            y = table[x, m]
            if d[y] < 0:
                d[y] = d[x] + 1
                q.append(y)
    return d


class Cube2(Problem):
    """2x2x2 cube in half-turn metric. State (perm, twist): corner permutation (5040) x corner twist (729).

    The two coordinates evolve independently under every move, so a pattern database on each coordinate is an
    admissible heuristic (max of the two) and the full 3.67M-state distance table is one vectorised BFS.
    """

    _shared = None

    def __init__(self):
        self.names, mv = _moves()
        pstep = lambda p, m: tuple(p[mv[m][0][i]] for i in range(8))
        tstep = lambda t, m: tuple((t[mv[m][0][i]] + mv[m][1][i]) % 3 for i in range(8))
        pidx, plst = _enumerate(tuple(range(8)), pstep)
        tidx, tlst = _enumerate((0,) * 8, tstep)
        self.PM = np.array([[pidx[pstep(p, m)] for m in range(9)] for p in plst], dtype=np.int32)
        self.TM = np.array([[tidx[tstep(t, m)] for m in range(9)] for t in tlst], dtype=np.int32)
        self.NT = len(tlst)
        self.pdb_perm = _bfs_1d(self.PM)
        self.pdb_twist = _bfs_1d(self.TM)
        self.dist = self._load_or_build()
        self._by_depth = {}

    def _load_or_build(self):
        if _CACHE.exists():
            return np.load(_CACHE)
        NT = self.NT
        dist = np.full(len(self.PM) * NT, -1, dtype=np.int8)
        dist[0] = 0
        frontier, d = np.array([0], dtype=np.int64), 0
        while len(frontier):
            d += 1
            p, t = frontier // NT, frontier % NT
            nxt = np.unique(np.concatenate([self.PM[p, m].astype(np.int64) * NT + self.TM[t, m] for m in range(9)]))
            nxt = nxt[dist[nxt] < 0]
            dist[nxt] = d
            frontier = nxt
        _CACHE.parent.mkdir(exist_ok=True)
        np.save(_CACHE, dist)
        return dist

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def neighbors(self, s):
        p, t = s
        for m, name in enumerate(self.names):
            yield name, (int(self.PM[p, m]), int(self.TM[t, m])), 1.0

    def is_goal(self, s):
        return s == (0, 0)

    def h(self, s):
        return float(max(self.pdb_perm[s[0]], self.pdb_twist[s[1]]))

    def res(self, s, a, s2):
        return 2.0 if a.endswith("2") else 1.0

    def exact_dist(self, s):
        return float(self.dist[s[0] * self.NT + s[1]])

    def random_start(self, rng, depth):
        if depth not in self._by_depth:
            self._by_depth[depth] = np.flatnonzero(self.dist == depth)
        ids = self._by_depth[depth]
        return divmod(int(ids[rng.randrange(len(ids))]), self.NT) if len(ids) else None
