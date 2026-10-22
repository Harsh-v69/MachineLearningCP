from __future__ import annotations

from .problem import INF
from .solvers import astar


class Oracle:
    """Exact distance-to-goal for the simulated baselines. Cached; search limit hits count as unreachable.

    ponytail: assumes unit edge cost (dist == path length) and treats a max_nodes hit as INF.
    """

    def __init__(self, problem, max_nodes: int = 300_000):
        self.p = problem
        self.max_nodes = max_nodes
        self._d = {}
        self._a = {}
        self._exact = getattr(problem, "exact_dist", None)

    def dist(self, s) -> float:
        if self._exact:
            return self._exact(s)
        if s in self._d:
            return self._d[s]
        if self.p.prune(s):
            self._d[s] = INF
            return INF
        r = astar.solve(self.p, s, max_nodes=self.max_nodes)
        if r.status != "ok":
            self._d[s] = INF
            return INF
        n = len(r.path)
        for i, st in enumerate(r.states):  # suffixes of an optimal path are optimal
            self._d[st] = n - i
            if i < n:
                self._a[st] = r.path[i]
        return n

    def best_action(self, s):
        d = self.dist(s)
        if d == 0 or d == INF:
            return None
        if self._exact:
            for a, s2, _ in self.p.neighbors(s):
                if self._exact(s2) == d - 1:
                    return a
            return None
        return self._a.get(s)

    def viable(self, s, rem):
        return [a for a, s2, _ in self.p.neighbors(s) if self.dist(s2) <= rem - 1]
