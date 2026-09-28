"""LLM-free proposer for levels too big for blind BFS (Boxoban, 4 boxes).

Runs weighted A* (priority = moves so far + w * heuristic) once per weight
under a shared node budget per search. Small w gives short plans but may
run out of budget; large w is nearly greedy and finds a plan fast but a
long one. The plans that finish become the candidates, so the layer
downstream (merge, check, choose) has different-quality plans to combine.

`validator`, if given, prunes successors it rejects during the search,
the way Sokoban solvers prune dead corners. Without it the search is
unaware of the rule.
"""
from __future__ import annotations

import heapq
import itertools

from tape.env_base import Environment, State


class WeightedAStarProposer:
    def __init__(self, weights=(1, 2, 4, 8), node_budget: int = 30_000, validator=None):
        self.weights, self.node_budget, self.validator = weights, node_budget, validator
        self.expansions = 0  # total across all searches of the last call
        self.log: list[tuple[float, int, int | None]] = []  # (weight, expansions used, plan length or None)

    def _search(self, level: Environment, start: State, w: float) -> list[str] | None:
        tie = itertools.count()
        heap = [(w * level.heuristic(start), next(tie), 0, start)]
        came: dict[State, tuple[State, str]] = {}
        best_g = {start: 0}
        closed: set[State] = set()
        expanded = 0
        while heap and expanded < self.node_budget:
            _, _, g, cur = heapq.heappop(heap)
            if cur in closed:
                continue
            closed.add(cur)
            expanded += 1
            if level.is_goal(cur):
                self.expansions += expanded
                actions = []
                while cur != start:
                    cur, a = came[cur]
                    actions.append(a)
                self.log.append((w, expanded, len(actions)))
                return actions[::-1]
            for a in level.ACTIONS:
                nxt, moved = level.step(cur, a)
                if not moved or nxt in closed:
                    continue
                if self.validator and not self.validator.validate(level, cur, a, nxt).accept:
                    continue
                if g + 1 < best_g.get(nxt, 1 << 30):
                    best_g[nxt] = g + 1
                    came[nxt] = (cur, a)
                    heapq.heappush(heap, (g + 1 + w * level.heuristic(nxt), next(tie), g + 1, nxt))
        self.expansions += expanded
        self.log.append((w, expanded, None))
        return None

    def generate_candidate_plans(self, level, state, n, max_depth):
        self.expansions = 0
        self.log = []
        plans = [self._search(level, state, w) for w in self.weights[:n]]
        return [p for p in plans if p is not None and len(p) <= max_depth]
