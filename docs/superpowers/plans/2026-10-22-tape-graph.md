# tape-graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tape-graph`, an LLM-free version of TAPE: graph solvers (BFS, A*, weighted A*, IDA*, CP-SAT ILP) on four benchmarks (Sokoban, Boxoban, River Crossing, Rubik's 2x2x2), compared against simulated ReAct and simulated TAPE.

**Architecture:** Each benchmark implements one small `Problem` interface (implicit graph + admissible heuristic + dead-end prune + random-start generator). Solvers share one signature `solve(problem, start, budget, ...) -> Result`. An `Oracle` (exact distance-to-goal) powers the simulated ReAct/TAPE baselines, which use TAPE's noise model (`delta` planning error, `eta` execution noise). A `bench` CLI writes CSVs and a `results.md` table.

**Tech Stack:** Python 3.12, numpy, pytest, ortools (CP-SAT, for the ILP only). Standard library for everything else.

**Spec:** `docs/superpowers/specs/2026-10-22-tape-graph-design.md`

## Global Constraints

- New project at `C:\Users\harsh\Desktop\TAPE\tape-graph\`; `TAPE-main` is never modified.
- All edges have cost 1.0 (path length). A second per-edge resource (`Problem.res`) exists only for the constrained experiment.
- Python 3.12; numpy for the cube; `ortools` is imported lazily and the code and tests must work (ILP tests skipped) without it.
- Tests are plain `pytest`/`assert`; no other test framework, no fixtures beyond module-level helpers.
- Dependencies are installed only after the user confirms (Task 1 Step 1).
- No plotting in this plan (spec §7 said "only if matplotlib installed"; deferred as YAGNI, tables only).
- Deliberate deviation from spec §5: the ILP uses an edge-flow formulation (one binary per edge) instead of TAPE's time-expanded model. Costs are positive, so the optimum is a simple path, and the model is `L` times smaller. The time-expanded form is only needed for node-score objectives, which this project does not use.
- Run all commands from `C:\Users\harsh\Desktop\TAPE\tape-graph` (bash syntax shown).

## File Structure

```
tape-graph/
  conftest.py                    # empty; makes the repo root importable for pytest
  requirements.txt
  .gitignore
  README.md                      # Task 10
  tapegraph/
    __init__.py
    problem.py                   # State, Result, Problem, make_result, fail      (Task 1)
    oracle.py                    # Oracle: exact dist / best action / viable      (Task 3)
    execute.py                   # run_episode, evaluate                          (Task 8)
    benchmarks.py                # BENCHMARKS registry, make_instances            (Task 9)
    bench.py                     # CLI: solvers | agents | constrained | report   (Task 9)
    problems/{__init__,river,sokoban,boxoban,cube2}.py
    solvers/{__init__,bfs,astar,idastar,ilp}.py
    baselines/{__init__,react_sim,tape_sim,replan}.py
  tests/
    toy.py                       # GraphProblem used by solver tests
    test_core_solvers.py  test_idastar.py  test_oracle_river.py  test_sokoban.py
    test_boxoban.py  test_cube2.py  test_ilp.py  test_baselines.py  test_bench.py
```

---

### Task 1: Project scaffold, core types, BFS, A* (with weighted and resource-constrained modes)

**Files:**
- Create: `.gitignore`, `requirements.txt`, `conftest.py`, `tapegraph/__init__.py`, `tapegraph/problem.py`, `tapegraph/solvers/__init__.py`, `tapegraph/solvers/bfs.py`, `tapegraph/solvers/astar.py`, `tests/toy.py`, `tests/test_core_solvers.py`

**Interfaces:**
- Produces:
  - `Problem` with `neighbors(s) -> Iterable[(action:str, next, cost:float)]`, `is_goal(s)`, `h(s)=0.0`, `prune(s)=False`, `res(s,a,s2)=1.0`, `random_start(rng, depth)`, `step(s,a) -> next|None`
  - `Result(status, path, states, cost, res, nodes, seconds)` with `status in {"ok","no_path","node_limit","too_large"}`
  - `make_result(problem, start, actions, nodes, t0) -> Result`, `fail(status, nodes, t0) -> Result`
  - `bfs.solve(problem, start, budget=INF, max_nodes=2_000_000)`
  - `astar.solve(problem, start, budget=INF, w=1.0, res_budget=None, max_nodes=2_000_000)`

- [ ] **Step 1: Ask the user to confirm installing dependencies, then install**

Ask: "OK to run `pip install numpy pytest ortools`?" Only after a yes:

```bash
cd /c/Users/harsh/Desktop/TAPE/tape-graph
python -m pip install numpy pytest ortools
python -c "import numpy, pytest, ortools; print('ok')"
```
Expected: prints `ok`. If the user declines `ortools`, install only `numpy pytest`; ILP tests will skip.

- [ ] **Step 2: Scaffold files and init git**

`requirements.txt`:
```
numpy
pytest
ortools
```
`.gitignore`:
```
__pycache__/
.cache/
results/
*.pyc
```
Create empty `conftest.py`, `tapegraph/__init__.py`, `tapegraph/solvers/__init__.py`. Then:
```bash
git init
```

- [ ] **Step 3: Write the toy graph and the failing tests**

`tests/toy.py`:
```python
from tapegraph.problem import Problem


class GraphProblem(Problem):
    """Explicit graph. adj[s] = [(action, next, resource)]; every edge costs 1."""

    def __init__(self, adj, goal, h=None):
        self.adj, self.goal, self._h = adj, goal, h or {}

    def neighbors(self, s):
        for a, v, _ in self.adj[s]:
            yield a, v, 1.0

    def is_goal(self, s):
        return s == self.goal

    def h(self, s):
        return float(self._h.get(s, 0))

    def res(self, s, a, s2):
        return float(next(r for a2, v, r in self.adj[s] if a2 == a))


# Two routes A->E: short but resource-hungry (len 2, res 6) vs long and cheap (len 3, res 3).
GRAPH = GraphProblem(
    {
        "A": [("ab", "B", 1), ("ac", "C", 1)],
        "B": [("be", "E", 5)],
        "C": [("cd", "D", 1)],
        "D": [("de", "E", 1)],
        "E": [],
        "X": [],  # dead end: goal unreachable
    },
    goal="E",
    h={"A": 2, "B": 1, "C": 1, "D": 1, "E": 0},
)
```

`tests/test_core_solvers.py`:
```python
from toy import GRAPH
from tapegraph.solvers import astar, bfs


def test_bfs_finds_shortest():
    r = bfs.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2 and r.res == 6


def test_bfs_budget_too_small():
    assert bfs.solve(GRAPH, "A", budget=1).status == "no_path"


def test_astar_matches_bfs():
    r = astar.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.states == ["A", "B", "E"]


def test_astar_budget_too_small():
    assert astar.solve(GRAPH, "A", budget=1).status == "no_path"


def test_astar_resource_budget_forces_longer_path():
    r = astar.solve(GRAPH, "A", res_budget=4)
    assert r.status == "ok" and r.path == ["ac", "cd", "de"] and r.cost == 3 and r.res == 3
    assert astar.solve(GRAPH, "A", res_budget=2).status == "no_path"


def test_resource_budget_and_length_budget_interact():
    # res_budget=4 needs length 3, so a length budget of 2 makes it infeasible.
    assert astar.solve(GRAPH, "A", budget=2, res_budget=4).status == "no_path"


def test_weighted_astar_never_beats_optimal():
    r = astar.solve(GRAPH, "A", w=2.0)
    assert r.status == "ok" and r.cost >= 2


def test_start_is_goal():
    r = astar.solve(GRAPH, "E")
    assert r.status == "ok" and r.path == [] and r.cost == 0


def test_node_limit():
    assert astar.solve(GRAPH, "A", max_nodes=0).status == "node_limit"


def test_unreachable_goal_is_no_path():
    assert bfs.solve(GRAPH, "X").status == "no_path"
    assert astar.solve(GRAPH, "X").status == "no_path"
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_core_solvers.py -v`
Expected: FAIL / ERROR (`ModuleNotFoundError: tapegraph.problem`).

- [ ] **Step 5: Implement `problem.py`**

```python
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
    status: str  # ok | no_path | node_limit | too_large
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
```

- [ ] **Step 6: Implement `solvers/bfs.py`**

```python
from __future__ import annotations

import time
from collections import deque

from ..problem import INF, fail, make_result


def solve(problem, start, budget=INF, max_nodes=2_000_000):
    """Plain BFS. Ignores h() and prune() on purpose: it is the independent reference the others are checked against.

    ponytail: assumes unit edge cost; switch to Dijkstra if a benchmark gets non-unit costs.
    """
    t0 = time.perf_counter()
    if problem.is_goal(start):
        return make_result(problem, start, [], 0, t0)
    parent = {start: (None, None)}
    g = {start: 0}
    q = deque([start])
    nodes = 0
    while q:
        u = q.popleft()
        if g[u] >= budget:
            continue
        nodes += 1
        if nodes > max_nodes:
            return fail("node_limit", nodes, t0)
        for a, v, _ in problem.neighbors(u):
            if v in parent:
                continue
            parent[v] = (u, a)
            g[v] = g[u] + 1
            if problem.is_goal(v):
                acts, x = [], v
                while parent[x][0] is not None:
                    acts.append(parent[x][1])
                    x = parent[x][0]
                return make_result(problem, start, acts[::-1], nodes, t0)
            q.append(v)
    return fail("no_path", nodes, t0)
```

- [ ] **Step 7: Implement `solvers/astar.py`**

```python
from __future__ import annotations

import heapq
import itertools
import time

from ..problem import INF, fail, make_result


def solve(problem, start, budget=INF, w=1.0, res_budget=None, max_nodes=2_000_000):
    """A* / weighted A* (w > 1) with optional side-resource budget.

    Graph constraints applied: prune() dead ends, drop nodes with g+h > budget, drop labels whose
    accumulated resource exceeds res_budget. With res_budget the search is label-setting over
    (state, g, resource) with dominance, so it stays exact.
    """
    t0 = time.perf_counter()
    if problem.prune(start):
        return fail("no_path", 0, t0)
    use_res = res_budget is not None
    labels = [(start, 0.0, 0.0, -1, None)]  # (state, g, resource, parent label, action)
    front = {start: [0]}  # non-dominated label ids per state
    dead = set()
    tie = itertools.count()
    heap = [(w * problem.h(start), next(tie), 0)]
    nodes = 0
    while heap:
        _, _, i = heapq.heappop(heap)
        if i in dead:
            continue
        s, g, r, _, _ = labels[i]
        if problem.is_goal(s):
            acts, j = [], i
            while labels[j][3] != -1:
                acts.append(labels[j][4])
                j = labels[j][3]
            return make_result(problem, start, acts[::-1], nodes, t0)
        nodes += 1
        if nodes > max_nodes:
            return fail("node_limit", nodes, t0)
        for a, s2, c in problem.neighbors(s):
            if problem.prune(s2):
                continue
            g2 = g + c
            r2 = r + (problem.res(s, a, s2) if use_res else 0.0)
            h2 = problem.h(s2)
            if g2 + h2 > budget or (use_res and r2 > res_budget):
                continue
            cur = front.get(s2, [])
            if any(labels[j][1] <= g2 and labels[j][2] <= r2 for j in cur):
                continue
            for j in cur:
                if g2 <= labels[j][1] and r2 <= labels[j][2]:
                    dead.add(j)
            labels.append((s2, g2, r2, i, a))
            front[s2] = [j for j in cur if j not in dead] + [len(labels) - 1]
            heapq.heappush(heap, (g2 + w * h2, next(tie), len(labels) - 1))
    return fail("no_path", nodes, t0)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python -m pytest tests/test_core_solvers.py -v`
Expected: 10 passed.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: core Problem/Result types, BFS and A* (weighted, resource-constrained)"
```

---

### Task 2: IDA*

**Files:**
- Create: `tapegraph/solvers/idastar.py`, `tests/test_idastar.py`

**Interfaces:**
- Consumes: `Problem`, `make_result`, `fail`, `INF` from Task 1; `tests/toy.py::GRAPH`.
- Produces: `idastar.solve(problem, start, budget=INF, max_nodes=2_000_000) -> Result`

- [ ] **Step 1: Write the failing test**

`tests/test_idastar.py`:
```python
from toy import GRAPH
from tapegraph.solvers import idastar


def test_idastar_optimal_on_toy():
    r = idastar.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2


def test_idastar_budget_too_small():
    assert idastar.solve(GRAPH, "A", budget=1).status == "no_path"


def test_idastar_unreachable_goal_terminates():
    assert idastar.solve(GRAPH, "X").status == "no_path"  # infinite budget, must still stop


def test_idastar_from_midpoint():
    r = idastar.solve(GRAPH, "B", budget=10)
    assert r.status == "ok" and r.path == ["be"]


def test_idastar_start_is_goal():
    assert idastar.solve(GRAPH, "E").path == []
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_idastar.py -v`
Expected: ERROR (`cannot import name 'idastar'`).

- [ ] **Step 3: Implement**

`tapegraph/solvers/idastar.py`:
```python
from __future__ import annotations

import time

from ..problem import INF, fail, make_result

_FOUND = -1.0


class _Limit(Exception):
    pass


def solve(problem, start, budget=INF, max_nodes=2_000_000):
    """IDA* with a per-iteration transposition table (state -> best g seen this iteration)."""
    t0 = time.perf_counter()
    if problem.prune(start):
        return fail("no_path", 0, t0)
    nodes = 0
    acts = []
    bound = problem.h(start)

    def dfs(s, g, seen):
        nonlocal nodes
        f = g + problem.h(s)
        if f > bound:
            return f
        if problem.is_goal(s):
            return _FOUND
        nodes += 1
        if nodes > max_nodes:
            raise _Limit
        low = INF
        for a, s2, c in problem.neighbors(s):
            if problem.prune(s2):
                continue
            g2 = g + c
            if seen.get(s2, INF) <= g2:
                continue
            seen[s2] = g2
            acts.append(a)
            r = dfs(s2, g2, seen)
            if r == _FOUND:
                return _FOUND
            acts.pop()
            low = min(low, r)
        return low

    try:
        while bound <= budget:
            r = dfs(start, 0.0, {start: 0.0})
            if r == _FOUND:
                return make_result(problem, start, list(acts), nodes, t0)
            if r == INF:
                break
            bound = r
    except _Limit:
        return fail("node_limit", nodes, t0)
    return fail("no_path", nodes, t0)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_idastar.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: IDA* solver"
```

---

### Task 3: Oracle and River Crossing

**Files:**
- Create: `tapegraph/oracle.py`, `tapegraph/problems/__init__.py` (empty), `tapegraph/problems/river.py`, `tests/test_oracle_river.py`

**Interfaces:**
- Consumes: `Problem`, `INF`; `astar.solve`; `bfs.solve`; `idastar.solve`; `tests/toy.py::GRAPH`.
- Produces:
  - `Oracle(problem, max_nodes=300_000)` with `.dist(s) -> float` (INF if unreachable or search limit hit), `.best_action(s) -> str|None`, `.viable(s, rem) -> list[str]` (actions whose next state has `dist <= rem-1`). If the problem defines `exact_dist(s)`, the oracle uses it. Assumes unit edge costs.
  - `River(n=8, cap=4)`: `.dist` dict (exact distance for every reachable state), `.exact_dist(s)`, goal `(0,0,1)`, `River(n,cap).start`-style starts via `random_start(rng, depth)` where `depth` is the exact `T*`.

- [ ] **Step 1: Write the failing tests**

`tests/test_oracle_river.py`:
```python
import random

from toy import GRAPH
from tapegraph.oracle import Oracle
from tapegraph.problem import INF
from tapegraph.problems.river import River
from tapegraph.solvers import astar, bfs, idastar


def test_oracle_on_toy_graph():
    o = Oracle(GRAPH)
    assert o.dist("A") == 2 and o.dist("E") == 0
    assert o.best_action("A") == "ab" and o.best_action("E") is None
    assert o.viable("A", 2) == ["ab"]  # "ac" leaves dist 2 > rem-1 = 1
    assert sorted(o.viable("A", 3)) == ["ab", "ac"]


def test_classic_missionaries_and_cannibals_needs_11_crossings():
    assert River(3, 2).exact_dist((3, 3, 0)) == 11


def test_river_solvers_agree_with_exact_distance_from_every_state():
    p = River(8, 4)
    for s, d in p.dist.items():
        if d == 0:
            continue
        b = bfs.solve(p, s)
        a = astar.solve(p, s)
        i = idastar.solve(p, s)
        assert b.cost == a.cost == i.cost == d, s


def test_river_heuristic_is_admissible():
    p = River(8, 4)
    assert all(p.h(s) <= d for s, d in p.dist.items())


def test_river_random_start_has_requested_distance():
    p = River(8, 4)
    rng = random.Random(0)
    for depth in (3, 7, 12):
        s = p.random_start(rng, depth)
        assert p.exact_dist(s) == depth
    assert p.random_start(rng, 99) is None


def test_oracle_uses_exact_dist_when_available():
    p = River(8, 4)
    o = Oracle(p)
    s = p.random_start(random.Random(1), 9)
    assert o.dist(s) == 9
    a = o.best_action(s)
    assert p.exact_dist(p.step(s, a)) == 8
    assert o.dist((99, 99, 0)) == INF
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_oracle_river.py -v`
Expected: ERROR (`No module named 'tapegraph.oracle'`).

- [ ] **Step 3: Implement `oracle.py`**

```python
from __future__ import annotations

from .problem import INF
from .solvers import astar


class Oracle:
    """Exact distance-to-goal for the simulated baselines. Cached; search limit hits count as unreachable.

    ponytail: assumes unit edge cost (dist == path length) and treats a max_nodes hit as INF.
    """

    def __init__(self, problem, max_nodes: int = 300_000):
        self.p = problem
        self.max_nodes = max_nodes
        self._d = {}
        self._a = {}
        self._exact = getattr(problem, "exact_dist", None)

    def dist(self, s) -> float:
        if self._exact:
            return self._exact(s)
        if s in self._d:
            return self._d[s]
        if self.p.prune(s):
            self._d[s] = INF
            return INF
        r = astar.solve(self.p, s, max_nodes=self.max_nodes)
        if r.status != "ok":
            self._d[s] = INF
            return INF
        n = len(r.path)
        for i, st in enumerate(r.states):  # suffixes of an optimal path are optimal
            self._d[st] = n - i
            if i < n:
                self._a[st] = r.path[i]
        return n

    def best_action(self, s):
        d = self.dist(s)
        if d == 0 or d == INF:
            return None
        if self._exact:
            for a, s2, _ in self.p.neighbors(s):
                if self._exact(s2) == d - 1:
                    return a
            return None
        return self._a.get(s)

    def viable(self, s, rem):
        return [a for a, s2, _ in self.p.neighbors(s) if self.dist(s2) <= rem - 1]
```

- [ ] **Step 4: Implement `problems/river.py`**

```python
from __future__ import annotations

from collections import deque

from ..problem import INF, Problem


class River(Problem):
    """Missionaries and cannibals: n of each, boat holds `cap`. State (missionaries_left, cannibals_left, boat) with
    boat 0 = left bank. Goal (0, 0, 1). Moves are reversible, so distances come from one reverse BFS."""

    GOAL = (0, 0, 1)

    def __init__(self, n: int = 8, cap: int = 4):
        self.n, self.cap = n, cap
        self.dist = {self.GOAL: 0}
        q = deque([self.GOAL])
        while q:
            x = q.popleft()
            for _, y, _ in self.neighbors(x):
                if y not in self.dist:
                    self.dist[y] = self.dist[x] + 1
                    q.append(y)

    def _safe(self, m, c):
        return (m == 0 or m >= c) and (self.n - m == 0 or self.n - m >= self.n - c)

    def neighbors(self, s):
        m, c, b = s
        sgn = -1 if b == 0 else 1
        am, ac = (m, c) if b == 0 else (self.n - m, self.n - c)
        for dm in range(min(am, self.cap) + 1):
            for dc in range(min(ac, self.cap - dm) + 1):
                if dm + dc == 0:
                    continue
                t = (m + sgn * dm, c + sgn * dc, 1 - b)
                if self._safe(t[0], t[1]):
                    yield f"{dm}M{dc}C", t, 1.0

    def is_goal(self, s):
        return s == self.GOAL

    def h(self, s):
        m, c, b = s
        left = m + c
        if left == 0:
            return 0.0
        trips = -(-left // self.cap)  # forward crossings needed; each forward trip (but the last) needs a return
        return float(2 * trips - 1 if b == 0 else 2 * trips)

    def res(self, s, a, s2):
        return float(abs(s[0] - s2[0]) + abs(s[1] - s2[1]))  # passengers carried

    def exact_dist(self, s):
        return float(self.dist.get(s, INF))

    def random_start(self, rng, depth):
        cands = sorted(s for s, d in self.dist.items() if d == depth)
        return rng.choice(cands) if cands else None
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_oracle_river.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: Oracle and River Crossing benchmark"
```

---

### Task 4: Sokoban

**Files:**
- Create: `tapegraph/problems/sokoban.py`, `tests/test_sokoban.py`

**Interfaces:**
- Consumes: `Problem`; `bfs`, `astar`.
- Produces: `Sokoban(H, W, walls, goals)` with `Sokoban.from_grid(grid) -> (problem, start_state)`, `Sokoban.random_level(rng, H=7, W=9, boxes=1, wall_prob=0.08) -> Sokoban`, `.dead` (static dead cells), `.random_start(rng, depth)` (reverse play from a solved layout; `depth` = reverse steps). State = `((r, c), boxes_tuple_sorted)`. Actions `"U" "D" "L" "R"`. Resource: push = 3, plain move = 1.

- [ ] **Step 1: Write the failing tests**

`tests/test_sokoban.py`:
```python
import random

from tapegraph.problems.sokoban import Sokoban
from tapegraph.solvers import astar, bfs, idastar

GRID = """
#######
#     #
# .$@ #
#     #
#######
"""


def test_single_push():
    p, s = Sokoban.from_grid(GRID)
    r = bfs.solve(p, s)
    assert r.path == ["L"] and r.cost == 1
    assert r.res == 3  # a push costs 3 resource units
    assert astar.solve(p, s).path == ["L"]


def test_dead_cells_are_static_deadlocks():
    p, _ = Sokoban.from_grid(GRID)
    assert (1, 1) in p.dead and (3, 3) in p.dead and (2, 1) in p.dead
    assert (2, 2) not in p.dead and (2, 3) not in p.dead


def test_pushing_into_a_dead_cell_is_pruned():
    p, s = Sokoban.from_grid(GRID)
    s_dead = ((2, 4), ((1, 3),))  # row 1 is all dead in this room
    assert p.prune(s_dead) and not p.prune(s)


def _levels(boxes, seeds, depth):
    for seed in seeds:
        rng = random.Random(seed)
        p = Sokoban.random_level(rng, 7, 9, boxes, 0.08)
        yield p, p.random_start(rng, depth)


def test_astar_and_idastar_match_bfs_on_random_levels():
    cases = list(_levels(1, range(12), 25)) + list(_levels(2, range(100, 105), 30))
    for p, s in cases:
        b = bfs.solve(p, s)  # BFS ignores h and prune
        a = astar.solve(p, s)
        i = idastar.solve(p, s)
        assert b.status == "ok" and b.cost <= 30  # reverse play guarantees solvability
        assert a.status == "ok" and i.status == "ok"
        assert a.cost == b.cost == i.cost, "inadmissible h or unsound prune"


def test_random_start_is_a_legal_state():
    p, s = next(_levels(2, [7], 20))
    (pr, pc), boxes = s
    assert len(boxes) == 2 and (pr, pc) not in p.walls and not set(boxes) & p.walls
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_sokoban.py -v`
Expected: ERROR (`No module named 'tapegraph.problems.sokoban'`).

- [ ] **Step 3: Implement `problems/sokoban.py`**

```python
from __future__ import annotations

from collections import deque

from ..problem import Problem

DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


class Sokoban(Problem):
    """Sokoban level (walls + goals). State = (player, sorted box tuple). Map must be enclosed by walls.

    Legend for from_grid: # wall, . goal, $ box, @ player, * box on goal, + player on goal.
    """

    def __init__(self, H, W, walls, goals):
        self.H, self.W = H, W
        self.walls = frozenset(walls)
        self.goals = frozenset(goals)
        self.free = [(r, c) for r in range(H) for c in range(W) if (r, c) not in self.walls]
        self.dead = self._dead_cells()

    @classmethod
    def from_grid(cls, grid):
        walls, goals, boxes, player = set(), set(), [], None
        rows = grid.strip("\n").split("\n")
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "#":
                    walls.add((r, c))
                if ch in ".*+":
                    goals.add((r, c))
                if ch in "$*":
                    boxes.append((r, c))
                if ch in "@+":
                    player = (r, c)
        p = cls(len(rows), max(map(len, rows)), walls, goals)
        return p, (player, tuple(sorted(boxes)))

    @classmethod
    def random_level(cls, rng, H=7, W=9, boxes=1, wall_prob=0.08):
        border = {(r, c) for r in range(H) for c in range(W) if r in (0, H - 1) or c in (0, W - 1)}
        inner = [(r, c) for r in range(1, H - 1) for c in range(1, W - 1)]
        while True:
            walls = border | {x for x in inner if rng.random() < wall_prob}
            free = [x for x in inner if x not in walls]
            if len(free) >= boxes + 1:
                rng.shuffle(free)
                return cls(H, W, walls, free[:boxes])

    def _dead_cells(self):
        """Cells from which a box can never reach any goal (walls only, other boxes ignored)."""
        alive = set(self.goals)
        q = deque(alive)
        while q:
            g = q.popleft()
            for dr, dc in DIRS.values():
                x = (g[0] - dr, g[1] - dc)  # box pushed from x to g in direction d
                pl = (x[0] - dr, x[1] - dc)  # player stands here to push
                if x in alive or x in self.walls or pl in self.walls:
                    continue
                alive.add(x)
                q.append(x)
        return frozenset(c for c in self.free if c not in alive)

    def neighbors(self, s):
        (pr, pc), boxes = s
        for a, (dr, dc) in DIRS.items():
            n = (pr + dr, pc + dc)
            if n in self.walls:
                continue
            if n in boxes:
                b = (n[0] + dr, n[1] + dc)
                if b in self.walls or b in boxes:
                    continue
                nb = tuple(sorted([x for x in boxes if x != n] + [b]))
                yield a, (n, nb), 1.0
            else:
                yield a, (n, boxes), 1.0

    def is_goal(self, s):
        return set(s[1]) == self.goals

    def h(self, s):
        return float(sum(min(abs(b[0] - g[0]) + abs(b[1] - g[1]) for g in self.goals) for b in s[1]))

    def prune(self, s):
        return any(b in self.dead for b in s[1])

    def res(self, s, a, s2):
        return 3.0 if s2[1] != s[1] else 1.0  # pushing costs more fuel than walking

    def _reverse_neighbors(self, s):
        (pr, pc), boxes = s
        for dr, dc in DIRS.values():
            n = (pr + dr, pc + dc)
            if n in self.walls or n in boxes:
                continue
            yield (n, boxes)
            back = (pr - dr, pc - dc)  # a box behind the player can be pulled into the player's cell
            if back in boxes:
                yield (n, tuple(sorted([x for x in boxes if x != back] + [(pr, pc)])))

    def random_start(self, rng, depth):
        spots = [x for x in self.free if x not in self.goals]
        s = (rng.choice(spots), tuple(sorted(self.goals)))
        for _ in range(depth):
            nbrs = list(self._reverse_neighbors(s))
            if not nbrs:
                break
            s = rng.choice(nbrs)
        return s
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_sokoban.py -v`
Expected: 5 passed. If `test_astar_and_idastar_match_bfs_on_random_levels` fails with a cost mismatch, the heuristic is inadmissible or `prune` is unsound; debug that first (print the level and both paths).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Sokoban benchmark with dead-cell pruning"
```

---

### Task 5: Boxoban-style generator

**Files:**
- Create: `tapegraph/problems/boxoban.py`, `tests/test_boxoban.py`

**Interfaces:**
- Consumes: `Sokoban`; `astar.solve`.
- Produces: `boxoban_level(rng) -> Sokoban` (10x10, 4 boxes, 5% internal walls). Starts come from `Sokoban.random_start`.

- [ ] **Step 1: Write the failing test**

`tests/test_boxoban.py`:
```python
import random

from tapegraph.problems.boxoban import boxoban_level
from tapegraph.solvers import astar


def test_boxoban_level_shape():
    p = boxoban_level(random.Random(0))
    assert (p.H, p.W) == (10, 10) and len(p.goals) == 4


def test_boxoban_short_reverse_play_is_solvable_by_astar():
    for seed in range(4):
        rng = random.Random(seed)
        p = boxoban_level(rng)
        s = p.random_start(rng, 12)
        r = astar.solve(p, s, max_nodes=500_000)
        assert r.status == "ok" and r.cost <= 12  # reverse play of 12 steps => solution of length <= 12
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_boxoban.py -v`
Expected: ERROR (`No module named 'tapegraph.problems.boxoban'`).

- [ ] **Step 3: Implement**

`tapegraph/problems/boxoban.py`:
```python
from .sokoban import Sokoban

# Boxoban-style: 10x10 room, 4 boxes. Generated locally; DeepMind's level files can be added as a loader later.
def boxoban_level(rng):
    return Sokoban.random_level(rng, H=10, W=10, boxes=4, wall_prob=0.05)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_boxoban.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Boxoban-style 10x10 4-box generator"
```

---

### Task 6: Rubik's 2x2x2

**Files:**
- Create: `tapegraph/problems/cube2.py`, `tests/test_cube2.py`

**Interfaces:**
- Consumes: `Problem`, `INF`; numpy; `astar`, `idastar`.
- Produces: `Cube2.shared()` (cached singleton; builds move tables, two pattern databases and the full 3,674,160-entry distance table, cached to `.cache/cube2_dist.npy`; the first build takes about 12 s). State `(perm_index, twist_index)`, goal `(0, 0)`. 9 moves: `U U2 U' R R2 R' F F2 F'` (half-turn metric, God's number 11). `h = max(perm PDB, twist PDB)` (admissible, not exact). `exact_dist(s)`. `random_start(rng, depth)` returns a state with exact `T* == depth`. Resource: half-turn = 2, quarter-turn = 1.

The move data was verified in a prototype: the BFS depth counts are exactly `1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644` (sum 3,674,160), and the PDB heuristic is admissible.

- [ ] **Step 1: Write the failing tests**

`tests/test_cube2.py`:
```python
import random

import numpy as np

from tapegraph.problems.cube2 import Cube2
from tapegraph.solvers import astar, idastar

CUBE = Cube2.shared()


def test_distance_distribution_matches_known_2x2x2_counts():
    counts = np.bincount(CUBE.dist.astype(np.int64))
    assert counts.tolist() == [1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644]


def test_heuristic_is_admissible_and_goal_is_zero():
    rng = random.Random(0)
    for _ in range(2000):
        i = rng.randrange(len(CUBE.dist))
        s = divmod(i, CUBE.NT)
        assert CUBE.h(s) <= CUBE.exact_dist(s)
    assert CUBE.h((0, 0)) == 0 and CUBE.is_goal((0, 0))


def test_random_start_has_exact_requested_depth():
    rng = random.Random(1)
    for depth in (1, 5, 9, 11):
        assert CUBE.exact_dist(CUBE.random_start(rng, depth)) == depth


def test_solvers_find_optimal_solutions():
    rng = random.Random(2)
    for depth in (4, 6, 7):
        s = CUBE.random_start(rng, depth)
        a = astar.solve(CUBE, s)
        i = idastar.solve(CUBE, s)
        assert a.status == i.status == "ok"
        assert a.cost == i.cost == depth


def test_moves_are_inverses():
    s = CUBE.random_start(random.Random(3), 8)
    for name, inv in (("U", "U'"), ("R", "R'"), ("F", "F'"), ("U2", "U2")):
        assert CUBE.step(CUBE.step(s, name), inv) == s


def test_half_turns_cost_two_resource_units():
    s = CUBE.random_start(random.Random(4), 5)
    assert CUBE.res(s, "R2", CUBE.step(s, "R2")) == 2 and CUBE.res(s, "R", CUBE.step(s, "R")) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_cube2.py -v`
Expected: ERROR (`No module named 'tapegraph.problems.cube2'`).

- [ ] **Step 3: Implement**

`tapegraph/problems/cube2.py`:
```python
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np

from ..problem import INF, Problem

# Corners URF UFL ULB UBR DFR DLF DBL DRB = 0..7. Corner 6 (DBL) is fixed by U, R, F, which removes cube rotations.
# Quarter-turn data: (corner permutation, corner orientation twist).
_QUARTER = {
    "U": ([3, 0, 1, 2, 4, 5, 6, 7], [0] * 8),
    "R": ([4, 1, 2, 0, 7, 5, 6, 3], [2, 0, 0, 1, 1, 0, 0, 2]),
    "F": ([1, 5, 2, 3, 0, 4, 6, 7], [1, 2, 0, 0, 2, 1, 0, 0]),
}
_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "cube2_dist.npy"


def _mul(a, b):
    cp = [a[0][b[0][i]] for i in range(8)]
    co = [(a[1][b[0][i]] + b[1][i]) % 3 for i in range(8)]
    return cp, co


def _moves():
    names, tabs = [], []
    for n, m in _QUARTER.items():
        m2 = _mul(m, m)
        m3 = _mul(m2, m)
        names += [n, n + "2", n + "'"]
        tabs += [m, m2, m3]
    return names, tabs


def _enumerate(start, step):
    idx, lst, q = {start: 0}, [start], deque([start])
    while q:
        x = q.popleft()
        for m in range(9):
            y = step(x, m)
            if y not in idx:
                idx[y] = len(lst)
                lst.append(y)
                q.append(y)
    return idx, lst


def _bfs_1d(table):
    d = np.full(len(table), -1, dtype=np.int16)
    d[0] = 0
    q = deque([0])
    while q:
        x = q.popleft()
        for m in range(table.shape[1]):
            y = table[x, m]
            if d[y] < 0:
                d[y] = d[x] + 1
                q.append(y)
    return d


class Cube2(Problem):
    """2x2x2 cube in half-turn metric. State (perm, twist): corner permutation (5040) x corner twist (729).

    The two coordinates evolve independently under every move, so a pattern database on each coordinate is an
    admissible heuristic (max of the two) and the full 3.67M-state distance table is one vectorised BFS.
    """

    _shared = None

    def __init__(self):
        self.names, mv = _moves()
        pstep = lambda p, m: tuple(p[mv[m][0][i]] for i in range(8))
        tstep = lambda t, m: tuple((t[mv[m][0][i]] + mv[m][1][i]) % 3 for i in range(8))
        pidx, plst = _enumerate(tuple(range(8)), pstep)
        tidx, tlst = _enumerate((0,) * 8, tstep)
        self.PM = np.array([[pidx[pstep(p, m)] for m in range(9)] for p in plst], dtype=np.int32)
        self.TM = np.array([[tidx[tstep(t, m)] for m in range(9)] for t in tlst], dtype=np.int32)
        self.NT = len(tlst)
        self.pdb_perm = _bfs_1d(self.PM)
        self.pdb_twist = _bfs_1d(self.TM)
        self.dist = self._load_or_build()
        self._by_depth = {}

    def _load_or_build(self):
        if _CACHE.exists():
            return np.load(_CACHE)
        NT = self.NT
        dist = np.full(len(self.PM) * NT, -1, dtype=np.int8)
        dist[0] = 0
        frontier, d = np.array([0], dtype=np.int64), 0
        while len(frontier):
            d += 1
            p, t = frontier // NT, frontier % NT
            nxt = np.unique(np.concatenate([self.PM[p, m].astype(np.int64) * NT + self.TM[t, m] for m in range(9)]))
            nxt = nxt[dist[nxt] < 0]
            dist[nxt] = d
            frontier = nxt
        _CACHE.parent.mkdir(exist_ok=True)
        np.save(_CACHE, dist)
        return dist

    @classmethod
    def shared(cls):
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def neighbors(self, s):
        p, t = s
        for m, name in enumerate(self.names):
            yield name, (int(self.PM[p, m]), int(self.TM[t, m])), 1.0

    def is_goal(self, s):
        return s == (0, 0)

    def h(self, s):
        return float(max(self.pdb_perm[s[0]], self.pdb_twist[s[1]]))

    def res(self, s, a, s2):
        return 2.0 if a.endswith("2") else 1.0

    def exact_dist(self, s):
        return float(self.dist[s[0] * self.NT + s[1]])

    def random_start(self, rng, depth):
        if depth not in self._by_depth:
            self._by_depth[depth] = np.flatnonzero(self.dist == depth)
        ids = self._by_depth[depth]
        return divmod(int(ids[rng.randrange(len(ids))]), self.NT) if len(ids) else None
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_cube2.py -v`
Expected: 6 passed (first run about 15 s while the distance table is built; later runs load `.cache/cube2_dist.npy`).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Rubik's 2x2x2 benchmark with pattern-database heuristic"
```

---

### Task 7: CP-SAT ILP solver

**Files:**
- Create: `tapegraph/solvers/ilp.py`, `tests/test_ilp.py`

**Interfaces:**
- Consumes: `Problem`, `make_result`, `fail`, `INF`; `River`; `astar`, `bfs`; `tests/toy.py::GRAPH`.
- Produces:
  - `ORTOOLS_AVAILABLE: bool`
  - `solve_graph(start, goals, edges, res_budget=None, cost_budget=None, time_limit=10.0) -> list[(u, a, v)] | None`; `edges` is `[(u, a, v, cost, res)]`
  - `graph_path_bfs(start, goals, edges) -> list[(u, a, v)] | None` (no ortools needed; same return format)
  - `solve(problem, start, budget=INF, res_budget=None, max_nodes=200_000, time_limit=10.0) -> Result`; builds the subgraph of nodes with `g + h <= budget` (status `too_large` if it exceeds `max_nodes`), then runs `solve_graph` with `cost_budget=budget`.

- [ ] **Step 1: Write the failing tests**

`tests/test_ilp.py`:
```python
import math
import random

import pytest

pytest.importorskip("ortools")

from toy import GRAPH
from tapegraph.problems.river import River
from tapegraph.solvers import astar, bfs, ilp


def test_ilp_finds_shortest_on_toy_graph():
    r = ilp.solve(GRAPH, "A")
    assert r.status == "ok" and r.path == ["ab", "be"] and r.cost == 2


def test_ilp_length_budget():
    assert ilp.solve(GRAPH, "A", budget=1).status == "no_path"


def test_ilp_resource_budget_forces_longer_path():
    r = ilp.solve(GRAPH, "A", res_budget=4)
    assert r.status == "ok" and r.path == ["ac", "cd", "de"] and r.res == 3
    assert ilp.solve(GRAPH, "A", res_budget=2).status == "no_path"


def test_ilp_start_is_goal():
    assert ilp.solve(GRAPH, "E").path == []


def test_ilp_matches_bfs_from_every_river_state():
    p = River(8, 4)
    for s, d in p.dist.items():
        if d == 0:
            continue
        b = bfs.solve(p, s)
        i = ilp.solve(p, s, budget=b.cost + 2)
        assert i.status == "ok" and i.cost == b.cost, s


def test_ilp_matches_constrained_astar_on_river():
    p = River(8, 4)
    checked = 0
    for s, d in sorted(p.dist.items()):
        if d < 4:
            continue
        B = d + 2
        base = astar.solve(p, s, budget=B)
        R = math.floor(0.9 * base.res)
        a = astar.solve(p, s, budget=B, res_budget=R)
        i = ilp.solve(p, s, budget=B, res_budget=R)
        assert a.status == i.status, (s, R)
        if a.status == "ok":
            assert a.cost == i.cost, (s, R)
            checked += 1
    assert checked > 0


def test_ilp_reports_too_large_instead_of_truncating():
    p = River(8, 4)
    s = p.random_start(random.Random(0), 10)
    assert ilp.solve(p, s, budget=20, max_nodes=3).status == "too_large"


def test_graph_path_bfs_same_format_as_ilp():
    edges = [("A", "ab", "B", 1, 1), ("B", "be", "E", 1, 5)]
    assert ilp.graph_path_bfs("A", {"E"}, edges) == [("A", "ab", "B"), ("B", "be", "E")]
    assert ilp.solve_graph("A", {"E"}, edges) == [("A", "ab", "B"), ("B", "be", "E")]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_ilp.py -v`
Expected: ERROR (`cannot import name 'ilp'`). Without `ortools` installed the file is skipped; install it first (Task 1 Step 1).

- [ ] **Step 3: Implement**

`tapegraph/solvers/ilp.py`:
```python
from __future__ import annotations

import time
from collections import defaultdict, deque

from ..problem import INF, fail, make_result

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:  # the rest of the package works without it
    cp_model = None
    ORTOOLS_AVAILABLE = False

SCALE = 1000  # CP-SAT needs integers


def solve_graph(start, goals, edges, res_budget=None, cost_budget=None, time_limit=10.0):
    """Min-cost start->goal path on an explicit graph as a unit-flow ILP.

    edges: [(u, action, v, cost, res)]. Costs are positive, so the optimum is a simple path.
    """
    if not ORTOOLS_AVAILABLE:
        raise RuntimeError("OR-Tools not available. Install with: pip install ortools")
    out, inn = defaultdict(list), defaultdict(list)
    for i, (u, _, v, _, _) in enumerate(edges):
        out[u].append(i)
        inn[v].append(i)
    nodes = set(out) | set(inn) | {start}
    sinks = [g for g in goals if g in nodes]
    if not sinks:
        return None
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{i}") for i in range(len(edges))]
    z = {g: m.NewBoolVar(f"z{j}") for j, g in enumerate(sinks)}
    m.Add(sum(z.values()) == 1)  # exactly one goal ends the path
    for n in nodes:
        # outflow - inflow = [n is start] - [n is the chosen goal]
        m.Add(sum(x[i] for i in out[n]) - sum(x[i] for i in inn[n]) == (1 if n == start else 0) - z.get(n, 0))
    cost = [int(round(e[3] * SCALE)) for e in edges]
    if cost_budget is not None and cost_budget != INF:
        m.Add(sum(c * xi for c, xi in zip(cost, x)) <= int(round(cost_budget * SCALE)))
    if res_budget is not None:
        m.Add(sum(int(round(e[4] * SCALE)) * xi for e, xi in zip(edges, x)) <= int(round(res_budget * SCALE)))
    m.Minimize(sum(c * xi for c, xi in zip(cost, x)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    if solver.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    path, cur, seen = [], start, {start}
    while not (cur in z and solver.Value(z[cur])):
        step = [i for i in out[cur] if solver.Value(x[i])]
        if not step:
            return None
        u, a, v, _, _ = edges[step[0]]
        path.append((u, a, v))
        cur = v
        if cur in seen:  # only possible for a non-optimal answer at the time limit
            return None
        seen.add(cur)
    return path


def graph_path_bfs(start, goals, edges):
    """Fewest-edge path on an explicit graph; same return format as solve_graph, no ortools needed."""
    out = defaultdict(list)
    for u, a, v, _, _ in edges:
        out[u].append((a, v))
    parent, q = {start: None}, deque([start])
    while q:
        u = q.popleft()
        if u in goals:
            path, x = [], u
            while parent[x] is not None:
                pu, pa = parent[x]
                path.append((pu, pa, x))
                x = pu
            return path[::-1]
        for a, v in out[u]:
            if v not in parent:
                parent[v] = (u, a)
                q.append(v)
    return None


def solve(problem, start, budget=INF, res_budget=None, max_nodes=200_000, time_limit=10.0):
    """ILP on the bounded subgraph {g + h <= budget} (the same ball A* would expand), capped at max_nodes.

    ponytail: BFS layering for g assumes unit edge cost.
    """
    t0 = time.perf_counter()
    if problem.is_goal(start):
        return make_result(problem, start, [], 0, t0)
    if problem.prune(start):
        return fail("no_path", 0, t0)
    g = {start: 0}
    edges, q = [], deque([start])
    while q:
        u = q.popleft()
        if problem.is_goal(u):
            continue
        for a, v, c in problem.neighbors(u):
            if problem.prune(v) or g[u] + c + problem.h(v) > budget:
                continue
            edges.append((u, a, v, c, problem.res(u, a, v)))
            if v not in g:
                if len(g) >= max_nodes:
                    return fail("too_large", len(g), t0)
                g[v] = g[u] + c
                q.append(v)
    goals = {u for u in g if problem.is_goal(u)}
    path = solve_graph(start, goals, edges, res_budget, budget, time_limit) if goals else None
    if not path:
        return fail("no_path", len(g), t0)
    return make_result(problem, start, [a for _, a, _ in path], len(g), t0)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_ilp.py -v`
Expected: 8 passed. If `test_ilp_matches_constrained_astar_on_river` reports a status or cost disagreement, print `(s, R, a.path, i.path)`; both are exact, so a disagreement is a bug in the subgraph construction (edges dropped by the `g + c + h > budget` filter) or in A* dominance.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: CP-SAT flow ILP solver with resource budget and graph fallback"
```

---

### Task 8: Execution loop and baselines (ReAct-sim, TAPE-sim, Replan)

**Files:**
- Create: `tapegraph/execute.py`, `tapegraph/baselines/__init__.py` (empty), `tapegraph/baselines/react_sim.py`, `tapegraph/baselines/tape_sim.py`, `tapegraph/baselines/replan.py`, `tests/test_baselines.py`

**Interfaces:**
- Consumes: `Problem.step/neighbors/is_goal`, `Oracle`, `ilp.solve_graph`, `ilp.graph_path_bfs`, `ilp.ORTOOLS_AVAILABLE`, solver functions with signature `(problem, start, budget=..., **cfg) -> Result`.
- Produces: a policy protocol: `reset(seed)`, `act(s, rem) -> action`, attribute `solves` (cumulative re-plan count).
  - `run_episode(problem, policy, start, B, eta, rng) -> (success: bool, steps: int)`; with probability `eta` the executed action is replaced by a different legal action.
  - `evaluate(problem, start, policy, B, eta, episodes, seed) -> {"success", "mean_steps", "solves", "seconds"}` (per-episode means).
  - `noisy_recommend(problem, oracle, rng, s, rem, delta) -> action`
  - `ReActSim(problem, oracle, delta)`, `TapeSim(problem, oracle, delta, N=16, use_ilp=True)`, `Replan(problem, solver, **cfg)`

- [ ] **Step 1: Write the failing tests**

`tests/test_baselines.py`:
```python
import random

from tapegraph.baselines.react_sim import ReActSim
from tapegraph.baselines.replan import Replan
from tapegraph.baselines.tape_sim import TapeSim
from tapegraph.execute import evaluate, run_episode
from tapegraph.oracle import Oracle
from tapegraph.problems.river import River
from tapegraph.solvers import astar


def _river_case(depth=10, seed=0):
    p = River(8, 4)
    return p, Oracle(p), p.random_start(random.Random(seed), depth)


def test_noise_free_react_is_optimal():
    p, o, s = _river_case()
    ok, steps = run_episode(p, ReActSim(p, o, delta=0.0), s, B=12, eta=0.0, rng=random.Random(0))
    assert ok and steps == 10


def test_react_with_always_wrong_planning_fails_at_zero_slack():
    p, o, s = _river_case()
    r = evaluate(p, s, ReActSim(p, o, delta=1.0), B=10, eta=0.0, episodes=20, seed=0)
    assert r["success"] < 0.5


def test_replan_is_optimal_without_noise_and_solves_once():
    p, o, s = _river_case()
    pol = Replan(p, astar.solve)
    r = evaluate(p, s, pol, B=10, eta=0.0, episodes=5, seed=0)
    assert r["success"] == 1.0 and r["mean_steps"] == 10 and r["solves"] == 1.0


def test_replan_recovers_from_a_deviation():
    p, o, s = _river_case()
    pol = Replan(p, astar.solve)
    pol.reset(0)
    a = pol.act(s, 12)
    other = next(a2 for a2, _, _ in p.neighbors(s) if a2 != a)
    s_dev = p.step(s, other)  # the world did something else
    a2 = pol.act(s_dev, 11)
    assert pol.solves == 2
    assert o.dist(p.step(s_dev, a2)) <= 11  # the new plan starts from the observed state


def test_tape_sim_without_planning_error_succeeds():
    p, o, s = _river_case()
    pol = TapeSim(p, o, delta=0.0, N=2, use_ilp=False)
    r = evaluate(p, s, pol, B=12, eta=0.0, episodes=5, seed=0)
    assert r["success"] == 1.0


def test_replan_beats_react_under_noise():
    p, o, s = _river_case(depth=12)
    B, eta, delta = 12 + 2, 0.04, 0.16
    react = evaluate(p, s, ReActSim(p, o, delta), B, eta, episodes=100, seed=1)
    ours = evaluate(p, s, Replan(p, astar.solve), B, eta, episodes=100, seed=1)
    assert ours["success"] > react["success"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_baselines.py -v`
Expected: ERROR (`No module named 'tapegraph.baselines'`).

- [ ] **Step 3: Implement `execute.py`**

```python
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
        "seconds": (time.perf_counter() - t0) / episodes,
    }
```

- [ ] **Step 4: Implement `baselines/react_sim.py`**

```python
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
```

- [ ] **Step 5: Implement `baselines/tape_sim.py`**

```python
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
        path = pick(s, goals, [(u, a, v, 1.0, 1.0) for u, a, v in sorted(edges, key=repr)])
        if path:
            self.plan = deque((a, v) for _, a, v in path)
```

- [ ] **Step 6: Implement `baselines/replan.py`**

```python
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
```

- [ ] **Step 7: Run to verify pass**

Run: `python -m pytest tests/test_baselines.py -v`
Expected: 6 passed. `test_replan_beats_react_under_noise` is seeded but statistical; if it fails, print both success rates before changing anything, they should differ by far more than one episode.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: episode loop, ReAct-sim, TAPE-sim and re-planning baselines"
```

---

### Task 9: Benchmarks registry and the bench CLI

**Files:**
- Create: `tapegraph/benchmarks.py`, `tapegraph/bench.py`, `tests/test_bench.py`

**Interfaces:**
- Consumes: all problems, `Oracle`, solvers, baselines, `evaluate`.
- Produces:
  - `BENCHMARKS: dict[str, Bench]`, `Bench(make, T_targets, exact=False, depth=(10, 60))`
  - `make_instances(name, per_bucket, seed, tol=1, max_tries=5000) -> list[Instance]`, `Instance(problem, start, T, oracle)`
  - CLI `python -m tapegraph.bench {solvers|agents|constrained|report}`; CSVs in `results/`, report in `results/results.md`.

- [ ] **Step 1: Write the failing tests**

`tests/test_bench.py`:
```python
import csv
import sys

from tapegraph import bench
from tapegraph.benchmarks import BENCHMARKS, make_instances


def test_make_instances_fills_buckets_with_true_distances():
    insts = make_instances("river", per_bucket=2, seed=0)
    assert len(insts) == 2 * len(BENCHMARKS["river"].T_targets)
    for i in insts:
        assert i.oracle.dist(i.start) == i.T


def test_cli_end_to_end_on_river(tmp_path, monkeypatch):
    out = str(tmp_path)
    for cmd in ("solvers", "agents", "constrained"):
        monkeypatch.setattr(sys, "argv", ["bench", cmd, "--bench", "river", "--n", "1", "--episodes", "3", "--out", out])
        bench.main()
    monkeypatch.setattr(sys, "argv", ["bench", "report", "--out", out])
    bench.main()
    rows = list(csv.DictReader(open(tmp_path / "solvers_river.csv")))
    assert {r["solver"] for r in rows} >= {"bfs", "astar", "wastar", "idastar"}
    assert all(r["status"] == "ok" for r in rows if r["solver"] == "astar")
    agents = {r["method"] for r in csv.DictReader(open(tmp_path / "agents_river.csv"))}
    assert agents >= {"react", "tape", "ours_astar"}
    assert "river" in (tmp_path / "results.md").read_text()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_bench.py -v`
Expected: ERROR (`cannot import name 'bench'`).

- [ ] **Step 3: Implement `benchmarks.py`**

```python
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
    "sokoban": Bench(lambda rng: Sokoban.random_level(rng, 7, 9, 1, 0.08), [6, 10, 14, 18, 22], depth=(10, 60)),
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
```

- [ ] **Step 4: Implement `bench.py`**

```python
"""Usage: python -m tapegraph.bench {solvers|agents|constrained|report} --bench river --n 5 --out results"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from functools import partial
from pathlib import Path
from statistics import mean

from .baselines.react_sim import ReActSim
from .baselines.replan import Replan
from .baselines.tape_sim import TapeSim
from .benchmarks import BENCHMARKS, make_instances
from .execute import evaluate
from .solvers import astar, bfs, idastar, ilp

SOLVERS = {
    "bfs": bfs.solve,
    "astar": astar.solve,
    "wastar": partial(astar.solve, w=2.0),
    "idastar": idastar.solve,
    "ilp": ilp.solve,
}


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"[saved] {path} ({len(rows)} rows)")


def _usable(name):
    return name != "ilp" or ilp.ORTOOLS_AVAILABLE


def run_solvers(a):
    rows = []
    for inst in make_instances(a.bench, a.n, a.seed):
        B = inst.T + a.slack
        for name in a.solvers:
            if not _usable(name):
                continue
            r = SOLVERS[name](inst.problem, inst.start, budget=B, max_nodes=a.max_nodes)
            rows.append({
                "bench": a.bench, "T": inst.T, "solver": name, "status": r.status, "ok": int(r.status == "ok"),
                "cost_ratio": r.cost / inst.T if r.status == "ok" else "",
                "nodes": r.nodes, "seconds": round(r.seconds, 5),
            })
    _write(Path(a.out) / f"solvers_{a.bench}.csv", rows)


def run_agents(a):
    rows = []
    for inst in make_instances(a.bench, a.n, a.seed):
        p, o, B = inst.problem, inst.oracle, inst.T + a.slack
        makers = {
            "react": lambda: ReActSim(p, o, a.delta),
            "tape": lambda: TapeSim(p, o, a.delta, N=a.N),
            "ours_astar": lambda: Replan(p, astar.solve, max_nodes=a.max_nodes),
        }
        if ilp.ORTOOLS_AVAILABLE:
            makers["ours_ilp"] = lambda: Replan(p, ilp.solve, max_nodes=a.max_nodes)
        for name, mk in makers.items():
            r = evaluate(p, inst.start, mk(), B, a.eta, a.episodes, a.seed)
            rows.append({"bench": a.bench, "T": inst.T, "method": name, **{k: round(v, 5) for k, v in r.items()}})
    _write(Path(a.out) / f"agents_{a.bench}.csv", rows)


def run_constrained(a):
    """min length s.t. length <= T*+slack and resource <= floor(res_frac * resource of the unconstrained optimum)."""
    rows, skipped = [], 0
    for inst in make_instances(a.bench, a.n, a.seed):
        p, B = inst.problem, inst.T + a.slack
        base = astar.solve(p, inst.start, budget=B, max_nodes=a.max_nodes)
        if base.status != "ok":
            skipped += 1
            continue
        R = math.floor(a.res_frac * base.res)
        results = {n: SOLVERS[n](p, inst.start, budget=B, res_budget=R, max_nodes=a.max_nodes)
                   for n in ("astar", "ilp") if _usable(n)}
        if results["astar"].status != "ok":  # infeasible at this resource budget
            skipped += 1
            continue
        for n, r in results.items():
            rows.append({
                "bench": a.bench, "T": inst.T, "solver": n, "status": r.status, "ok": int(r.status == "ok"), "R": R,
                "cost": r.cost if r.status == "ok" else "",
                "agrees_with_astar": int(r.status == results["astar"].status and r.cost == results["astar"].cost),
                "nodes": r.nodes, "seconds": round(r.seconds, 5),
            })
    print(f"[constrained] skipped {skipped} infeasible/unsolved instances")
    _write(Path(a.out) / f"constrained_{a.bench}.csv", rows)


def _num(v):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def summarize(rows, group, metrics):
    buckets = defaultdict(list)
    for r in rows:
        buckets[tuple(r[k] for k in group)].append(r)
    out = []
    for key, rs in sorted(buckets.items(), key=lambda kv: kv[0]):  # each key position has one type: bench str, T int, name str
        row = dict(zip(group, key), n=len(rs))
        for m in metrics:
            vals = [float(r[m]) for r in rs if r.get(m) not in ("", None)]
            row[m] = round(mean(vals), 4) if vals else ""
        out.append(row)
    return out


def _md(rows):
    if not rows:
        return "_no data_\n"
    keys = list(rows[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def run_report(a):
    out = Path(a.out)
    sections = [
        ("Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap)", "solvers_*.csv",
         ["bench", "T", "solver"], ["ok", "cost_ratio", "nodes", "seconds"]),
        ("Agents (success within budget under noise)", "agents_*.csv", ["bench", "T", "method"],
         ["success", "mean_steps", "solves", "seconds"]),
        ("Constrained (length + resource budget; agrees_with_astar = rate of identical status and cost)",
         "constrained_*.csv", ["bench", "T", "solver"], ["ok", "agrees_with_astar", "cost", "nodes", "seconds"]),
    ]
    md = ["# Results\n"]
    for title, pattern, group, metrics in sections:
        rows = []
        for f in sorted(out.glob(pattern)):
            rows += [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(open(f))]
        md.append(f"## {title}\n\n" + _md(summarize(rows, group, metrics)))
    (out / "results.md").write_text("\n".join(md))
    print(f"[saved] {out / 'results.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["solvers", "agents", "constrained", "report"])
    ap.add_argument("--bench", choices=list(BENCHMARKS), default="river")
    ap.add_argument("--n", type=int, default=5, help="instances per T* bucket")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--slack", type=int, default=2)
    ap.add_argument("--max_nodes", type=int, default=500_000)
    ap.add_argument("--solvers", nargs="+", default=list(SOLVERS))
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--delta", type=float, default=0.16, help="planning error rate (ReAct/TAPE sim)")
    ap.add_argument("--eta", type=float, default=0.04, help="execution noise rate")
    ap.add_argument("--N", type=int, default=16, help="rollouts folded by TAPE-sim")
    ap.add_argument("--res_frac", type=float, default=0.9, help="constrained: resource budget as a fraction of the optimum's")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    {"solvers": run_solvers, "agents": run_agents, "constrained": run_constrained, "report": run_report}[a.cmd](a)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_bench.py -v`
Expected: 2 passed.

- [ ] **Step 6: Tune the Sokoban-family buckets (one-off)**

```bash
python -m tapegraph.bench solvers --bench sokoban --n 2 --out results_tmp
python -m tapegraph.bench solvers --bench boxoban --n 1 --out results_tmp
```
Expected: sokoban reports 2 instances for each of T = 6, 10, 14, 18, 22. If a bucket stays empty for boxoban (the script silently produces fewer rows), widen `depth=(…)` or `T_targets` for `boxoban` in `benchmarks.py` until all four buckets fill within a minute, then `rm -r results_tmp`. Do not raise `max_tries` above 20000.

- [ ] **Step 7: Run the full test suite and commit**

Run: `python -m pytest -q`
Expected: all pass (ILP tests skip if `ortools` is missing).

```bash
git add -A && git commit -m "feat: benchmark registry and bench CLI (solvers, agents, constrained, report)"
```

---

### Task 10: README, full run, findings

**Files:**
- Create: `README.md`
- Modify: `README.md` (Findings section, after the run)

- [ ] **Step 1: Write `README.md`** (the algorithm write-up; no results yet)

````markdown
# tape-graph: TAPE as an LLM-free path-finding algorithm

> Given an implicit state graph G, a random start s0 and a goal set, find a minimum-cost feasible path under
> budget B. Fold candidate paths into a graph, solve for the best constrained path, execute one step, and
> re-solve from the state the world actually returned.

TAPE (Jeong, Kim, Lee 2026) uses an LLM to propose plans, folds them into a graph, and picks a path with an ILP.
This project removes the LLM and asks what is left: a planning loop over a state graph. Two changes:

1. **No LLM.** Benchmarks have a fixed goal and a random start (Sokoban, Boxoban-style, River Crossing, Rubik's
   2x2x2), so state structuring and merging are exact and cannot be gotten wrong by a model.
2. **More than one solver.** BFS, A*, weighted A*, IDA* and the CP-SAT ILP all run on the same graph, each with
   its own graph constraints (dead-end pruning, `g+h <= B` cut, bounded explicit subgraph for the ILP, resource
   budgets).

ReAct and TAPE are *simulated* with the paper's noise model (`delta` planning error, `eta` execution noise), so
they are models of LLM behaviour, not real LLM runs.

## Run

```bash
pip install -r requirements.txt
python -m pytest -q
for b in river sokoban boxoban cube2; do
  python -m tapegraph.bench solvers     --bench $b --n 5
  python -m tapegraph.bench agents      --bench $b --n 5 --episodes 100
  python -m tapegraph.bench constrained --bench $b --n 5
done
python -m tapegraph.bench report        # writes results/results.md
```

## Layout

See `docs/superpowers/specs/2026-10-22-tape-graph-design.md`.
````

- [ ] **Step 2: Run the full benchmark**

Run the loop from the README (it can take several minutes; `cube2` BFS hits `--max_nodes` by design and is reported as `node_limit`). If `boxoban` agents are too slow, lower `--episodes` to 20 for that benchmark and say so in the Findings.

Expected: `results/*.csv` and `results/results.md` exist.

- [ ] **Step 3: Write the Findings section from the data**

Read `results/results.md` and append a `## Findings` section to `README.md` stating only what the tables show, in these four points: (1) which solvers matched `T*` and at what node/time cost per benchmark; (2) where BFS or the ILP hit `node_limit`/`too_large`; (3) in the constrained table, whether the ILP or resource-constrained A* was faster and whether they always agreed; (4) success rates of ReAct-sim vs TAPE-sim vs ours as `T*` grows, noting that reversible domains (River, Cube) absorb errors via slack while Sokoban/Boxoban pushes can be irrecoverable. If the ILP never wins anywhere, say so plainly.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "docs: README with algorithm statement and measured findings"
```
