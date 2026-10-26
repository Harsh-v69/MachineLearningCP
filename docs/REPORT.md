# tape-graph: project report

Status at code commit `365263c` (tests: 202
passed and 5 skipped; about 5,900 lines of Python across package, tests and scripts). Every number below is taken from
`docs/paper.md` (generated from the CSVs under `docs/data/`), the generated tables `docs/results*.md` or the raw CSVs;
the README holds the same results with more per-bucket detail and the reproduction commands. Two time-ratio statistics appear: the paper headlines the **median of per-row ILP/A*
seconds ratios** and lists the **ratio of mean seconds** (mean ILP seconds over mean A* seconds on the same rows, pulled toward
the slowest rows) beside it; this report gives both where they fit and labels each figure as "median" or "ratio of mean seconds". Example: cube2 at `c_slack` 4 is 228x as a ratio of means and 431x as a
median per-row ratio.

## 1. Summary

`tape-graph` takes TAPE (Jeong, Kim, Lee 2026: an LLM proposes plans, the plans are folded into a graph, an ILP picks a
path, execution is constrained and re-planned on deviation) and removes the LLM. What is left is a planning algorithm
over a state graph:

> Given an implicit state graph G, a random start s0 and a goal set, find a minimum-cost feasible path under budget B.
> Fold candidate paths into a graph, solve for the best constrained path, execute one step, and re-solve from the state
> the world actually returned.

Headline results, on seven generated benchmarks (River Crossing; Sokoban with 1, 2 and 3 boxes; a Boxoban-style 4-box
imitation; Rubik's 2x2x2 and 3x3x3, half-turn metric):

1. **The graph solvers are exact where they finish, and A* finished on all 170 unconstrained instances.** BFS, A*, IDA* and the ILP never returned a
   path longer than the optimum `T*` on any instance they solved (635 solved rows). A* solved all 170 unconstrained
   instances (it hit its node limit once in the frac cube2 run and once in the cube3 bind bisection). By median seconds per instance, weighted A* (w = 2) is the fastest solver on river, sokoban, sokoban2, sokoban3 and
   boxoban, and IDA* is the fastest on cube2 and cube3; weighted A* returned a longer path on 6 of its 169 solved rows (worst 1.1429 = 8/7).
2. **The ILP did not beat A* in any measured regime.** Unconstrained it solved 142 of 170 instances (A* 170 of 170; A* by construction: instances and budgets are derived with A*) and was
   faster than A* on 0 of the 142 where both solved (median 29x to 224x slower per benchmark; ratio of mean seconds 52x to
   366x). With a resource budget that always binds (the `bind` design; `c_slack` 2, 4 and 8, not every value on every
   benchmark) it solved 362 of 453 (instance, level, `c_slack`) rows (A* 453 of 453; A* by construction: instances and budgets are derived with A*); on the 362 rows where both solved (77
   distinct instances) the cost was equal and the ILP was faster on 0 (median 28x to 2236x slower per benchmark and
   `c_slack`; ratio of mean seconds 25x to 2231x). On 27 rows it returned sooner than A*, but with a failure status; a
   fast failure is not a win. This is scoped to the edge-flow formulation, the 10 s ILP limit, the node caps (500,000 by
   default, 100,000 for cube3) and these resources.
3. **Re-planning on the true graph beats the simulated ReAct by 0.43 to 0.69** in mean per-instance success, and differs
   from the simulated TAPE by -0.001 to +0.031. The bootstrap interval of that last difference excludes 0, with the
   LLM-free loop higher, on river (300 episodes), sokoban (300), sokoban2 and sokoban3, and contains 0 on boxoban and cube2
   (20 and 30 episodes, ILP-disabled tape). The difference is small, not zero (an earlier version of this report called it
   close by construction and not shown to matter; with 300 episodes and more benchmarks that wording was too strong).
4. **Everything that is simulated is labelled as such.** ReAct and TAPE are models of LLM behaviour using the paper's
   noise model (planning error `delta` = 0.16, execution noise `eta` = 0.04), not LLM runs. No language model was run.

<!-- CUBE3-AGENTS -->cube3 agents: PENDING (see docs/paper.md section 7.4); this sentence is replaced when the run finishes or is abandoned.<!-- CUBE3-AGENTS -->

## 2. How the project maps to the original goals

| Your goal | Where it landed |
|---|---|
| 1. Showcase TAPE as an algorithm: best path to a goal from a random start | The algorithm statement above and `README.md`; implemented as `Replan` (`tapegraph/baselines/replan.py`) over any `Problem` |
| 2. LLM + algorithm gives long-horizon planning (not our scope) | Out of scope, as agreed (real-LLM runs were not done, by the user's choice). The loop's planner is an interface (`solver(problem, start, budget=...)`), so an LLM proposer could replace the oracle later |
| 3a. No LLM; benchmarks with a set goal and random start (Sokoban, Boxoban, Rubik's, River Crossing) | Seven generated benchmarks (River; Sokoban with 1, 2, 3 boxes; Boxoban-style; Rubik's 2x2x2 and 3x3x3), each with a random-start generator and a true `T*` for every instance (sections 3.3 and 4.1); plus a strict loader for real Boxoban files (no results on real levels) |
| 3b. Replace the single ILP with graph solvers (A* etc.) and adjust graph constraints per algorithm | BFS, A*, weighted A*, IDA* and the CP-SAT ILP behind one signature, each with its own constraints (section 3.2) |
| 4. Compare with ReAct and TAPE | Simulated ReAct and TAPE with the paper's noise model, same instances, paired noise, Wilson intervals and a paired bootstrap (sections 3.4 and 5.4) |
| Later additions | Packaging (`pip install -e`, `tapegraph` console script, `tapegraph all --profile smoke` or `full`), dependency-free SVG figures, a generated paper (`docs/paper.md`) |

## 3. Architecture

```
tapegraph/
  problem.py        Problem interface, Result dataclass, res_bind (resource for the binding experiment)
  oracle.py         exact distance-to-goal for the simulated baselines (cached A*, or an exact table)
  execute.py        episode loop with execution noise; evaluate() with per-episode seeds
  benchmarks.py     registry of the benchmarks, T*-bucketed instance generation, boxoban_file registration
  bench.py          CLI: solvers | agents | constrained | report | all
  stats.py          Wilson interval and percentile bootstrap (numpy only)
  plots.py          dependency-free deterministic SVG line/bar/scatter charts
  problems/         river.py  sokoban.py (1 to 3 boxes)  boxoban.py (generator + strict file loader)  cube2.py  cube3.py
  solvers/          bfs.py  astar.py  idastar.py  ilp.py
  baselines/        react_sim.py  tape_sim.py  replan.py
scripts/            make_figures.py  make_paper.py  probe_resources.py (which resources trade off against length)
docs/               paper.md (generated), results*.md (generated), data/ (CSVs), figures/ (49 SVGs), this report, spec, plans
tests/              202 passed + 5 skipped
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

Optional: `exact_dist(s)` (River and Cube2 have exact tables), `res(s, a, s2)` (a side resource) and `res_bind` (the
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
objectives, which this project does not use. The ILP's result counts as `ok` only when CP-SAT proves optimality; any other
non-infeasible outcome is `timeout`.

### 3.3 Benchmarks

| Benchmark | State | Heuristic | Dead-end prune | Random start |
|---|---|---|---|---|
| Sokoban (7x9, 1 box) | player + sorted boxes | sum over boxes of Manhattan distance to the nearest goal | static dead cells (cells from which no goal is reachable by pushes, ignoring other boxes) | reverse play from a solved layout |
| sokoban2 (7x9, 2 boxes), sokoban3 (8x10, 3 boxes) | same | same | same | same (`T*` targets 6 to 22 and 10 to 26) |
| Boxoban-style (10x10, 4 boxes) | same | same | same | same, generated locally (no download) |
| River Crossing (8 missionaries/cannibals, boat 4) | (missionaries left, cannibals left, boat) | trip-count lower bound | none | a state with exact distance `T*` from an exact table |
| Rubik's 2x2x2 (half-turn metric, 9 moves) | (corner permutation, corner twist) | max of two pattern databases (5,040 and 729 entries) | none | a uniformly random state at exact depth `T*` |
| Rubik's 3x3x3 (half-turn metric, 18 moves) | corner coordinate + three edge-quad coordinates | corner pattern database, 88,179,840 int8 entries (chunked vectorised build, cached under `.cache/`) | none | random walk without same-axis repeats; `T*` from A* with the database as oracle (targets 3, 5, 7, 9) |

The 2x2x2's two coordinates evolve independently under every move, so the full 3,674,160-state distance table is one
vectorised BFS (about 12 s once, then cached), and the depth counts reproduce the published 2x2x2 distribution exactly
(1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644; God's number 11). The cube3 target `T* = 10` was dropped because weighted A* hit the 500,000-node cap on 1 of 2 instances there (comment in `benchmarks.py`). The 3x3x3 move tables reproduce the
known half-turn-metric counts 1, 18, 243, 3240, 43239 by full-state BFS, and a slow test (`--runslow`) checks the pattern database against
the depth-5 count 574,908.

`load_boxoban_file` (`--bench boxoban_file --boxoban_file PATH`) reads a user-supplied file in DeepMind's format and is strict
about malformed levels; levels the oracle cannot solve or that are already solved become `skipped` rows. Nothing is
downloaded and **no results on real Boxoban levels exist** in this repository.

### 3.4 Agents (all on the same instances, paired noise)

- **ReAct-sim:** the oracle's next action; with probability `delta` a planning error (an action that breaks the budget if
  one exists); with probability `eta` a different action than intended is executed. No recovery.
- **TAPE-sim:** 16 rollouts with the same planning error are folded into a graph; a shortest path in the folded graph
  (the real ILP, or BFS on the folded graph when the ILP is disabled with `--no_ilp`) is followed; it re-plans on deviation.
- **Replan (this project, "ours"):** one step of a chosen solver on the true graph, execute, re-solve from the observed
  state on deviation. Variants `ours_astar` and `ours_ilp`. Execution noise `eta` applies to all methods in the loop.

## 4. Method

### 4.1 Instances and budgets

Instances are generated per target `T*` (accepted within +-1, reported under their true `T*`; the true `T*` is verified
against the oracle or an exact table). The budget is `B = T* + 2` unless stated. Seed 1, `--max_nodes 500000` (100,000 for
cube3, because of RAM), `--n 5` instances per target for solvers, agents and the first constrained design. Because the Sokoban
family and Boxoban instances are rejection-sampled from long reverse random walks, buckets are keyed by the actual `T*` and contain 1 to 5 instances.

### 4.2 Metrics

Per benchmark, `T*` bucket and method: success within budget under noise, path length over `T*` (`cost_ratio`), nodes
expanded, wall-clock seconds, and for the constrained experiments agreement with A*, status counts and a failure
breakdown. Failures (`node_limit`, `too_large`, `timeout`, `no_path`, `no_tradeoff`) are recorded as rows, and cost means
are over solved instances only (every table says so). One qualification of "never dropped": the `bind` figures ignore rows where A*
itself was skipped for `node_limit` (cube3 at `c_slack` 4 has one such instance); the tables count it. Agent success has 95%
Wilson intervals (pooled over instances, which assumes independent episodes) and methods are compared with a paired 95%
percentile bootstrap over instances (B = 2000, seed 0).

## 5. Results

### 5.1 Unconstrained solvers (`docs/results.md`, `docs/results_new_solvers.md`; paper 7.1)

- **Exactness.** `cost_ratio` is exactly 1.0 for every solved row of BFS, A*, IDA* and the ILP (635 rows). Weighted A* is the
  only solver that returned longer paths (6 of 169 solved rows; mean 1.0476 at Boxoban `T*` 7; worst single instance 8/7 = 1.143).
- **River (30 instances).** The graph is tiny, so the heuristic buys nothing: A* expands 41 nodes against BFS's 40 at
  `T*` 14.
- **Sokoban (25).** At `T*` 23: BFS 536 nodes, A* 231, IDA* 2,467.5, weighted A* 167, ILP 292. A* uses fewer nodes but is not
  faster in wall-clock at this size.
- **sokoban2 (25) and sokoban3 (25).** BFS, A*, weighted A* and IDA* solved all 50; the ILP solved 25 of 25 on sokoban2
  and 16 of 25 on sokoban3 (9 `timeout`). IDA* is slower than A* in median per-instance seconds (1.63x and 1.82x).
- **Boxoban (20).** At `T*` 21: BFS 93,674 nodes / 0.864 s, A* 6,418 / 0.293 s, weighted A* 1,842 / 0.079 s. A* is faster
  than BFS from `T*` 16 up.
- **Cube2 (25).** At `T*` 11: A* 87,583 nodes / 4.38 s, IDA* 36,250 / 0.659 s, weighted A* 5,614 / 0.236 s. IDA* expands
  fewer nodes than A* at every `T*` from 5 up. BFS hit its 500,000-node cap on 7 of 25 instances.
- **cube3 (20, cap 100,000).** A* and IDA* solved 20 of 20, weighted A* 19 of 20, BFS 10 of 20 (10 `node_limit`), the ILP 16 of
  20 (4 `too_large`). IDA* is faster than A* in median per-instance seconds on both cubes (0.32x on cube3, 0.38x on cube2).
- **Where the ILP fails.** Boxoban: 5 of 20 `timeout` (all at `T*` >= 16). Cube2: 5 `timeout` (all at `T*` 9) and 5
  `too_large` (all at `T*` 11), 15 of 25 solved. sokoban3: 9 `timeout`. cube3: 4 `too_large`. It solved every River, Sokoban
  and sokoban2 instance but was slower than A* on all of them (bucket-level 34x to 136x on River and Sokoban).
- **How much slower.** Median per-instance ILP/A* seconds by benchmark: river 82x, sokoban 54x, sokoban2 47x, sokoban3 50x,
  boxoban 29x, cube2 224x, cube3 174x; the same as a ratio of mean seconds: 81x, 52x, 61x, 72x, 55x, 311x, 366x. The ILP was
  faster than A* on 0 of the 142 instances where both solved.

### 5.2 Constrained, first design (`frac`; `docs/results.md`, `docs/results_rf95.md`; paper 7.2)

The resource budget was a fraction of the unconstrained optimum's resource (`res_frac` 0.9, plus supplementary 0.95, 0.97
and a non-binding 1.0). It almost never made the budget bind: **all 30 solved main-table instances have `cost == T*`**,
and Sokoban (25 of 25) and Boxoban (20 of 20) were infeasible at the budget. Over the runs with `res_frac` below 1 (190
instance-runs), 156 were infeasible and 3 of the 33 solved A* rows had cost above `T*` (2 distinct instances, all Sokoban). So
this design does not test the case a resource-constrained ILP is meant for. For Sokoban and Boxoban that is structural: the
resource is steps plus 2 per push, so any budget below the optimum's resource needs fewer pushes, which almost never exists.
(This is reasoning plus A*/ILP agreement on 8 spot-checked instances, not an enumeration.) "The constrained regime was barely
exercised" is a statement about this design only.

### 5.3 Constrained, redesigned (`bind`; `docs/results_bind*.md`; paper 7.3)

A probe (`scripts/probe_resources.py`) found that the original resources are almost never in tension with length: a
cheaper longer path existed on 0 of 30 River, 0 of 8 Cube2, 2 of 25 Sokoban and 0 of 3 Boxoban instances. The redesign
therefore (a) uses resources that do trade off and (b) picks the budget so it always binds and always stays feasible:

- `r_opt` = least resource among paths of length <= `T*`; `r_min` = least resource among paths of length <= `T* + c_slack`.
  Skip as `no_tradeoff` if `r_min >= r_opt`. Otherwise two levels: `bind` (R = `r_opt - 1`, so every length-optimal path
  is infeasible) and `tight` (R = `r_min`). A* and the ILP both run at `(T* + c_slack, R)`.
- `res_bind` resources: pushes only (Sokoban family, Boxoban), passengers squared (River), half-turns only (cubes). They were
  chosen because they create trade-offs, so the experiment tests solver behaviour under a binding budget and says
  nothing about which resource a real application would care about.

First run (`c_slack` 4, four benchmarks; ratio of mean seconds where both solved):

| Benchmark | Instances | With a trade-off | A* rows ok | ILP rows ok | ILP failures | ILP/A* time (both ok) |
|---|---|---|---|---|---|---|
| River | 120 | 43 | 86 / 86 | 86 / 86 | none | 66x slower |
| Sokoban | 90 | 7 | 14 / 14 | 14 / 14 | none | 49x slower |
| Boxoban | 40 | 1 | 2 / 2 | 2 / 2 | none | 100x slower |
| Cube2 | 20 | 18 | 29 / 29 | 8 / 29 | 15 `too_large`, 6 `timeout` | 228x slower (431x as a median per-row ratio) |

The ILP matched A*'s cost on all 110 pairs where both solved. The optimum was longer than `T*` by +2 on every River and
Sokoban row, +1 on both Boxoban rows, and +1 to +4 on Cube2. (That the optimum is longer at all is a sanity check of the
construction, not a finding; the size of the increase is the content.) The only rows where the ILP was faster are 8 Cube2
`T*` 11 rows where it returned `too_large` in about 3 s and A* solved them in about 8 s. On Cube2 the ILP solved 6 of
the 18 trade-off instances, all at `T*` <= 5.

**The `c_slack` sweep and the new benchmarks** (ILP ok / rows; trade-off instances; median ILP/A* time ratio where both solved):

| bench | `c_slack` 2 | `c_slack` 4 | `c_slack` 8 |
|---|---|---|---|
| river | 86/86, 43 inst., 58x | 86/86, 43 inst., 63x | 86/86, 43 inst., 66x |
| sokoban | 14/14, 7 inst., 28x | 14/14, 7 inst., 44x | 14/14, 7 inst., 79x |
| sokoban2 | 6/6, 3 inst., 31x | 8/8, 4 inst., 58x | 8/12, 6 inst., 153x |
| cube2 | 14/29, 18 inst., 75x | 8/29, 18 inst., 431x | 0/29, 18 inst., n/a |
| sokoban3 | not run | 4/8, 4 inst., 31x | not run |
| boxoban | not run | 2/2, 1 inst., 107x | not run |
| cube3 | not run | 12/30, 17 inst., 2236x | not run |

A* solved all rows (453 of 453; A* by construction: instances and budgets are derived with A*). On cube2 the ILP solved 14/29, 8/29 and 0/29 rows at `c_slack` 2, 4, 8, but the sweep mostly
measures the ILP's subgraph growth: at the `bind` level `R = r_opt - 1` and the constrained optimum do not depend on `c_slack`, so A* expands
identical nodes in every run (mean nodes over the `bind`-level rows: cube2 41,166.6 at `c_slack` 2, 4 and 8; river 42.5; sokoban 276.1) while the ILP's
explicit subgraph (the `g + h <= T* + c_slack` ball, built without resource pruning) grows (cube2 131,418.2, 243,148.5, 433,078.5; river 30.3, 32.0, 37.4; sokoban
268.0, 397.1, 496.7). The sweep therefore shows the edge-flow ILP's sensitivity to a slack length budget, not a harder trade-off; it ran at the same `--n`
as the `c_slack` 4 runs on purpose, so the instances pair across runs (a larger `--n` was not run). The same cells as a ratio of mean seconds: river 70x, 66x, 72x;
sokoban 29x, 49x, 73x; sokoban2 33x, 60x, 122x; cube2 38x, 228x, n/a; sokoban3 25x; boxoban 100x; cube3 2231x. Distinct trade-off instances
(an instance counted once across `c_slack` runs; recomputed from the CSVs): river 43, sokoban 7, sokoban2 6, sokoban3 4, boxoban 1,
cube2 18, cube3 17, so the multi-box and Boxoban evidence is thin. The cube3 run has one A* `node_limit` skip (in the tables, not in
the figures) and ILP failures of 2 `timeout` and 16 `too_large` on 30 rows. Totals: ILP failures 26 `timeout` and 65 `too_large`; the
ILP was faster than A* on 27 rows, all failures, and on no row where both solved.

### 5.4 Agents under noise (`docs/results.md`, `docs/results_new_agents.md`, `docs/results_agents_ep300.md`; paper 7.4)

Success within budget (`delta` 0.16, `eta` 0.04). One agents dataset per benchmark is used, the one with the most episodes; the
100-episode `main` runs on river and sokoban are superseded by `agents_ep300` (same instances and noise seeds, so counting both
would count episodes twice). Pooled success, and the paired difference of mean per-instance success with a 95% bootstrap CI:

| Benchmark (episodes) | react (sim.) | tape (sim.) | ours_astar | ours_ilp | ours_astar - tape [CI] | ours_astar - react [CI] |
|---|---|---|---|---|---|---|
| River (300) | 0.461 | 0.952 | 0.955 | 0.960 | +0.0026 [+0.0009, +0.0044] | +0.4934 [+0.4329, +0.5493] |
| Sokoban (300) | 0.246 | 0.858 | 0.868 | 0.868 | +0.0103 [+0.0032, +0.0181] | +0.6219 [+0.5749, +0.6647] |
| sokoban2 (100) | 0.214 | 0.842 | 0.850 | 0.852 | +0.0088 [+0.0028, +0.0156] | +0.6364 [+0.5880, +0.6784] |
| sokoban3 (30, no ILP) | 0.133 | 0.796 | 0.827 | not run | +0.0307 [+0.0147, +0.0493] | +0.6933 [+0.6547, +0.7307] |
| Boxoban (20, no ILP) | 0.225 | 0.850 | 0.855 | not run | +0.0050 [-0.0050, +0.0150] | +0.6300 [+0.5625, +0.6975] |
| Cube2 (30, no ILP) | 0.539 | 0.967 | 0.965 | not run | -0.0013 [-0.0067, +0.0027] | +0.4267 [+0.3587, +0.4893] |

Where tape differs from ours_astar per instance it is lower more often than higher on river (14 vs 4), sokoban (11 vs 5), sokoban2
(11 vs 3), sokoban3 (12 vs 1) and boxoban (3 vs 1), and higher on cube2 (2 vs 1). On sokoban the per-bucket gap is largest at the longest bucket
(`T*` 23: tape 0.732, ours_astar 0.782); on sokoban2 and sokoban3 the largest bucket gaps sit at `T*` 21 and `T*` 25, near but not at the longest bucket,
and buckets there hold one to three instances, so the trend with `T*` is suggestive, not established. A plausible mechanism, which was **not tested**, is that 16 noisy rollouts are less likely to contain an
optimal path as `T*` grows. `ours_ilp` is within 0.006 of `ours_astar` in pooled success on the three benchmarks where both ran (unsurprising: both plan
optimally on the true graph), but the per-instance split on river (19 higher, 6 lower) is unexplained (tie-breaking among optimal paths is plausible, untested); it costs far more time per episode. Success of the re-planning methods declines with `T*` in every
benchmark, mildly on the reversible domains (river 0.946 at `T*` 14, cube2 0.940 at `T*` 11) and more on push-based puzzles
(sokoban 0.782 at `T*` 23, sokoban2 0.820 at 23, sokoban3 0.733 at 27); that is consistent with errors being recoverable in
reversible domains and irrecoverable on pushes, but the buckets differ in `T*`, instance counts and episodes, so the cause is not isolated.
In the earlier 100-episode `main` run, tape had higher success than ours_astar on 10 of 100 instances, lower on 23 and equal on 67 (river,
sokoban, boxoban, cube2).

<!-- CUBE3-AGENTS -->cube3 agents: PENDING (see docs/paper.md section 7.4); this sentence is replaced when the run finishes or is abandoned.<!-- CUBE3-AGENTS -->

### 5.5 Figures, paper and reproduction tooling

`python scripts/make_figures.py` draws 49 dependency-free SVG figures from the CSVs (agents success with Wilson bands, solver
nodes and seconds vs `T*`, ILP solve rate, ILP-vs-A* scatter per `c_slack`, solve rate by `c_slack`). `python scripts/make_paper.py`
builds `docs/paper.md` from the same CSVs; its tables and generated sentences are recomputed, and a test asserts that the
committed paper equals a fresh build. Both generators are deterministic. Figures for river and sokoban built from the superseded
100-episode `main` data are still generated; the paper uses the 300-episode ones.

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
| A README caveat said the agents CSV had no solver-failure count, contradicting the new `solver_fail` column | Caveat rewritten; `solver_fail` documented and shown in the agents report table |
| A loaded Boxoban level that is already solved (oracle `T*` = 0) crashed `solvers` with `ZeroDivisionError` | Such levels become `skipped` rows with status `already_solved` in all four commands; test added |
| `report` raised `KeyError` on old agents CSVs without an `episodes` column for benchmarks outside the original four | Those rows are excluded from the CI sections with a printed note; duplicate rows are detected |
| The generated paper's abstract and conclusion hid ILP failure denominators (A* 453 of 453 bind rows against the ILP's 362 of 453; unconstrained 170 of 170 against 142 of 170) | Denominators stated next to every ILP-vs-A* claim |
| The generated paper double counted instances: the `c_slack` runs of a benchmark re-use the same instances (860 `no_tradeoff` instance-runs vs 346 distinct instances), and `agents_ep300` re-uses `main`'s instances and noise seeds, so river and sokoban were counted twice | Counts are over distinct instances (identified by generation order, accepted only if `T*` and `r_opt` agree across runs) and one agents dataset per benchmark (`agents_ep300` supersedes `main`) |
| Smaller issues in the paper generator: the A* reference title was wrong, the ILP ball was described as `T* + slack` for the `bind` runs (it is `T* + c_slack`), "timeout" was described too narrowly (any non-optimal CP-SAT outcome), the median and the ratio of means were not both shown, the hand-written interpretation block could be lost silently | All corrected; a `ratio of mean seconds` column was added; a missing marker fails loudly; a test compares the committed paper with a fresh build |
| The figure review found that the `bind` figures ignore skipped A* `node_limit` rows (so "never dropped" was too strong) | README and section 4.2 wording qualified |
| After the `c_slack` sweep was run, README/REPORT prose still said a tighter `c_slack` had not been tried and that the constrained regime was barely exercised | Found while preparing this refresh; the prose was rewritten (section 5.3) |
| The first README/REPORT said `tape` and `ours_astar` were "close by construction, not by coincidence" and that the difference was "not shown to matter" | With 300 episodes and more benchmarks the paired difference is small but excludes 0 on four of six benchmarks; wording replaced (section 5.4) |
| cube3 A* uses roughly 7 KB per expansion (a 500,000-node cap peaked at about 3.5 GB on the development machine) | All cube3 runs use `--max_nodes 100000`; the solver and `bind` runs ran one at a time (the cube3 agents run ran in parallel with other jobs); the oracle's fixed 300,000 cap, which ignores `--max_nodes`, was noted and not changed |

## 7. Limitations and threats to validity

1. **The baselines are simulated.** ReAct-sim and TAPE-sim use the paper's noise model; they say nothing about how a real
   LLM behaves. The 0.43 to 0.69 gap to ReAct-sim is by construction of the simulator (planning errors are injected
   unfiltered and never corrected); no ablation was run.
2. **TAPE-sim and `ours` are close in success, but not identical.** Why they are close is a hypothesis that was not tested
   here: TAPE-sim's rollouts come from an exact oracle with 16% errors, so a shortest path in the folded graph may be (close to)
   an optimal path of the true graph, which is what `ours` follows. They have identical success on 82 of 150 instances (6
   benchmarks); the difference is small (at most 0.031) but its interval excludes 0 on river, sokoban, sokoban2 and sokoban3 and
   contains 0 on boxoban and cube2 (section 5.4). The difference that does not depend on the noise model is cost: `ours` needs no
   oracle, no rollouts and no ILP.
3. **Constrained evidence is thin on some benchmarks.** Distinct trade-off instances: sokoban 7, sokoban2 6, sokoban3 4, boxoban
   1; the `bind` resources are unusual by design; A* `ok` at the `tight` level partly repeats the bisection's last probe, so the
   informative number is the ILP's behaviour, not A*'s solve rate; instances where A* fails during the bisection are skipped,
   which biases the sample toward instances A* handles. The `c_slack` sweep (2, 4, 8) mostly measures the growth of the
   ILP's explicit subgraph: at the `bind` level `R` and the optimum do not depend on `c_slack`, and A* expands identical nodes in every run (section 5.3).
4. **Fairness is approximate.** The ILP's subgraph is the `{g + h <= T* + slack}` ball (`T* + c_slack` in the `bind` runs; larger
   than A*'s region, built without resource pruning), its graph build counts toward its time, it runs 8 workers against
   single-threaded A*, and it has a 10 s limit A* lacks. ILP failure rates depend on that limit and on the node caps.
5. **Reduced runs.** Agents episodes: river 300, sokoban 300, sokoban2 100, sokoban3 30, Boxoban 20, Cube2 30. ILP disabled
   (no `ours_ilp` rows; `tape` used BFS on the folded graph) on Boxoban, Cube2, sokoban3 and cube3. Buckets hold 1 to 5
   instances, so success differences of a few points are within noise at the bucket level. Pooled Wilson intervals assume
   independent episodes; the paired bootstrap over instances is the honest comparison.
6. **Timing columns.** The solver and constrained runs (original and new, including the `c_slack` sweep) ran one at a time and
   uncontended. The agents runs (original and new) ran as parallel processes and, for the newer ones, alongside development
   work, so every agents `seconds` column is contended; `react` and `tape` `seconds` also include oracle computations and are
   not comparable to `ours_*`.
7. **Node caps.** The cube3 runs use `--max_nodes 100000` because of RAM. The oracle that fixes `T*` and drives the simulated
   baselines has its own 300,000-node cap that `--max_nodes` does not change, so instances it cannot solve are never generated, and
   solver failures at a cap are failures of that configuration, not proofs of infeasibility.
8. **No real data.** The Boxoban loader is tested on a 3-level fixture only; no real Boxoban level and no real LLM was run.
9. **Test gaps of the first version are closed.** BFS node limits, IDA* deepening on a toy graph, an inadmissible-heuristic
   negative control and the `make_instances` warning now have direct tests in `tests/test_polish.py`. What the tests do not
   model, such as timing, remains a risk.

## 8. Reproducing

```bash
cd tape-graph
pip install -e ".[test]"            # numpy, ortools, pytest; installs the `tapegraph` console script
python -m pytest -q                 # 202 passed, 5 skipped (--runslow adds the cube3 corner-PDB cold build)
tapegraph all --profile smoke --out smoke_out    # about 20 s
tapegraph all --profile full  --out full_out     # the original four-benchmark published commands, sequentially (hours)
python scripts/make_figures.py                   # docs/figures from docs/data
python scripts/make_paper.py                     # docs/paper.md from docs/data
```

`all --profile full` covers the original four benchmarks; the commands for the newer benchmarks, the `c_slack` sweep and the
300-episode runs, and the map from `docs/data/<dataset>/` to the commands and tables, are in the README ("Run", "Exact
commands behind the published tables"). From the logged times: the original solvers and first-design constrained runs take about
710 s together, the four original agents runs 3,684 s if run one after another (about 2,267 s when run in parallel, as they were;
the Boxoban run alone is about 38 minutes), and the first `bind` runs about 9 minutes. The raw CSVs are committed under `docs/data/`.

## 9. Not done / candidates for later

Done since the first version of this report: plots (49 SVG figures), the generated paper, packaging and CI, the 3x3 cube, multi-box
Sokoban, the `c_slack` sweep, the strict Boxoban file loader, confidence intervals and the closed test gaps.

Still not done:

- **Real-LLM ReAct and TAPE runs.** Out of scope, by the user's choice (the original repository has this for Sokoban and ALFWorld; it
  needs API keys and costs money).
- **Real Boxoban results.** The loader exists, but no real level file was downloaded or run; this needs a file supplied by the user.
- **More constrained evidence on multi-box puzzles.** Only 4 to 6 trade-off instances on sokoban2 and sokoban3, 1 on Boxoban; and a
  resource model that applications would recognise.
- **cube3 agents.** <!-- CUBE3-AGENTS -->cube3 agents: PENDING (see docs/paper.md section 7.4); this sentence is replaced when the run finishes or is abandoned.<!-- CUBE3-AGENTS -->
- **Untested mechanism** for the small `ours_astar` over `tape` margin (section 5.4). (The `c_slack` effect on the ILP's subgraph is separated from the budget effect by the `bind`-level rows, section 5.3: A* nodes are constant across `c_slack`, ILP nodes grow.)
- An oracle cap that follows `--max_nodes` (it is fixed at 300,000), and a smaller-memory A* for cube3.
