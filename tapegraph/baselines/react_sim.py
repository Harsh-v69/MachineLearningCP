from __future__ import annotations

import random


def noisy_recommend(problem, oracle, rng, s, rem, delta):
    """Oracle's next action; with probability delta a planning error (an action that breaks the budget if one exists)."""
    legal = [a for a, _, _ in problem.neighbors(s)]
    if not legal:
        return ""
    base = oracle.best_action(s) or rng.choice(legal)
    if rng.random() < delta:
        viable = set(oracle.viable(s, rem))
        pool = [a for a in legal if a not in viable] or [a for a in legal if a != base]
        return rng.choice(pool) if pool else base
    return base


class ReActSim:
    """ReAct as modelled in the TAPE paper: one noisy recommendation per step, no recovery."""

    def __init__(self, problem, oracle, delta):
        self.problem, self.oracle, self.delta = problem, oracle, delta
        self.solves = 0
        self.rng = random.Random(0)

    def reset(self, seed):
        self.rng = random.Random(seed)

    def act(self, s, rem):
        return noisy_recommend(self.problem, self.oracle, self.rng, s, rem, self.delta)
