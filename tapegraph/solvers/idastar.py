from __future__ import annotations

import time

from ..problem import INF, fail, make_result

_FOUND = -1.0


class _Limit(Exception):
    pass


def solve(problem, start, budget=INF, max_nodes=2_000_000):
    """IDA* with a per-iteration transposition table (state -> best g seen this iteration)."""
    t0 = time.perf_counter()
    if problem.prune(start):
        return fail("no_path", 0, t0)
    nodes = 0
    acts = []
    bound = problem.h(start)

    def dfs(s, g, seen):
        nonlocal nodes
        f = g + problem.h(s)
        if f > bound:
            return f
        if problem.is_goal(s):
            return _FOUND
        nodes += 1
        if nodes > max_nodes:
            raise _Limit
        low = INF
        for a, s2, c in problem.neighbors(s):
            if problem.prune(s2):
                continue
            g2 = g + c
            if seen.get(s2, INF) <= g2:
                continue
            seen[s2] = g2
            acts.append(a)
            r = dfs(s2, g2, seen)
            if r == _FOUND:
                return _FOUND
            acts.pop()
            low = min(low, r)
        return low

    try:
        while bound <= budget:
            r = dfs(start, 0.0, {start: 0.0})
            if r == _FOUND:
                return make_result(problem, start, list(acts), nodes, t0)
            if r == INF:
                break
            bound = r
    except _Limit:
        return fail("node_limit", nodes, t0)
    return fail("no_path", nodes, t0)
