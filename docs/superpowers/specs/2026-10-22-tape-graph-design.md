# tape-graph: TAPE as an LLM-free path-finding algorithm

Status: draft for review. Date: 2026-10-22.

## 1. Goal

Present TAPE's core loop as a standalone algorithm, with the LLM removed:

> Given an implicit state graph G, a random start s0 and a goal set, find a
> minimum-cost feasible path under budget B. Fold candidate paths into a graph,
> solve for the best constrained path, execute one step, and re-solve from the
> state the world actually returned.

It tackles two drawbacks of TAPE:

1. **LLM dependence.** In TAPE the LLM proposes the plans that are folded into
   the graph, so quality depends on the model structuring and merging states
   correctly. Here the state graph comes from a benchmark with a fixed goal and
   a random start, so no model is involved.
2. **One solver (the ILP).** TAPE solves every instance with a CP-SAT ILP. Here
   graph solvers (BFS, A*, weighted A*, IDA*) are compared against the ILP, and
   each solver gets its own graph constraints.

Results compare this project against simulated ReAct and simulated TAPE.

## 2. Scope

In scope: four benchmarks, five solvers, simulated ReAct/TAPE baselines, an
unconstrained and a resource-constrained comparison, a results table, and a
README that states the algorithm.

Out of scope: real-LLM runs, DeepMind's Boxoban level files (one loader
function can be added later), Rubik's 3x3, learned heuristics. Long-horizon
planning with an LLM proposer is not part of this project.

The existing project `TAPE-main` is not modified. The Sokoban env and level
generator are copied into the new project.

## 3. Layout

```
tape-graph/
  tapegraph/
    problem.py        # Problem protocol, Result dataclass
    problems/         # sokoban.py  boxoban.py  river.py  cube2.py
    solvers/          # bfs.py  astar.py  idastar.py  ilp.py
    oracle.py         # exact distance-to-goal for the simulated baselines
    execute.py        # episode loop with execution noise
    baselines/        # react_sim.py  tape_sim.py  replan.py
    benchmarks.py     # benchmark registry, T*-bucketed instance generation
    bench.py          # runs the grid, writes results/*.csv + results.md
  tests/
  README.md
```

## 4. Problem interface

| Method | Meaning |
|---|---|
| `neighbors(s)` | yields `(action, s', cost)`; states are hashable |
| `is_goal(s)` | goal test |
| `h(s)` | admissible lower bound on remaining cost |
| `prune(s)` | True for a provable dead end (Sokoban corner deadlock); default False |
| `random_start(rng, depth)` | random start made by reverse-play or scrambling from the goal, so a solution always exists |

Difficulty is the optimal length `T*`. Each generated start gets its true `T*`
from BFS and is placed in a `T*` bucket within a tolerance, as in TAPE.

Benchmarks:

- **Sokoban:** copied env; `h` is the sum over boxes of distance to the nearest goal.
- **Boxoban:** same env, 10x10 with 4 boxes, generated locally (no download).
- **River Crossing:** parameterised missionaries/cannibals; boat size and group sizes set difficulty.
- **Rubik's 2x2x2:** permutation-table moves; `h` is the max of a corner-orientation and a corner-permutation pattern database (admissible, not exact).

## 5. Solvers

One signature: `solve(problem, start, budget, **cfg) -> Result(path, cost, nodes, seconds, status)`.

| Solver | Graph it sees | Constraint adjustments |
|---|---|---|
| BFS | implicit graph | none; oracle for `T*` and correctness |
| A* | implicit graph | `prune()` dead ends; drop nodes with `g+h > budget` |
| Weighted A* | same | weight `w > 1`; reported as cost ratio vs `T*` |
| IDA* | same | depth-bounded DFS with a transposition table |
| CP-SAT ILP | explicit subgraph of nodes with `g+h <= budget`, capped at `max_nodes` | length budget; optional resource budget. Edge-flow formulation (one binary per edge), not `select_path_ilp`'s time-expanded model: costs are positive so the optimum is a simple path, and the model is `L` times smaller |

The ILP gets the same bounded subgraph the A* family would expand, so the
comparison is fair. If the subgraph exceeds `max_nodes` the ILP reports
`status="too_large"`; it does not silently truncate.

**Constrained variant.** Every edge carries a second resource (fuel or time).
Solvers take a `cost_budget`. A* becomes label-setting search over
`(state, spent)`; the ILP adds one linear constraint. This is the case where
the ILP may win, and the results must report it either way.

## 6. Baselines and the execution loop

All use the `Problem` interface and the noise knobs of `TAPE-main/src/agents/`.

- **ReAct-sim:** the oracle's next action; with probability `delta` a wrong action; with probability `eta` a different action than intended executes. No recovery.
- **TAPE-sim:** N oracle rollouts with error rate `delta`, folded into a graph, ILP picks a path, one step executes, re-plan on deviation. Generalises `OursGraphILPPolicy` from Sokoban's `State` to any `Problem`.
- **Ours:** one step of a chosen solver on the true graph, execute, re-plan from the observed state. Execution noise `eta` still applies.

## 7. Metrics and outputs

Per benchmark, per `T*` bucket, per method, over N episodes:

1. success rate within budget `B = T* + slack`
2. path length / `T*`
3. nodes expanded
4. wall-clock seconds

Outputs: `results/*.csv` and a generated `results.md`. No plots in v1 (tables
only; `matplotlib` not required). The write-up must not claim the ILP is beaten on
unconstrained problems unless the data shows it; on plain shortest path an exact
ILP can at most match A* on optimality.

## 8. Testing

Plain `assert`-based scripts or pytest, no other framework.

- On every benchmark, BFS, A* and IDA* return equal costs, and the ILP matches on small instances. An inadmissible `h` shows up as a longer path than BFS.
- Each generator returns solvable starts, and BFS `T*` falls in the requested bucket within tolerance.
- A returned path replays through `neighbors` to the goal.
- The re-plan loop recovers from an injected execution deviation.

## 9. Environment

Python 3.12 and numpy are installed. `ortools` (for the ILP) and `pytest` are
not; they need `pip install ortools pytest`, which will be confirmed with the
user before running.
