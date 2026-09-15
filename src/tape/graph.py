"""Merge multiple candidate plans into a single plan graph (TAPE Phase 1).

Each candidate action sequence is simulated step by step from the current
real state. Identical resulting states across different candidates collapse
onto the same graph node (this is the "merging" TAPE describes). A candidate
step that turns out illegal (wall ahead, unpushable box) is simply not added
as an edge -- that candidate's path dead-ends in the graph. There is no
separate validator yet (that's Phase 2); this is exactly the baseline's
"trust the LLM, discover problems structurally" behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from tape.envs.sokoban import SokobanLevel, State


@dataclass
class PlanGraphResult:
    graph: nx.DiGraph
    start: State
    goal_nodes: list[State] = field(default_factory=list)
    attempted_transitions: int = 0
    invalid_transitions: int = 0

    @property
    def invalid_transition_rate(self) -> float:
        if self.attempted_transitions == 0:
            return 0.0
        return self.invalid_transitions / self.attempted_transitions


def build_plan_graph(
    level: SokobanLevel, start: State, candidate_plans: list[list[str]]
) -> PlanGraphResult:
    graph = nx.DiGraph()
    graph.add_node(start)
    result = PlanGraphResult(graph=graph, start=start)

    for plan in candidate_plans:
        cur = start
        for action in plan:
            result.attempted_transitions += 1
            nxt, moved = level.step(cur, action)
            if not moved:
                result.invalid_transitions += 1
                break
            if not graph.has_edge(cur, nxt):
                graph.add_edge(cur, nxt, action=action, cost=1)
            cur = nxt
            if level.is_goal(cur):
                break

    result.goal_nodes = [n for n in graph.nodes if level.is_goal(n)]
    return result
