"""LLM-free proposer for puzzles with reversible moves and one solved state
(Rubik's cube): breadth-first search from the start and from the solved
state at the same time, meeting in the middle. Depth d costs about the work
of depth d/2 on each side.

The plans it returns are all shortest solutions through different meeting
states, so the plan graph has several routes that share their ends.

`validator`, if given, is applied to every forward move (for the backward
side, to the forward move that the backward step reverses). A start from
which every move is rejected makes the forward side run dry at once, and the
search stops with no plan instead of using up its budget.
"""
from __future__ import annotations


class BidirectionalProposer:
    def __init__(self, node_budget: int = 200_000, validator=None):
        self.node_budget, self.validator = node_budget, validator
        self.expansions = 0

    def _ok(self, level, a, b, action) -> bool:
        return self.validator is None or self.validator.validate(level, a, action, b).accept

    def generate_candidate_plans(self, level, state, n, max_depth):
        self.expansions = 0
        goal = level.solved
        if state == goal:
            return [[]]
        fwd, bwd = {state: (None, None)}, {goal: (None, None)}
        ff, fb = [state], [goal]
        meets: list = []
        depth = 0
        while ff and fb and not meets and depth < max_depth:
            expand_fwd = len(ff) <= len(fb)
            layer, seen, other = (ff, fwd, bwd) if expand_fwd else (fb, bwd, fwd)
            nxt_layer = []
            for cur in layer:
                for a in level.ACTIONS:
                    if expand_fwd:
                        nxt, _ = level.step(cur, a)
                        if nxt in seen or not self._ok(level, cur, nxt, a):
                            continue
                        seen[nxt] = (cur, a)
                    else:
                        inv = level.inverse(a)
                        prev, _ = level.step(cur, inv)  # forward move prev --a--> cur
                        if prev in seen or not self._ok(level, prev, cur, a):
                            continue
                        seen[prev] = (cur, a)
                        nxt = prev
                    nxt_layer.append(nxt)
                    self.expansions += 1
                    if nxt in other:
                        meets.append(nxt)
                if self.expansions > self.node_budget:
                    return []
            if expand_fwd:
                ff = nxt_layer
            else:
                fb = nxt_layer
            depth += 1
        plans = []
        for m in meets[:n]:
            head, cur = [], m
            while fwd[cur][0] is not None:
                cur, a = fwd[cur][1] and (fwd[cur][0], fwd[cur][1])
                head.append(a)
            tail, cur = [], m
            while bwd[cur][0] is not None:
                nxt, a = bwd[cur]
                tail.append(a)
                cur = nxt
            plan = head[::-1] + tail
            if plan not in plans:
                plans.append(plan)
        return plans
