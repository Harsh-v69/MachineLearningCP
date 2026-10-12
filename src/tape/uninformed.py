"""Uninformed proposers, for comparison with weighted A* and the meet in the
middle search.

BFS  finds a shortest plan, but its frontier grows as branching ** depth.
DFS  (depth limited, never revisits a state) is complete only for a fixed
     depth, which is exactly Peg Solitaire's case: every solution is 31
     jumps, so there is no shorter plan to miss.

Both take a node budget and an optional validator that prunes rejected moves,
the same way the other proposers do. `expansions` counts states taken off
the frontier.
"""
from __future__ import annotations

from collections import deque


class BFSProposer:
    def __init__(self, node_budget: int = 100_000, validator=None):
        self.node_budget, self.validator = node_budget, validator
        self.expansions = 0

    def generate_candidate_plans(self, level, state, n, max_depth):
        self.expansions = 0
        frontier, seen = deque([(state, ())]), {state}
        while frontier and self.expansions < self.node_budget:
            cur, path = frontier.popleft()
            self.expansions += 1
            if level.is_goal(cur):
                return [list(path)]
            if len(path) >= max_depth:
                continue
            for a in level.ACTIONS:
                nxt, moved = level.step(cur, a)
                if not moved or nxt in seen:
                    continue
                if self.validator and not self.validator.validate(level, cur, a, nxt).accept:
                    continue
                seen.add(nxt)
                frontier.append((nxt, path + (a,)))
        return []


class DFSProposer:
    def __init__(self, node_budget: int = 100_000, validator=None):
        self.node_budget, self.validator = node_budget, validator
        self.expansions = 0

    def generate_candidate_plans(self, level, state, n, max_depth):
        self.expansions = 0
        seen = {state}
        stack = [(state, iter(level.ACTIONS))]
        path: list[str] = []
        while stack and self.expansions < self.node_budget:
            cur, actions = stack[-1]
            if level.is_goal(cur):
                return [path[:]]
            if len(path) >= max_depth:
                stack.pop()
                path and path.pop()
                continue
            for a in actions:
                nxt, moved = level.step(cur, a)
                if not moved or nxt in seen:
                    continue
                if self.validator and not self.validator.validate(level, cur, a, nxt).accept:
                    continue
                seen.add(nxt)
                self.expansions += 1
                path.append(a)
                stack.append((nxt, iter(level.ACTIONS)))
                break
            else:
                stack.pop()
                path and path.pop()
        return []
