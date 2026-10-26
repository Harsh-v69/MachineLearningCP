from __future__ import annotations

import time
from collections import defaultdict, deque

from ..problem import INF, fail, make_result

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:  # the rest of the package works without it
    cp_model = None
    ORTOOLS_AVAILABLE = False

SCALE = 1000  # CP-SAT needs integers


class IlpTimeout(Exception):
    """CP-SAT stopped without proving optimality or infeasibility."""


def solve_graph(start, goals, edges, res_budget=None, cost_budget=None, time_limit=10.0):
    """Min-cost start->goal path on an explicit graph as a unit-flow ILP.

    edges: [(u, action, v, cost, res)]. Costs are positive, so the optimum is a simple path.
    """
    if not ORTOOLS_AVAILABLE:
        raise RuntimeError("OR-Tools not available. Install with: pip install ortools")
    out, inn = defaultdict(list), defaultdict(list)
    for i, (u, _, v, _, _) in enumerate(edges):
        out[u].append(i)
        inn[v].append(i)
    nodes = set(out) | set(inn) | {start}
    sinks = [g for g in goals if g in nodes]
    if not sinks:
        return None
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{i}") for i in range(len(edges))]
    z = {g: m.NewBoolVar(f"z{j}") for j, g in enumerate(sinks)}
    m.Add(sum(z.values()) == 1)  # exactly one goal ends the path
    for n in nodes:
        # outflow - inflow = [n is start] - [n is the chosen goal]
        m.Add(sum(x[i] for i in out[n]) - sum(x[i] for i in inn[n]) == (1 if n == start else 0) - z.get(n, 0))
    cost = [int(round(e[3] * SCALE)) for e in edges]
    if cost_budget is not None and cost_budget != INF:
        m.Add(sum(c * xi for c, xi in zip(cost, x)) <= int(round(cost_budget * SCALE)))
    if res_budget is not None:
        m.Add(sum(int(round(e[4] * SCALE)) * xi for e, xi in zip(edges, x)) <= int(round(res_budget * SCALE)))
    m.Minimize(sum(c * xi for c, xi in zip(cost, x)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)
    if status == cp_model.INFEASIBLE:
        return None
    if status != cp_model.OPTIMAL:
        raise IlpTimeout(solver.StatusName(status))
    path, cur, seen = [], start, {start}
    while not (cur in z and solver.Value(z[cur])):
        step = [i for i in out[cur] if solver.Value(x[i])]
        if not step:
            raise IlpTimeout("broken flow")
        u, a, v, _, _ = edges[step[0]]
        path.append((u, a, v))
        cur = v
        if cur in seen:  # only possible for a non-optimal answer
            raise IlpTimeout("cycle in reconstruction")
        seen.add(cur)
    return path


def graph_path_bfs(start, goals, edges):
    """Fewest-edge path on an explicit graph; same return format as solve_graph, no ortools needed."""
    out = defaultdict(list)
    for u, a, v, _, _ in edges:
        out[u].append((a, v))
    parent, q = {start: None}, deque([start])
    while q:
        u = q.popleft()
        if u in goals:
            path, x = [], u
            while parent[x] is not None:
                pu, pa = parent[x]
                path.append((pu, pa, x))
                x = pu
            return path[::-1]
        for a, v in out[u]:
            if v not in parent:
                parent[v] = (u, a)
                q.append(v)
    return None


def solve(problem, start, budget=INF, res_budget=None, max_nodes=200_000, time_limit=10.0):
    """ILP on the bounded subgraph {g + h <= budget}, capped at max_nodes. With budget = T*+slack this ball is larger
    than the f <= T* region A* expands, and it is built without resource pruning.

    ponytail: BFS layering for g assumes unit edge cost.
    """
    t0 = time.perf_counter()
    if problem.is_goal(start):
        return make_result(problem, start, [], 0, t0)
    if problem.prune(start):
        return fail("no_path", 0, t0)
    g = {start: 0}
    edges, q = [], deque([start])
    while q:
        u = q.popleft()
        if problem.is_goal(u):
            continue
        for a, v, c in problem.neighbors(u):
            if problem.prune(v) or g[u] + c + problem.h(v) > budget:
                continue
            edges.append((u, a, v, c, problem.res(u, a, v)))
            if v not in g:
                if len(g) >= max_nodes:
                    return fail("too_large", len(g), t0)
                g[v] = g[u] + c
                q.append(v)
    goals = {u for u in g if problem.is_goal(u)}
    try:
        path = solve_graph(start, goals, edges, res_budget, budget, time_limit) if goals else None
    except IlpTimeout:
        return fail("timeout", len(g), t0)
    if not path:
        return fail("no_path", len(g), t0)
    return make_result(problem, start, [a for _, a, _ in path], len(g), t0)
