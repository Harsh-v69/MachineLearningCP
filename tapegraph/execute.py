from __future__ import annotations

import random
import time


def run_episode(problem, policy, start, B, eta, rng):
    """Roll out `policy` for at most B steps. With probability eta the executed action differs from the intended one."""
    s = start
    if problem.is_goal(s):
        return True, 0
    for t in range(B):
        a = policy.act(s, B - t)
        if rng.random() < eta:
            others = [a2 for a2, _, _ in problem.neighbors(s) if a2 != a]
            if others:
                a = rng.choice(others)
        s2 = problem.step(s, a)  # illegal action => stay put (as in TAPE's env.step)
        if s2 is not None:
            s = s2
        if problem.is_goal(s):
            return True, t + 1
    return False, B


def evaluate(problem, start, policy, B, eta, episodes, seed):
    wins = steps = 0
    t0 = time.perf_counter()
    for i in range(episodes):
        policy.reset(seed + i)
        ok, n = run_episode(problem, policy, start, B, eta, random.Random(seed * 1_000_003 + i))
        wins += ok
        steps += n
    return {
        "success": wins / episodes,
        "mean_steps": steps / episodes,
        "solves": getattr(policy, "solves", 0) / episodes,
        "solver_fail": getattr(policy, "solver_fail", 0) / episodes,  # per episode; Replan's silent fallbacks
        "seconds": (time.perf_counter() - t0) / episodes,
    }
