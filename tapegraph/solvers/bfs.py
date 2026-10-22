from __future__ import annotations

import time
from collections import deque

from ..problem import INF, fail, make_result


def solve(problem, start, budget=INF, max_nodes=2_000_000):
    """Plain BFS. Ignores h() and prune() on purpose: it is the independent reference the others are checked against.

    ponytail: assumes unit edge cost; switch to Dijkstra if a benchmark gets non-unit costs.
    """
    t0 = time.perf_counter()
    if problem.is_goal(start):
        return make_result(problem, start, [], 0, t0)
    parent = {start: (None, None)}
    g = {start: 0}
    q = deque([start])
    nodes = 0
    while q:
        u = q.popleft()
        if g[u] >= budget:
            continue
        nodes += 1
        if nodes > max_nodes:
            return fail("node_limit", nodes, t0)
        for a, v, _ in problem.neighbors(u):
            if v in parent:
                continue
            parent[v] = (u, a)
            g[v] = g[u] + 1
            if problem.is_goal(v):
                acts, x = [], v
                while parent[x][0] is not None:
                    acts.append(parent[x][1])
                    x = parent[x][0]
                return make_result(problem, start, acts[::-1], nodes, t0)
            q.append(v)
    return fail("no_path", nodes, t0)
