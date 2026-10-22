from __future__ import annotations

from collections import deque

from ..problem import INF, Problem


class River(Problem):
    """Missionaries and cannibals: n of each, boat holds `cap`. State (missionaries_left, cannibals_left, boat) with
    boat 0 = left bank. Goal (0, 0, 1). Moves are reversible, so distances come from one reverse BFS."""

    GOAL = (0, 0, 1)

    def __init__(self, n: int = 8, cap: int = 4):
        self.n, self.cap = n, cap
        self.dist = {self.GOAL: 0}
        q = deque([self.GOAL])
        while q:
            x = q.popleft()
            for _, y, _ in self.neighbors(x):
                if y not in self.dist:
                    self.dist[y] = self.dist[x] + 1
                    q.append(y)

    def _safe(self, m, c):
        return (m == 0 or m >= c) and (self.n - m == 0 or self.n - m >= self.n - c)

    def neighbors(self, s):
        m, c, b = s
        sgn = -1 if b == 0 else 1
        am, ac = (m, c) if b == 0 else (self.n - m, self.n - c)
        for dm in range(min(am, self.cap) + 1):
            for dc in range(min(ac, self.cap - dm) + 1):
                if dm + dc == 0:
                    continue
                t = (m + sgn * dm, c + sgn * dc, 1 - b)
                if self._safe(t[0], t[1]):
                    yield f"{dm}M{dc}C", t, 1.0

    def is_goal(self, s):
        return s == self.GOAL

    def h(self, s):
        m, c, b = s
        left = m + c
        if left == 0:
            return 0.0
        trips = -(-left // self.cap)  # forward crossings needed; each forward trip (but the last) needs a return
        return float(2 * trips - 1 if b == 0 else 2 * trips)

    def res(self, s, a, s2):
        return float(abs(s[0] - s2[0]) + abs(s[1] - s2[1]))  # passengers carried

    def exact_dist(self, s):
        return float(self.dist.get(s, INF))

    def random_start(self, rng, depth):
        cands = sorted(s for s, d in self.dist.items() if d == depth)
        return rng.choice(cands) if cands else None
