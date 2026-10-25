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
| river | `solvers --bench river --n 5` (4 s) | `agents --bench river --n 5 --episodes 100` (231 s) | `constrained --bench river --n 5` (4 s) |
| sokoban | `solvers --bench sokoban --n 5` (12 s) | `agents --bench sokoban --n 5 --episodes 100` (345 s) | `constrained --bench sokoban --n 5` (13 s) |
| boxoban | `solvers --bench boxoban --n 5` (140 s) | `agents --bench boxoban --n 5 --episodes 20`, ILP disabled (2311 s) | `constrained --bench boxoban --n 5` (136 s) |
| cube2 | `solvers --bench cube2 --n 5` (228 s) | `agents --bench cube2 --n 5 --episodes 30`, ILP disabled (721 s) | `constrained --bench cube2 --n 5` (171 s) |

Wall-clock total about 4300 s (72 min); times are from the run logs. Then `python -m tapegraph.bench report`.

Deviations from the nominal loop above:

- **Fewer episodes for the two expensive benchmarks.** Boxoban agents used `--episodes 20` and Cube agents
  `--episodes 30` instead of 100. With 20 to 30 episodes a success rate has a standard error of roughly 0.05 to
  0.09, and all instances in a run share the same noise draws (the episode RNG is seeded from `seed` and the episode
  index only), so instances in a bucket are not independent replicates.
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
and Sokoban, 30 Cube, 20 Boxoban). Smallest and largest `T*` bucket:

| bench | T* | react | tape | ours_astar | ours_ilp |
|---|---|---|---|---|---|
| river | 4 / 14 | 0.798 / 0.24 | 1.0 / 0.93 | 1.0 / 0.94 | 1.0 / 0.90 |
| sokoban | 5 / 23 | 0.67 / 0.055 | 0.97 / 0.775 | 0.97 / 0.825 | 0.97 / 0.83 |
| boxoban | 7 / 21 | 0.433 / 0.033 | 0.95 / 0.683 | 0.95 / 0.70 | none |
| cube2 | 3 / 11 | 0.767 / 0.333 | 1.0 / 1.0 | 1.0 / 1.0 | none |

- ReAct-sim falls steadily with `T*` in every benchmark and is below the others from the first bucket. `tape`,
  `ours_astar` and `ours_ilp` are within a few points of each other everywhere (largest `tape` vs `ours_astar` gap:
  0.05 at Sokoban `T*` 23). `ours_astar` >= `tape` on 98 of the 100 instances (`tape` is higher on 2), but the margins
  are small and noise draws are shared, so I do not read this as a real edge. `tape` runs more solves per episode at
  large `T*` (Sokoban `T*` 23: 4.73 vs 3.23 for `ours_astar`). `ours_ilp` tracks `ours_astar` with no systematic
  difference (River `T*` 14: 0.90 vs 0.94; Sokoban `T*` 23: 0.83 vs 0.825) and takes far longer per episode (River
  `T*` 14: 0.0596 vs 0.0012 s; Sokoban `T*` 23: 0.1962 vs 0.0062 s).
- Reversible vs irreversible: River `ours_astar` stays between 0.918 and 1.0 across `T*` 4 to 14 and is flat from
  `T*` 8 on (0.95, 0.93, 0.918, 0.94). Sokoban falls from 0.97 to 0.79 at `T*` 21 (0.825 at 23) and Boxoban from 0.95
  to 0.70 at `T*` 19 and 21. This is consistent with a River move being undoable inside the 2 steps of slack while a
  Sokoban/Boxoban push can be irrecoverable, but the tables do not isolate that cause: at similar `T*` River and
  Sokoban are close (River `T*` 8 and 10: 0.95, 0.93; Sokoban `T*` 9: 0.91), the drop is larger with more boxes
  (Boxoban `T*` 16 to 21: 0.78 to 0.70; Sokoban `T*` 15 to 23: 0.90 to 0.83), and longer paths are also exposed to
  more noise.
- Cube shows 1.0 for `tape` and `ours` at every `T*`, but this is a small-sample artifact: only 30 episodes, and
  every instance sees the same 30 noise draws. A separate check (not in the tables: `ours_astar`, `--eta 0.04`,
  seed 1, 200 episodes, the same Cube instances for `T*` 3 to 9) gave about 1.00 (`T*` 3), 0.99 (`T*` 5), 0.96 (`T*`
  7) and 0.92 to 0.94 (`T*` 9). So Cube also declines with `T*`, at about the same rate as River and Sokoban; the
  first 30 episodes of that check were all successes, which is what the table contains. It was not run at `T*` 11
  (about 4.6 s per episode with A*).

**Does the ILP win anywhere?** No. In the unconstrained table it is the slowest of the five solvers in every
`(benchmark, T*)` bucket except Cube `T*` 11 (34 to 136 times slower than A* on River and Sokoban). Its
node count is below BFS in some Sokoban and Boxoban buckets, but ILP "nodes" is the size of the bounded subgraph it
builds. That exception (Cube `T*` 11, ILP 3.3 s vs A* 4.4 s) is a bucket where it
solved 0 of 5 and failed fast with `too_large`. It also never beats A* in the constrained table and solves fewer
instances on Boxoban and Cube. Supplementary check, not in the tables: re-running Sokoban constrained with
`--res_frac 1.0` (so the constraint is feasible) had both solve 25/25 and agree 25/25, with A* at 0.0014 s and the
ILP at 0.081 s on average.

## Caveats

- ReAct and TAPE are simulated with the paper's noise model, not real LLMs.
- Sokoban/Boxoban instances are rejection-sampled from long reverse random walks and reported by their true `T*`.
- TAPE-sim minimises path length in the folded graph, not TAPE's node-score objective.
- The ILP is an edge-flow formulation, not time-expanded.
- Cost means in the tables are over solved instances only.
- Instances in a bucket share the same episode noise draws and buckets have 1 to 5 instances, so the success-rate
  tables are not independent samples; differences of a few points are within noise.
