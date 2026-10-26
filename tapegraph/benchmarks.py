from __future__ import annotations

import functools
import random
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .oracle import Oracle
from .problem import INF, Problem
from .problems.boxoban import boxoban_level, load_boxoban_file
from .problems.cube2 import Cube2
from .problems.cube3 import Cube3
from .problems.river import River
from .problems.sokoban import Sokoban
from .solvers import astar


@dataclass(frozen=True)
class Bench:
    make: Optional[Callable[[random.Random], Problem]]
    T_targets: List[int]
    exact: bool = False  # True: random_start(rng, target) (river/cube2: T* == depth; cube3: T* <= depth, oracle-checked)
    depth: Tuple[int, int] = (10, 60)  # reverse-play steps range when not exact
    levels: Optional[tuple] = None  # fixed (problem, start) pairs (user-supplied file); make/T_targets/depth are then unused


@functools.lru_cache(maxsize=None)
def _river():
    return River(8, 4)


BENCHMARKS = {
    "sokoban": Bench(lambda rng: Sokoban.random_level(rng, 7, 9, 1, 0.08), [6, 10, 14, 18, 22], depth=(60, 600)),
    "sokoban2": Bench(lambda rng: Sokoban.random_level(rng, 7, 9, 2, 0.08), [6, 10, 14, 18, 22], depth=(60, 600)),
    "sokoban3": Bench(lambda rng: Sokoban.random_level(rng, 8, 10, 3, 0.08), [10, 14, 18, 22, 26], depth=(60, 600)),
    "boxoban": Bench(boxoban_level, [8, 12, 16, 20], depth=(30, 150)),
    "river": Bench(lambda rng: _river(), [4, 6, 8, 10, 12, 14], exact=True),
    "cube2": Bench(lambda rng: Cube2.shared(), [3, 5, 7, 9, 11], exact=True),
    "cube3": Bench(lambda rng: Cube3.shared(), [3, 5, 7, 9], exact=True),  # T=10: wA* hit the 500k cap
}


@dataclass
class Instance:
    problem: Problem
    start: object
    T: int
    oracle: Oracle
    skip: str = ""  # oracle status when a user-supplied level could not be solved (T is then -1); "" for solved instances
    index: int = -1  # position in the user-supplied file; -1 for generated instances


_oracles = {}


def use_boxoban_file(path):
    """Register the `boxoban_file` benchmark for a user-supplied DeepMind-format file (ValueError if malformed)."""
    BENCHMARKS["boxoban_file"] = Bench(None, [], levels=tuple(load_boxoban_file(path)))


def _fixed_instances(levels, limit):
    """First `limit` levels; T* comes from the oracle. A level the oracle cannot solve (or that is already solved)
    keeps its slot as a skip instance."""
    out = []
    for idx, (p, s) in enumerate(levels[:limit]):
        o = _oracles.setdefault(p, Oracle(p))
        T = o.dist(s)
        if T == INF:  # Oracle reports INF for no_path and node_limit alike; recover which
            status = "no_path" if p.prune(s) else astar.solve(p, s, max_nodes=o.max_nodes).status
            out.append(Instance(p, s, -1, o, skip=status if status != "ok" else "no_path", index=idx))
        elif T == 0:  # already solved: no T* to ratio against, so it is skipped like an unsolved level
            out.append(Instance(p, s, -1, o, skip="already_solved", index=idx))
        else:
            out.append(Instance(p, s, int(T), o, index=idx))
    return out


def make_instances(name, per_bucket, seed, tol=1, max_tries=5000):
    b = BENCHMARKS[name]
    if b.levels is not None:  # per_bucket caps the number of levels; seed and tol do not apply
        return _fixed_instances(b.levels, per_bucket)
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
        if got < per_bucket:
            print(f"[make_instances] {name} T*={target}: only {got}/{per_bucket} instances after {tries} tries", file=sys.stderr)
    return out
