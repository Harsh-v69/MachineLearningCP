from __future__ import annotations

from collections import deque


class Replan:
    """The LLM-free TAPE loop: solve on the true graph, execute, re-solve from the observed state on deviation."""

    def __init__(self, problem, solver, **cfg):
        self.problem, self.solver, self.cfg = problem, solver, cfg
        self.solves = 0
        self.reset(0)

    def reset(self, seed):
        self.plan, self.expect = deque(), None

    def act(self, s, rem):
        if not self.plan or s != self.expect:
            self.solves += 1
            r = self.solver(self.problem, s, budget=rem, **self.cfg)
            self.plan = deque(zip(r.path, r.states[1:])) if r.status == "ok" else deque()
        if not self.plan:
            return next((a for a, _, _ in self.problem.neighbors(s)), "")
        a, self.expect = self.plan.popleft()
        return a
