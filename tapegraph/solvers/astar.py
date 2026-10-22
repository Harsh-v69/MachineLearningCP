from __future__ import annotations

import heapq
import itertools
import time

from ..problem import INF, fail, make_result


def solve(problem, start, budget=INF, w=1.0, res_budget=None, max_nodes=2_000_000):
    """A* / weighted A* (w > 1) with optional side-resource budget.

    Graph constraints applied: prune() dead ends, drop nodes with g+h > budget, drop labels whose
    accumulated resource exceeds res_budget. With res_budget the search is label-setting over
    (state, g, resource) with dominance, so it stays exact.
    """
    t0 = time.perf_counter()
    if problem.prune(start):
        return fail("no_path", 0, t0)
    use_res = res_budget is not None
    labels = [(start, 0.0, 0.0, -1, None)]  # (state, g, resource, parent label, action)
    front = {start: [0]}  # non-dominated label ids per state
    dead = set()
    tie = itertools.count()
    heap = [(w * problem.h(start), next(tie), 0)]
    nodes = 0
    while heap:
        _, _, i = heapq.heappop(heap)
        if i in dead:
            continue
        s, g, r, _, _ = labels[i]
        if problem.is_goal(s):
            acts, j = [], i
            while labels[j][3] != -1:
                acts.append(labels[j][4])
                j = labels[j][3]
            return make_result(problem, start, acts[::-1], nodes, t0)
        nodes += 1
        if nodes > max_nodes:
            return fail("node_limit", nodes, t0)
        for a, s2, c in problem.neighbors(s):
            if problem.prune(s2):
                continue
            g2 = g + c
            r2 = r + (problem.res(s, a, s2) if use_res else 0.0)
            h2 = problem.h(s2)
            if g2 + h2 > budget or (use_res and r2 > res_budget):
                continue
            cur = front.get(s2, [])
            if any(labels[j][1] <= g2 and labels[j][2] <= r2 for j in cur):
                continue
            for j in cur:
                if g2 <= labels[j][1] and r2 <= labels[j][2]:
                    dead.add(j)
            labels.append((s2, g2, r2, i, a))
            front[s2] = [j for j in cur if j not in dead] + [len(labels) - 1]
            heapq.heappush(heap, (g2 + w * h2, next(tie), len(labels) - 1))
    return fail("no_path", nodes, t0)
