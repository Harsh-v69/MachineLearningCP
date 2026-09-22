"""Phase 5: adaptive path selection.

TAPE's baseline (and Phases 1-4 above) always resolve the plan graph with
CP-SAT: a real ILP-style solver, but overkill for a graph where a plain
best-first search would find the same answer just as well. TAPE's authors
flag exactly this: the framework depends on one pre-specified solver for
every task, with no way to adapt.

This module adds a second path-selection method, A* using the Phase 4
score as its heuristic, and a `decide_method` rule that picks between the
two based on a property of the task itself, reported by the environment's
own `complexity(state)`: a puzzle with one independently-movable piece
(a single Sokoban box; river crossing's one boat) is just a shortest-path
problem (A* suffices), while more than one (multiple boxes; Rush Hour's
several vehicles) need those pieces coordinated jointly, exactly the kind
of hard, interacting constraint CP-SAT is for. `select_path_adaptive` is
the one entry point that actually chooses.
"""
from __future__ import annotations

import heapq
import itertools

from tape.env_base import Environment, State
from tape.graph import PlanGraphResult
from tape.scoring import goal_distance
from tape.solver import PlanSolution, select_path

ASTAR = "astar"
CP_SAT = "cp_sat"


def astar_select_path(level: Environment, plan_graph: PlanGraphResult) -> PlanSolution | None:
    """A* over the plan graph: g-cost is the sum of edge costs (the same
    Phase 4 scores CP-SAT minimizes), h-cost is `goal_distance` scaled to
    match those costs' units. Finds the same optimal-cost path CP-SAT
    would, without formulating an ILP."""
    goals = set(plan_graph.goal_nodes)
    if not goals:
        return None

    graph = plan_graph.graph
    start = plan_graph.start
    counter = itertools.count()  # tie-breaker so States never get compared

    def h(state: State) -> int:
        return goal_distance(level, state) * 10  # matches scoring.py's ×10 cost scaling

    open_heap: list[tuple[int, int, int, State]] = [(h(start), 0, next(counter), start)]
    best_g = {start: 0}
    came_from: dict[State, tuple[State, str]] = {}
    closed: set[State] = set()

    while open_heap:
        _, g, _, node = heapq.heappop(open_heap)
        if node in closed:
            continue
        closed.add(node)

        if node in goals:
            actions: list[str] = []
            node_path: list[State] = [node]
            while node_path[-1] != start:
                prev, action = came_from[node_path[-1]]
                actions.append(action)
                node_path.append(prev)
            actions.reverse()
            node_path.reverse()
            return PlanSolution(actions=actions, node_path=node_path, cost=g)

        for _, nxt, data in graph.out_edges(node, data=True):
            tentative_g = g + data["cost"]
            if tentative_g < best_g.get(nxt, float("inf")):
                best_g[nxt] = tentative_g
                came_from[nxt] = (node, data["action"])
                heapq.heappush(open_heap, (tentative_g + h(nxt), tentative_g, next(counter), nxt))

    return None


def decide_method(level: Environment, plan_graph: PlanGraphResult) -> str:
    """One independently-movable piece is a pure shortest-path problem;
    A* handles it fine. More than one means their moves have to be
    coordinated jointly (progress on one piece's route can conflict with
    another's), which is exactly the kind of hard combinatorial
    constraint CP-SAT exists for."""
    if level.complexity(plan_graph.start) > 1:
        return CP_SAT
    return ASTAR


def select_path_adaptive(
    level: Environment, plan_graph: PlanGraphResult
) -> tuple[PlanSolution | None, str]:
    method = decide_method(level, plan_graph)
    if method == ASTAR:
        return astar_select_path(level, plan_graph), ASTAR
    return select_path(plan_graph), CP_SAT
