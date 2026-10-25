from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Hashable, Iterable, List, Optional, Tuple

State = Hashable
INF = math.inf


@dataclass
class Result:
    status: str  # ok | no_path | node_limit | too_large | timeout
    path: List[str] = field(default_factory=list)
    states: List[State] = field(default_factory=list)  # len(path) + 1 when ok
    cost: float = INF
    res: float = 0.0  # total side resource along the path
    nodes: int = 0
    seconds: float = 0.0


class Problem:
    """Implicit state graph. Subclasses override neighbors/is_goal/random_start; the rest have safe defaults."""

    def neighbors(self, s: State) -> Iterable[Tuple[str, State, float]]:
        raise NotImplementedError

    def is_goal(self, s: State) -> bool:
        raise NotImplementedError

    def h(self, s: State) -> float:
        """Admissible lower bound on remaining cost."""
        return 0.0

    def prune(self, s: State) -> bool:
        """True only for a provable dead end (goal unreachable from s)."""
        return False

    def res(self, s: State, a: str, s2: State) -> float:
        """Side resource of an edge, used by the constrained experiment."""
        return 1.0

    def res_bind(self, s: State, a: str, s2: State) -> float:
        """Resource of the binding constrained experiment (--design bind). Defaults to `res`; benchmarks override it
        because their `res` grows with length, so the length-optimal path is already resource-minimal."""
        return self.res(s, a, s2)

    def random_start(self, rng: random.Random, depth: int) -> Optional[State]:
        """A start from which the goal is reachable. `depth` is a difficulty knob; true T* comes from the Oracle."""
        raise NotImplementedError

    def step(self, s: State, a: str) -> Optional[State]:
        for a2, s2, _ in self.neighbors(s):
            if a2 == a:
                return s2
        return None


def make_result(problem: Problem, start: State, actions: List[str], nodes: int, t0: float) -> Result:
    """Replay `actions` from `start` to fill in states, cost and resource consistently for every solver."""
    states, cost, res, s = [start], 0.0, 0.0, start
    for a in actions:
        for a2, s2, c in problem.neighbors(s):
            if a2 == a:
                cost += c
                res += problem.res(s, a, s2)
                s = s2
                states.append(s)
                break
        else:
            raise ValueError(f"illegal action {a!r} in state {s!r}")
    return Result("ok", list(actions), states, cost, res, nodes, time.perf_counter() - t0)


def fail(status: str, nodes: int, t0: float) -> Result:
    return Result(status, nodes=nodes, seconds=time.perf_counter() - t0)
