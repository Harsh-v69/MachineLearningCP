"""Select a feasible path through the plan graph using CP-SAT (TAPE's
solver-based path selection, phrased as a min-cost single-unit flow: send one
unit from `start` to a virtual sink wired to every goal node).
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
from ortools.sat.python import cp_model

from tape.env_base import State
from tape.graph import PlanGraphResult

_SINK = object()


@dataclass
class PlanSolution:
    actions: list[str]
    node_path: list[State]
    cost: int


def select_path(plan_graph: PlanGraphResult) -> PlanSolution | None:
    if not plan_graph.goal_nodes:
        return None

    g = nx.DiGraph()
    g.add_edges_from(plan_graph.graph.edges(data=True))
    for goal in plan_graph.goal_nodes:
        g.add_edge(goal, _SINK, action=None, cost=0)

    model = cp_model.CpModel()
    edge_vars: dict[tuple, cp_model.IntVar] = {}
    for u, v in g.edges:
        edge_vars[(u, v)] = model.NewBoolVar(f"x_{id(u)}_{id(v)}")

    for node in g.nodes:
        out_flow = [edge_vars[(u, v)] for (u, v) in edge_vars if u == node]
        in_flow = [edge_vars[(u, v)] for (u, v) in edge_vars if v == node]
        if node == plan_graph.start:
            net = 1
        elif node is _SINK:
            net = -1
        else:
            net = 0
        model.Add(sum(out_flow) - sum(in_flow) == net)

    model.Minimize(sum(g.edges[u, v]["cost"] * var for (u, v), var in edge_vars.items()))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    chosen = {(u, v) for (u, v), var in edge_vars.items() if solver.Value(var) == 1}
    actions: list[str] = []
    node_path: list[State] = [plan_graph.start]
    cur = plan_graph.start
    cost = 0
    while cur is not _SINK:
        nxt = next((v for (u, v) in chosen if u == cur), None)
        if nxt is None:
            break
        if nxt is _SINK:
            break
        edge_data = g.edges[cur, nxt]
        actions.append(edge_data["action"])
        cost += edge_data["cost"]
        node_path.append(nxt)
        cur = nxt

    return PlanSolution(actions=actions, node_path=node_path, cost=cost)
