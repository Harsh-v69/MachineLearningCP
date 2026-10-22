from __future__ import annotations

import random
from collections import deque

from ..solvers import ilp
from .react_sim import noisy_recommend


class TapeSim:
    """TAPE as modelled in the paper: fold N noisy rollouts into a graph, pick a path with the ILP, re-plan on deviation.

    ponytail: the ILP minimises path length in the folded graph (TAPE's node-score objective is not reproduced).
    """

    def __init__(self, problem, oracle, delta, N=16, use_ilp=True):
        self.problem, self.oracle, self.delta, self.N = problem, oracle, delta, N
        self.use_ilp = use_ilp and ilp.ORTOOLS_AVAILABLE
        self.solves = 0
        self.reset(0)

    def reset(self, seed):
        self.rng = random.Random(seed)
        self.plan, self.expect = deque(), None

    def act(self, s, rem):
        if not self.plan or s != self.expect:
            self._replan(s, rem)
        if not self.plan:
            return noisy_recommend(self.problem, self.oracle, self.rng, s, rem, self.delta)
        a, self.expect = self.plan.popleft()
        return a

    def _replan(self, s, rem):
        self.solves += 1
        edges = set()
        for _ in range(self.N):
            cur = s
            for _ in range(rem):
                if self.problem.is_goal(cur):
                    break
                a = noisy_recommend(self.problem, self.oracle, self.rng, cur, rem, self.delta)
                nxt = self.problem.step(cur, a)
                if nxt is None:
                    break
                edges.add((cur, a, nxt))
                cur = nxt
        self.plan = deque()
        goals = {v for _, _, v in edges if self.problem.is_goal(v)}
        if not goals:
            return
        pick = ilp.solve_graph if self.use_ilp else ilp.graph_path_bfs
        try:
            path = pick(s, goals, [(u, a, v, 1.0, 1.0) for u, a, v in sorted(edges, key=repr)])
        except ilp.IlpTimeout:
            return  # no plan: act() falls back to noisy_recommend
        if path:
            self.plan = deque((a, v) for _, a, v in path)
