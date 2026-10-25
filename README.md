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

This is the nominal loop; the run behind the reported numbers deviated from it for Boxoban and Cube (see below).

## Layout

See `docs/superpowers/specs/2026-10-22-tape-graph-design.md`. The measured tables from the run described below are
in `docs/results.md`.

## How the results were produced

Single machine, sequential runs, seed = CLI default (1). Defaults for everything not listed: budget `B = T* + 2`
(`--slack 2`), `--max_nodes 500000`, ILP `time_limit` 10 s per solve, `--delta 0.16`, `--eta 0.04`, `--N 16`,
`--res_frac 0.9`. Every benchmark used `--n 5` instances per `T*` target (River 6 targets = 30 instances, Sokoban
25, Boxoban 20, Cube 25). Instances are accepted within +-1 of the target and reported under their true `T*`, so
rows in the tables are keyed by actual `T*` and have 1 to 5 instances each.

| benchmark | solvers | agents | constrained |
|---|---|---|---|
| river | `solvers --bench river --n 5` (4 s) | `agents --bench river --n 5 --episodes 100` (238 s) | `constrained --bench river --n 5` (4 s) |
| sokoban | `solvers --bench sokoban --n 5` (12 s) | `agents --bench sokoban --n 5 --episodes 100` (367 s) | `constrained --bench sokoban --n 5` (13 s) |
| boxoban | `solvers --bench boxoban --n 5` (140 s) | `agents --bench boxoban --n 5 --episodes 20`, ILP disabled (2267 s) | `constrained --bench boxoban --n 5` (136 s) |
| cube2 | `solvers --bench cube2 --n 5` (228 s) | `agents --bench cube2 --n 5 --episodes 30`, ILP disabled (812 s) | `constrained --bench cube2 --n 5` (171 s) |

Times are from the run logs. The solvers and constrained runs were done sequentially (about 710 s in total). The
agents runs were **re-run after a seeding fix** (commit b7f6106: before it, every instance in a benchmark received the
same noise draws; now each instance gets its own seed `seed + 7919 * index`, shared by all methods of that instance so
the comparison stays paired). The first agents results were discarded. The four re-runs ran as parallel processes
(longest 2267 s), so their `seconds` columns are slightly inflated by contention. Then `python -m tapegraph.bench
report`.

Deviations from the nominal loop above:

- **Fewer episodes for the two expensive benchmarks.** Boxoban agents used `--episodes 20` and Cube agents
  `--episodes 30` instead of 100. With 20 to 30 episodes a success rate has a standard error of roughly 0.05 to
  0.09 per instance, and the Boxoban and Cube buckets have 1 to 5 instances each.
- **ILP disabled in the Boxoban and Cube agents runs.** Those two runs were started through a small wrapper that set
  `ilp.ORTOOLS_AVAILABLE = False` before calling `bench.main()`. Consequences: (a) there are **no `ours_ilp` rows**
  for Boxoban or Cube; (b) the `tape` rows for Boxoban and Cube used `ilp.graph_path_bfs` (a BFS shortest path on the
  folded graph: same minimum length, but not the ILP), whereas the `tape` rows for River and Sokoban used the real
  CP-SAT ILP. The solvers and constrained runs for all four benchmarks used the ILP normally. Why: the solver runs
  show the ILP does not scale on these two domains (10 s timeouts on 5 of 20 Boxoban instances, all at `T*` >= 16;
  0 of 10 Cube instances solved at `T*` 9 and 11), and `ours_ilp` and `tape` solve an ILP on every re-plan. The
  logs show an ILP-enabled Boxoban agents run (`--episodes 20`) and two ILP-enabled Cube agents runs (`--episodes
  100`, then `--episodes 30`) that were started and abandoned without writing a CSV (the first Cube one ran about
  28 min by log timestamps). The logs do not state the reason for abandoning them; the timeout and size numbers
  above are the likely cause.

## Findings

Everything below is read from `docs/results.md` (a copy of the generated `results/results.md`) unless marked as a
separate check. Numbers are means over the instances in a `T*` bucket; cost means are over solved instances only,
`seconds` includes failed runs. The budget is `T* + 2`, and `cost_ratio = 1.0` means a path of length exactly `T*`.

**1. Which solvers matched `T*`.** BFS, A*, IDA* and the ILP never returned a path longer than `T*` (`cost_ratio` is
exactly 1.0 for every solved instance in all four CSVs). Weighted A* (w = 2) is the only solver that returned longer
paths: mean `cost_ratio` 1.0476 at Boxoban `T*` 7, 1.0286 and 1.0444 at Cube `T*` 7 and 9 (worst single instance 8/7 =
1.143), and exactly 1.0 on River and Sokoban.

- River (30 instances): all five solvers solved all 30. At `T*` = 14: BFS 40 nodes / 0.0004 s, A* 41 / 0.0008 s,
  IDA* 123 / 0.0012 s, weighted A* 27 / 0.0006 s, ILP 45 / 0.0499 s. The state graph is tiny, so the heuristic buys
  nothing: A* expands as many nodes as BFS (41 vs 40 at `T*` 12 and 14).
- Sokoban (25): all five solved all 25. At `T*` = 23: BFS 536 nodes / 0.0022 s, A* 231 / 0.0036 s, IDA* 2467.5 /
  0.0186 s, weighted A* 167 / 0.0028 s, ILP 292 / 0.1521 s. A* uses fewer nodes than BFS but is not faster in
  wall-clock at this size.
- Boxoban (20): BFS, A*, IDA* and weighted A* solved 20/20. At `T*` = 21: BFS 93,674 nodes / 0.864 s, A* 6,418 /
  0.2929 s, IDA* 26,961 / 0.6123 s, weighted A* 1,842 / 0.0786 s (cost_ratio 1.0 there). A* is faster than BFS in
  wall-clock from `T*` 16 up (0.151 vs 0.3127 s at 16, 0.2958 vs 0.9689 s at 19); below that they are close.
- Cube (25): A*, IDA* and weighted A* solved 25/25. At `T*` = 11: A* 87,583 nodes / 4.38 s, IDA* 36,250 / 0.659 s,
  weighted A* 5,614 / 0.2359 s (cost_ratio 1.0 there). IDA* expands fewer nodes than A* at every Cube `T*` from 5
  up (`T*` 9: 2,472 vs 3,570).

**2. Where solvers hit limits** (Failure breakdown tables).

- BFS: `node_limit` on 7 of 25 Cube instances (2 of 5 at `T*` 9, all 5 at `T*` 11, at the 500,001-node cap). No BFS
  failures on River, Sokoban or Boxoban.
- ILP: Boxoban 15/20 ok, 5 `timeout`, all at `T*` >= 16 (2 of 3 at `T*` 16, 1 of 2 at 19, 2 of 3 at 21; 10 to 16 s
  each). Cube 15/25 ok, 5 `timeout` (all 5 instances at `T*` 9, 19.7 s mean) and 5 `too_large` (all 5 at `T*` 11, the
  bounded graph hit the 500,000-node cap). The ILP solved every River and Sokoban instance.
- A*, IDA* and weighted A* had no failures in any benchmark, unconstrained.
- Constrained (below): A* had 1 `node_limit` (Cube `T*` 11); the ILP had 5 `too_large` and 2 `timeout` on the 7 Cube
  instances it was run on, and 0 successes.

**3. Constrained: ILP vs resource-constrained A*.** The resource budget is `floor(0.9 x resource of the unconstrained
optimum)`. That is infeasible for most instances, which are recorded as `solver=skipped` rows (status `infeasible`):
River 6 of 30 (4 of 5 at `T*` 4, 2 of 5 at `T*` 6), **Sokoban 25 of 25, Boxoban 20 of 20**, Cube 18 of 25 (all 15 at
`T*` 3, 5, 7 and 3 of 5 at `T*` 9). So the ILP-vs-A* comparison exists only for River (24 instances) and Cube `T*` 9
and 11 (7 instances), and not at all for Sokoban or Boxoban. The skips are genuine: on a spot check of 8 of these
instances A* and the ILP both report no feasible path at the reduced budget, and the ILP does solve them at the
unreduced resource. (Skipped rows only record A*'s verdict, so the table itself does not show the ILP's.)

- River: both solved 24/24 and agree on cost 24/24 (`agrees_with_astar` 1.0 in every bucket). A* is faster in every
  bucket: 0.0001 to 0.0008 s vs 0.0188 to 0.0828 s for the ILP (roughly 65 to 190 times), with similar node counts
  (A* 10 to 41, ILP 19 to 45).
- Cube: A* solved 6 of 7 (cost 9.0 at `T*` 9 in 0.19 s; 4 of 5 at `T*` 11, cost 11.0, 170,665 nodes, 5.6 s). The ILP
  solved 0 of 7, so agreement is 0.0 there.
- The ILP never beat A* on time or on success in any constrained row.

**4. Success within budget under noise** (`delta` 0.16 planning error, `eta` 0.04 execution noise; episodes: 100 River
and Sokoban, 30 Cube, 20 Boxoban; each instance has its own noise seed, shared by the methods). Smallest and largest
`T*` bucket:

| bench | T* | react | tape | ours_astar | ours_ilp |
|---|---|---|---|---|---|
| river | 4 / 14 | 0.752 / 0.246 | 0.996 / 0.922 | 0.996 / 0.94 | 0.998 / 0.938 |
| sokoban | 5 / 23 | 0.66 / 0.05 | 0.98 / 0.755 | 0.98 / 0.81 | 0.98 / 0.80 |
| boxoban | 7 / 21 | 0.533 / 0.05 | 0.983 / 0.80 | 0.983 / 0.817 | none |
| cube2 | 3 / 11 | 0.84 / 0.32 | 1.0 / 0.947 | 1.0 / 0.94 | none |

Averaged over instances, success is react / tape / ours_astar / ours_ilp: River 0.455 / 0.951 / 0.954 / 0.959,
Sokoban 0.248 / 0.862 / 0.872 / 0.874, Boxoban 0.225 / 0.850 / 0.855 / none, Cube 0.539 / 0.967 / 0.965 / none.

- ReAct-sim falls steadily with `T*` in every benchmark and is far below the others from the first bucket (0.66 to
  0.84 at the smallest `T*`, 0.05 to 0.32 at the largest). `tape`, `ours_astar` and `ours_ilp` are within a few points
  of each other everywhere (largest `tape` vs `ours_astar` gap: 0.055 at Sokoban `T*` 23). Per instance, `tape` has
  higher success than `ours_astar` on 10 of 100 instances, lower on 23, equal on 67, so `ours_astar` >= `tape` on 90
  of 100; the pooled margin is 0.001 to 0.010 per benchmark, which I do not read as a real edge. `tape` runs more
  solves per episode at large `T*` (Sokoban `T*` 23: 5.04 vs 3.24 for `ours_astar`). `ours_ilp` tracks `ours_astar`:
  higher on 14 and lower on 5 of 30 River instances (pooled 0.959 vs 0.954), higher on 3 and lower on 2 of 25 Sokoban
  instances (0.874 vs 0.872), so no meaningful difference, and it takes far longer per episode (River `T*` 14: 0.065
  vs 0.0012 s; Sokoban `T*` 23: 0.2037 vs 0.0068 s).
- Success of the re-planning methods declines with `T*` in all four benchmarks, since a longer path is exposed to
  more noise with the same 2 steps of slack. The decline is mild where moves are reversible and steeper for
  push-based puzzles. River `ours_astar` goes 0.996, 0.988, 0.964, 0.936, 0.90, 0.94 over `T*` 4 to 14 (never below
  0.90). Cube goes 1.0, 0.973, 0.973, 0.94, 0.94 over `T*` 3 to 11 (never below 0.94). Sokoban goes 0.98, 0.99, 0.96,
  0.934, 0.865, 0.843, 0.817, 0.84, 0.753, 0.81 over `T*` 5 to 23. Boxoban goes from 0.983 (`T*` 7) to 0.70 (`T*` 16)
  and 0.80 and 0.817 at `T*` 19 and 21 (3 or fewer instances and 20 episodes per instance there). At `T*` 14 to 15
  River is 0.94 vs Sokoban 0.865 and 0.843; at `T*` 11 to 12 Cube is 0.94 vs Boxoban 0.90 (one instance) and 0.833.
  This is consistent with reversible domains (River, Cube) absorbing errors through slack while Sokoban/Boxoban pushes
  can be irrecoverable, but the tables do not isolate that cause: up to `T*` 9 River, Cube and Sokoban are close
  (River `T*` 8: 0.964; Cube `T*` 9: 0.94; Sokoban `T*` 9: 0.934), the gap only opens from `T*` 12 to 14 up (about 0.07
  to 0.1), and longer paths also mean more noise events.
- Before the seeding fix the Cube row read 1.0 for `tape` and `ours` at every `T*`. That was an artifact of the
  bug: all instances saw the same 30 noise draws, and none of them hurt. With per-instance seeds the Cube numbers
  match a separate 200-episode check made earlier on the old seeding (`ours_astar`, `T*` 5: 0.99, `T*` 7: 0.96, `T*` 9:
  0.92 to 0.94).

**Does the ILP win anywhere?** No. In the unconstrained table it is the slowest of the five solvers in every
`(benchmark, T*)` bucket except Cube `T*` 11 (34 to 136 times slower than A* on River and Sokoban). Its
node count is below BFS in some Sokoban and Boxoban buckets, but ILP "nodes" is the size of the bounded subgraph it
builds. That exception (Cube `T*` 11, ILP 3.3 s vs A* 4.4 s) is a bucket where it
solved 0 of 5 and failed fast with `too_large`. It also never beats A* in the constrained table and solves fewer
instances on Boxoban and Cube. The supplementary constrained runs below say the same.

### Supplementary: constrained at res_frac 0.95

The main constrained table uses `--res_frac 0.9` and leaves Sokoban and Boxoban with no solved instance. Extra runs
for Sokoban and Boxoban (`constrained --bench {sokoban,boxoban} --n 5 --res_frac X --out results_rfNN`, tables in
`docs/results_rf95.md`; same instances as the main run; run concurrently with other jobs, so timings are a little
inflated) show that **it is still almost all infeasible** just below the optimum's resource. The budget is
`floor(X * resource of the length-optimal path)`, and since resource is an integer (1 per step, 3 per push) a
fraction slightly below 1 already removes at least one unit; most likely the length-optimal path is already close to
the cheapest in resource, although I did not verify that beyond A* and the ILP agreeing that those budgets are
infeasible.

| res_frac | sokoban skipped (infeasible) / solved | boxoban skipped / solved | ILP vs A* where solved |
|---|---|---|---|
| 0.95 | 24 / 1 | 20 / 0 | Sokoban `T*` 17: both cost 19, agree; A* 0.0047 s, ILP 0.1458 s |
| 0.97 | 23 / 2 | 20 / 0 | Sokoban `T*` 17 and 21: both agree on cost; A* 0.0064 to 0.0068 s, ILP 0.17 to 0.21 s |
| 1.0 (non-binding by construction) | 0 / 25 | 0 / 20 | Sokoban: both 25/25, agree 25/25; A* 0.0017 s vs ILP 0.1033 s mean. Boxoban: A* 20/20, ILP 14/20 (6 `timeout`, all at `T*` >= 16), all 14 ILP solutions agree with A*; on those 14, A* 0.028 s vs ILP 2.02 s |

So for Boxoban there is no instance at 0.95 or 0.97 where the resource budget binds and is still feasible, and for
Sokoban only 1 and 2 of 25. In those, the ILP agreed with A* and was slower. With a non-binding budget (1.0) the
pattern is the same as in the unconstrained table.

## Caveats

- ReAct and TAPE are simulated with the paper's noise model, not real LLMs.
- Sokoban/Boxoban instances are rejection-sampled from long reverse random walks and reported by their true `T*`.
- TAPE-sim minimises path length in the folded graph, not TAPE's node-score objective.
- The ILP is an edge-flow formulation, not time-expanded.
- Cost means in the tables are over solved instances only.
- Buckets have 1 to 5 instances (and 20 to 100 episodes each), so success-rate differences of a few points are within
  noise.
