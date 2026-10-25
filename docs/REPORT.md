# tape-graph: project report

Status at commit `0a99c92` (23 commits, 83 tests passing, about 2,150 lines of Python across package, tests and
scripts). Every number below is taken from the committed tables in `docs/` and the raw CSVs in `docs/data/`; the
README holds the same results with more per-bucket detail.

## 1. Summary

`tape-graph` takes TAPE (Jeong, Kim, Lee 2026: an LLM proposes plans, the plans are folded into a graph, an ILP picks a
path, execution is constrained and re-planned on deviation) and removes the LLM. What is left is a planning algorithm
over a state graph:

> Given an implicit state graph G, a random start s0 and a goal set, find a minimum-cost feasible path under budget B.
> Fold candidate paths into a graph, solve for the best constrained path, execute one step, and re-solve from the state
> the world actually returned.

Headline results, on four benchmarks (Sokoban, Boxoban-style, River Crossing, Rubik's 2x2x2):

1. **The solvers are exact and cheap.** BFS, A*, IDA* and the ILP never returned a path longer than the optimum `T*` on any
   instance they solved. A* with a pattern-database or distance heuristic handles every instance; weighted A* (w = 2) is
   fastest and was at most 14.3% longer than optimal (8/7), and exactly optimal on River and Sokoban.
2. **The ILP never won.** In the unconstrained comparison it is the slowest solver in every bucket except Cube `T*` 11,
   where it solved 0 of 5. In the resource-constrained comparison it matched A*'s cost on all 110 instance pairs where both
   solved, and was 49x to 228x slower. The only rows where it was faster are rows where it failed fast.
3. **Re-planning on the true graph beats the simulated ReAct by 43 to 63 points** (pooled success) and matches the
   simulated TAPE. The match is close to built in (limitation 2 in section 7): the real difference between the LLM-free
   loop and TAPE is cost, not success rate.
4. **Everything that is simulated is labelled as such.** ReAct and TAPE are models of LLM behaviour using the paper's
   noise model (planning error `delta` = 0.16, execution noise `eta` = 0.04), not LLM runs.

## 2. How the project maps to the original goals

| Your goal | Where it landed |
|---|---|
| 1. Showcase TAPE as an algorithm: best path to a goal from a random start | The algorithm statement above and `README.md`; implemented as `Replan` (`tapegraph/baselines/replan.py`) over any `Problem` |
| 2. LLM + algorithm gives long-horizon planning (not our scope) | Out of scope, as agreed. The loop's planner is an interface (`solver(problem, start, budget=...)`), so an LLM proposer could replace the oracle later |
| 3a. No LLM; benchmarks with a set goal and random start (Sokoban, Boxoban, Rubik's, River Crossing) | Four benchmarks, each with a random-start generator and a true `T*` for every instance (sections 3.3 and 4.1) |
| 3b. Replace the single ILP with graph solvers (A* etc.) and adjust graph constraints per algorithm | BFS, A*, weighted A*, IDA* and the CP-SAT ILP behind one signature, each with its own constraints (section 3.2) |
| 4. Compare with ReAct and TAPE | Simulated ReAct and TAPE with the paper's noise model, same instances, paired noise (sections 3.4 and 5.4) |

## 3. Architecture

```
tapegraph/
  problem.py        Problem interface, Result dataclass, res_bind (resource for the binding experiment)
  oracle.py         exact distance-to-goal for the simulated baselines (cached A*, or an exact table)
  execute.py        episode loop with execution noise; evaluate() with per-episode seeds
  benchmarks.py     registry of the four benchmarks, T*-bucketed instance generation
  bench.py          CLI: solvers | agents | constrained | report
  problems/         river.py  sokoban.py  boxoban.py  cube2.py
  solvers/          bfs.py  astar.py  idastar.py  ilp.py
  baselines/        react_sim.py  tape_sim.py  replan.py
scripts/probe_resources.py   probe of which resource definitions trade off against length
docs/               results tables, raw CSVs (docs/data/), spec, plan, this report
tests/              83 tests
```

### 3.1 The `Problem` interface

Every benchmark implements five things, and solvers depend on nothing else:

| Method | Meaning |
|---|---|
| `neighbors(s)` | yields `(action, next_state, cost)`; all costs are 1.0 |
| `is_goal(s)` | goal test |
| `h(s)` | admissible lower bound on the remaining cost |
| `prune(s)` | `True` only for a provable dead end |
| `random_start(rng, depth)` | a start with a guaranteed solution (reverse play or scrambling from the goal) |

Optional: `exact_dist(s)` (River and Cube have exact tables), `res(s, a, s2)` (a side resource) and `res_bind` (the
resource used by the binding constrained experiment).

### 3.2 Solvers and the graph constraints each one uses

All share `solve(problem, start, budget, ...) -> Result(status, path, states, cost, res, nodes, seconds)`, with statuses
`ok`, `no_path`, `node_limit`, `too_large`, `timeout`.

| Solver | Graph it sees | Constraints applied |
|---|---|---|
| BFS | the implicit graph | none; deliberately ignores `h` and `prune`, so it is the independent reference the others are checked against |
| A* | the implicit graph | `prune()` dead ends; drop nodes with `g + h > budget`; optional resource budget via label-setting with dominance (stays exact) |
| Weighted A* (w = 2) | same | same, with `f = g + w*h`; reported as a cost ratio against `T*` |
| IDA* | same | depth-bounded DFS with a per-iteration transposition table |
| CP-SAT ILP | an explicit subgraph: the ball `{g + h <= budget}`, capped at `max_nodes` | edge-flow ILP (one binary per edge); length budget; optional resource budget; 10 s solver limit; 8 workers |

Deliberate deviation from TAPE: the ILP is an **edge-flow** model, not TAPE's time-expanded one. Costs are positive, so the
optimum is a simple path and the model is `L` times smaller. The time-expanded form is needed only for node-score
objectives, which this project does not use.

### 3.3 Benchmarks

| Benchmark | State | Heuristic | Dead-end prune | Random start |
|---|---|---|---|---|
| Sokoban (7x9, 1 box) | player + sorted boxes | sum over boxes of Manhattan distance to the nearest goal | static dead cells (cells from which no goal is reachable by pushes, ignoring other boxes) | reverse play from a solved layout |
| Boxoban-style (10x10, 4 boxes) | same | same | same | same, generated locally (no download) |
| River Crossing (8 missionaries/cannibals, boat 4) | (missionaries left, cannibals left, boat) | trip-count lower bound | none | a state with exact distance `T*` from an exact table |
| Rubik's 2x2x2 (half-turn metric, 9 moves) | (corner permutation, corner twist) | max of two pattern databases (5,040 and 729 entries) | none | a uniformly random state at exact depth `T*` |

The cube's two coordinates evolve independently under every move, so the full 3,674,160-state distance table is one
vectorised BFS (about 12 s once, then cached), and the depth counts reproduce the published 2x2x2 distribution exactly
(1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644; God's number 11).

### 3.4 Agents (all on the same instances, paired noise)

- **ReAct-sim:** the oracle's next action; with probability `delta` a planning error (an action that breaks the budget if
  one exists); with probability `eta` a different action than intended is executed. No recovery.
- **TAPE-sim:** 16 rollouts with the same planning error are folded into a graph; a shortest path in the folded graph
  (the real ILP on River and Sokoban, BFS on the folded graph on Boxoban and Cube) is followed; it re-plans on deviation.
- **Replan (this project, "ours"):** one step of a chosen solver on the true graph, execute, re-solve from the observed
  state on deviation. Variants `ours_astar` and `ours_ilp`. Execution noise `eta` applies to all methods in the loop.

## 4. Method

### 4.1 Instances and budgets

Instances are generated per target `T*` (accepted within +-1, reported under their true `T*`; the true `T*` is verified
against the oracle or an exact table). The budget is `B = T* + 2` unless stated. Seed 1, `--max_nodes 500000`,
`--n 5` instances per target for solvers, agents and the first constrained design. Because Sokoban and Boxoban instances
are rejection-sampled from long reverse random walks, buckets are keyed by the actual `T*` and contain 1 to 5 instances.

### 4.2 Metrics

Per benchmark, `T*` bucket and method: success within budget under noise, path length over `T*` (`cost_ratio`), nodes
expanded, wall-clock seconds, and for the constrained experiments agreement with A*, status counts and a failure
breakdown. Failures (`node_limit`, `too_large`, `timeout`, `no_path`, `no_tradeoff`) are recorded as rows, never dropped,
and cost means are over solved instances only (every table says so).

## 5. Results

### 5.1 Unconstrained solvers (`docs/results.md`)

- **Exactness.** `cost_ratio` is exactly 1.0 for every solved instance of BFS, A*, IDA* and the ILP. Weighted A* is the
  only solver that returned longer paths (mean 1.0476 at Boxoban `T*` 7; worst single instance 8/7 = 1.143).
- **River (30 instances).** The graph is tiny, so the heuristic buys nothing: A* expands 41 nodes against BFS's 40 at
  `T*` 14.
- **Sokoban (25).** At `T*` 23: BFS 536 nodes, A* 231, IDA* 2,467.5, weighted A* 167, ILP 292. A* uses fewer nodes but is not
  faster in wall-clock at this size.
- **Boxoban (20).** At `T*` 21: BFS 93,674 nodes / 0.864 s, A* 6,418 / 0.293 s, weighted A* 1,842 / 0.079 s. A* is faster
  than BFS from `T*` 16 up.
- **Cube (25).** At `T*` 11: A* 87,583 nodes / 4.38 s, IDA* 36,250 / 0.659 s, weighted A* 5,614 / 0.236 s. IDA* expands
  fewer nodes than A* at every `T*` from 5 up. BFS hit its 500,000-node cap on 7 of 25 instances.
- **Where the ILP fails.** Boxoban: 5 of 20 `timeout` (all at `T*` >= 16). Cube: 5 `timeout` (all at `T*` 9) and 5
  `too_large` (all at `T*` 11), 15 of 25 solved. It solved every River and Sokoban instance but was 34x to 136x slower than
  A* there.

### 5.2 Constrained, first design (`frac`; `docs/results.md`, `docs/results_rf95.md`)

The resource budget was a fraction of the unconstrained optimum's resource (`res_frac` 0.9, plus supplementary 0.95, 0.97
and a non-binding 1.0). It almost never made the budget bind: **all 30 solved main-table instances have `cost == T*`**,
and Sokoban (25 of 25) and Boxoban (20 of 20) were infeasible at the budget. Exactly 3 supplementary instance-runs (2
distinct instances, all Sokoban) were forced to a longer path. So this design does not test the case a resource-constrained
ILP is meant for. For Sokoban and Boxoban that is structural: the resource is steps plus 2 per push, so any budget below
the optimum's resource needs fewer pushes, which almost never exists. (This is reasoning plus A*/ILP agreement on 8
spot-checked instances, not an enumeration.)

### 5.3 Constrained, redesigned (`bind`; `docs/results_bind.md`)

A probe (`scripts/probe_resources.py`) found that the original resources are almost never in tension with length: a
cheaper longer path existed on 0 of 30 River, 0 of 8 Cube, 2 of 25 Sokoban and 0 of 3 Boxoban instances. The redesign
therefore (a) uses resources that do trade off and (b) picks the budget so it always binds and always stays feasible:

- `r_opt` = least resource among paths of length <= `T*`; `r_min` = least resource among paths of length <= `T* + 4`.
  Skip as `no_tradeoff` if `r_min >= r_opt`. Otherwise two levels: `bind` (R = `r_opt - 1`, so every length-optimal path
  is infeasible) and `tight` (R = `r_min`). A* and the ILP both run at `(T* + 4, R)`.
- `res_bind` resources: pushes only (Sokoban, Boxoban), passengers squared (River), half-turns only (Cube). They were
  chosen because they create trade-offs, so the experiment tests solver behaviour under a binding budget and says
  nothing about which resource a real application would care about.

| Benchmark | Instances | With a trade-off | A* rows ok | ILP rows ok | ILP failures | ILP/A* time (both ok) |
|---|---|---|---|---|---|---|
| River | 120 | 43 | 86 / 86 | 86 / 86 | none | 66x slower |
| Sokoban | 90 | 7 | 14 / 14 | 14 / 14 | none | 49x slower |
| Boxoban | 40 | 1 | 2 / 2 | 2 / 2 | none | 100x slower |
| Cube | 20 | 18 | 29 / 29 | 8 / 29 | 15 `too_large`, 6 `timeout` | 228x slower |

The ILP matched A*'s cost on all 110 pairs where both solved. The optimum was longer than `T*` by +2 on every River and
Sokoban row, +1 on both Boxoban rows, and +1 to +4 on Cube. (That the optimum is longer at all is a sanity check of the
construction, not a finding; the size of the increase is the content.) The only rows where the ILP was faster are 8 Cube
`T*` 11 rows where it returned `too_large` in about 3 s and A* solved them in about 8 s. On the cube the ILP solved 6 of
the 18 trade-off instances, all at `T*` <= 5.

### 5.4 Agents under noise (`docs/results.md`)

Success within budget, smallest and largest `T*` bucket (`delta` 0.16, `eta` 0.04; 100 episodes on River and Sokoban, 30
on Cube, 20 on Boxoban):

| Benchmark | T* | react | tape | ours_astar | ours_ilp |
|---|---|---|---|---|---|
| River | 4 / 14 | 0.752 / 0.246 | 0.996 / 0.922 | 0.996 / 0.94 | 0.998 / 0.938 |
| Sokoban | 5 / 23 | 0.66 / 0.05 | 0.98 / 0.755 | 0.98 / 0.81 | 0.98 / 0.80 |
| Boxoban | 7 / 21 | 0.533 / 0.05 | 0.983 / 0.80 | 0.983 / 0.817 | not run |
| Cube | 3 / 11 | 0.84 / 0.32 | 1.0 / 0.947 | 1.0 / 0.94 | not run |

Pooled over instances (react / tape / ours_astar / ours_ilp): River 0.455 / 0.951 / 0.954 / 0.959; Sokoban 0.248 / 0.862
/ 0.872 / 0.874; Boxoban 0.225 / 0.850 / 0.855 / not run; Cube 0.539 / 0.967 / 0.965 / not run. Per instance, tape beats
ours_astar on 10 of 100 instances, loses on 23, ties on 67. Success of the re-planning methods declines with `T*` in all
four benchmarks, mildly on River and Cube (never below 0.90 and 0.94) and more steeply on Sokoban and Boxoban. That is
consistent with errors being recoverable in reversible domains and irrecoverable on pushes, but the tables do not isolate
that cause (longer paths also meet more noise events).

## 6. Quality assurance: what review caught

Each task was implemented by a separate agent and reviewed by another against the spec, then the whole branch was
reviewed. The reviews changed real outcomes:

| Finding | Effect |
|---|---|
| ILP timeout and non-optimal answers were reported as `no_path` / `ok` | New `timeout` status and `IlpTimeout`; the ILP is `ok` only when proven optimal |
| Constrained comparison silently dropped instances where A* failed, biasing it toward A* | Every instance now yields a row (`skipped` with a reason); added a failure breakdown to the report |
| The Sokoban agreement test (A* vs BFS) was half trivial: many random starts were already solved | Test strengthened to require nontrivial cases |
| Every instance in a benchmark saw the same noise draws (found while writing results) | Per-instance seeds, paired across methods; all agents results re-run; the cube's "1.0 at every T" was an artifact of the bug |
| Constrained experiment never forced a longer path, and the README did not say so | Probe, redesigned `bind` experiment, re-run, README scoped honestly |
| The Boxoban/Cube agents runs were not reproducible from the CLI | `--no_ilp` flag and parameter columns in the agents CSV |
| Several README statements were stronger than the tables | Corrected, hedged, and every number re-verified against the CSVs |

## 7. Limitations and threats to validity

1. **The baselines are simulated.** ReAct-sim and TAPE-sim use the paper's noise model; they say nothing about how a real
   LLM behaves. The 43 to 63 point gap to ReAct-sim comes from the modelling assumption that planning errors are injected
   unfiltered and never corrected.
2. **TAPE-sim and `ours` are close by construction (section 3.4).** TAPE-sim's rollouts come from an exact oracle with 16%
   errors; 16 of them and a shortest path in the folded graph yield (close to) an optimal path of the true graph, which is
   what `ours` follows. They have identical success on 67 of 100 instance rows. The real difference is cost (no oracle, no
   rollouts, no ILP), not success.
3. **Constrained evidence is thin outside River and Cube.** Sokoban has 7 trade-off instances and Boxoban 1; the `bind`
   resources are unusual by design; `c_slack` was not varied; A* `ok` at the `tight` level partly repeats the bisection's last
   probe, so the informative number is the ILP's behaviour, not A*'s solve rate.
4. **Fairness is approximate.** The ILP's subgraph is the `{g + h <= T* + slack}` ball (larger than A*'s region), its graph
   build counts toward its time, it runs 8 workers against single-threaded A*, and it has a 10 s limit A* lacks.
5. **Reduced runs.** Boxoban agents used 20 episodes and Cube 30, both with the ILP disabled (no `ours_ilp` rows; `tape`
   there used BFS on the folded graph). Buckets hold 1 to 5 instances, so success differences of a few points are within noise.
6. **Timing columns.** The agents re-runs ran as parallel processes, so their `seconds` are slightly inflated; `react` and
   `tape` `seconds` include oracle computations and are not comparable to `ours_*`.
7. **Smaller test gaps:** A* dominance has a targeted test, but BFS node limits, IDA* deepening on a toy graph, an
   inadmissible-heuristic negative control and the `make_instances` warning have no direct tests.

## 8. Reproducing

```bash
cd tape-graph
pip install -r requirements.txt     # numpy, pytest, ortools
python -m pytest -q                 # 83 tests, about 30 s (first run builds the cube table, about 12 s)
```

The exact commands behind every published table are in the README ("Run" and "How the results were produced"). From the
logged times: the solvers and first-design constrained runs take about 710 s together, the four agents runs 3,684 s if run
one after another (about 2,267 s when run in parallel, as they were; the Boxoban run alone is about 38 minutes), and the
`bind` runs about 9 minutes. The raw CSVs are committed under `docs/data/`.

## 9. Not done / candidates for a "full project"

- Plots (the spec deferred them): success against `T*`, nodes and seconds per solver, constrained comparison.
- Real Boxoban levels (DeepMind's files; a download I would ask about first) and the 3x3 cube.
- More constrained evidence: multi-box Sokoban, a `c_slack` sweep, and a resource model that applications would recognise.
- Real-LLM ReAct and TAPE runs (the original repository has this for Sokoban and ALFWorld; it needs API keys and costs money).
- Packaging and polish: `pyproject.toml`, a console entry point, CI, the remaining test gaps, an agents configuration
  that is fully logged in every CSV.
