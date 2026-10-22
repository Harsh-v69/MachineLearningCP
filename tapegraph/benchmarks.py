from __future__ import annotations

import functools
import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from .oracle import Oracle
from .problem import INF, Problem
from .problems.boxoban import boxoban_level
from .problems.cube2 import Cube2
from .problems.river import River
from .problems.sokoban import Sokoban


@dataclass(frozen=True)
class Bench:
    make: Callable[[random.Random], Problem]
    T_targets: List[int]
    exact: bool = False  # True: random_start(depth) already returns T* == depth
    depth: Tuple[int, int] = (10, 60)  # reverse-play steps range when not exact


@functools.lru_cache(maxsize=None)
def _river():
    return River(8, 4)


BENCHMARKS = {
    "sokoban": Bench(lambda rng: Sokoban.random_level(rng, 7, 9, 1, 0.08), [6, 10, 14, 18, 22], depth=(60, 600)),
    "boxoban": Bench(boxoban_level, [8, 12, 16, 20], depth=(30, 150)),
    "river": Bench(lambda rng: _river(), [4, 6, 8, 10, 12, 14], exact=True),
    "cube2": Bench(lambda rng: Cube2.shared(), [3, 5, 7, 9, 11], exact=True),
}


@dataclass
class Instance:
    problem: Problem
    start: object
    T: int
    oracle: Oracle


_oracles = {}


def make_instances(name, per_bucket, seed, tol=1, max_tries=5000):
    b = BENCHMARKS[name]
    rng = random.Random(seed)
    out = []
    for target in b.T_targets:
        got = tries = 0
        while got < per_bucket and tries < max_tries:
            tries += 1
            p = b.make(rng)
            s = p.random_start(rng, target if b.exact else rng.randint(*b.depth))
            if s is None:
                continue
            o = _oracles.setdefault(p, Oracle(p))
            T = o.dist(s)
            if T == INF or T == 0 or abs(T - target) > tol:
                continue
            out.append(Instance(p, s, int(T), o))
            got += 1
    return out
