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

Status of the resource-constrained comparison (ILP vs A*): the original `frac` design (budget = a fraction of the
optimum's resource) almost never made the budget bind. A redesigned `bind` design, with resources chosen so that a
trade-off exists, does exercise it on River and Cube (thinly on Sokoban and Boxoban). In both, the ILP matched A*
wherever both solved and was never faster except on rows where it failed. See "Constrained experiment, redesigned so
the budget binds" below.

## Run

```bash
pip install -e ".[test]"      # Python 3.12; installs the `tapegraph` package and console script (numpy, ortools, pytest)
python -m pytest -q
tapegraph all --profile smoke --out smoke_out   # ~20 s: tiny pass over River and Cube2 (solvers, agents, constrained bind, report)
tapegraph all --profile full  --out full_out    # the single-command reproduction of every number in the main tables (hours)
tapegraph all --profile full  --out full_out --dry_run   # print the commands and the manifest skeleton, run nothing
```

`python -m tapegraph <cmd> ...` is the same CLI as `tapegraph <cmd> ...` and as `python -m tapegraph.bench <cmd> ...`
(`pip install -r requirements.txt` still works for running from a checkout). `all --profile full` runs the commands of
the table below sequentially (seed 1, one process at a time so the `seconds` columns are not contended), each kind of run
in its own subdirectory of `--out` (`solvers/`, `agents/`, `constrained_frac/`, `constrained_bind/`), each followed by a
`report` into that subdirectory, and writes `run_manifest.json` (every command with its parsed parameters, wall-clock
seconds per step, git commit, python/numpy/ortools versions; rewritten after each step). The supplementary
`res_frac` 0.95/0.97/1.0 runs and the resource probe table (`scripts/probe_resources.py`) are not part of `all`. Every `solvers` and `constrained` CSV row carries the run
parameters (`seed`, `max_nodes`, `n`, `time_limit`, plus `slack` for `solvers` and `frac`, `res_frac` for `frac`, `c_slack`
for `bind`), as `agents` rows already did; `agents` rows also carry `solver_fail` (mean per episode of solves with a
non-ok status, including a legitimate `no_path`; the agent then falls back to its first legal action).

Exact commands behind the published tables (seed = CLI default 1; `B` is `river`, `sokoban`, `boxoban`, `cube2`):

| step | command |
|---|---|
| solvers, all four | `python -m tapegraph.bench solvers --bench B --n 5` |
| agents, river and sokoban | `python -m tapegraph.bench agents --bench B --n 5 --episodes 100` |
| agents, boxoban | `python -m tapegraph.bench agents --bench boxoban --n 5 --episodes 20 --no_ilp` |
| agents, cube2 | `python -m tapegraph.bench agents --bench cube2 --n 5 --episodes 30 --no_ilp` |
| constrained, `frac` design, all four | `python -m tapegraph.bench constrained --design frac --bench B --n 5` |
| supplementary constrained (`frac`) | `python -m tapegraph.bench constrained --design frac --bench {sokoban,boxoban} --n 5 --res_frac {0.95,0.97,1.0} --out results_rf{95,97,100}` |
| constrained, `bind` design | `python -m tapegraph.bench constrained --design bind --c_slack 4 --out results_bind --bench river --n 20`, and the same with `sokoban --n 20`, `boxoban --n 10`, `cube2 --n 4` (run one at a time) |
| tables | `python -m tapegraph.bench report` (and `report --out results_rfNN`, `report --out results_bind`) |

Both constrained designs write `constrained_<bench>.csv`, so they must use different `--out` directories (the bind
runs went to `results_bind/`, git-ignored; its copies are in `docs/`). `--design` now **defaults to `bind`**: the
`frac` commands above need the explicit `--design frac` to reproduce the published `frac` tables (they were produced
before the flag existed, when `frac` was the only behaviour).

These now reproduce the published tables up to the `seconds` columns (and any ILP timeout that depends on machine
speed). The published Boxoban and Cube agents runs were made before `--no_ilp` existed, through an equivalent
uncommitted wrapper (`ilp.ORTOOLS_AVAILABLE = False` then `bench.main()`); `--no_ilp` skips `ours_ilp` and makes
`TapeSim` use BFS on the folded graph, which is what that wrapper did. The agents CSVs written by the current code
also carry `delta`, `eta`, `slack`, `episodes`, `N`, `use_ilp`, `seed` and `inst_seed` columns, and skipped constrained
rows carry `ilp_status`; the committed CSVs in `docs/data/` predate those columns. Raw CSVs behind every table are in
`docs/data/main/`, `docs/data/rf95|rf97|rf100/` and `docs/data/bind/` (tables: `docs/results.md`, `docs/results_rf95.md`,
`docs/results_bind.md`).

Two further generated benchmarks are available but not part of `all` or the published tables: `--bench sokoban2` (7x9,
2 boxes, `T*` targets 6/10/14/18/22) and `--bench sokoban3` (8x10, 3 boxes, `T*` targets 10/14/18/22/26); both use the
Sokoban generator with reverse-play depth 60 to 600 and fill every bucket at `--n 5` (about 3 s and 25 s respectively).

## Using real Boxoban levels

The repo ships no real levels and downloads nothing. The built-in `boxoban` benchmark is a locally generated 10x10,
4-box imitation. To run on real levels, obtain a file yourself in DeepMind's Boxoban text format (for example one of
the `.txt` files of the public `google-deepmind/boxoban-levels` repository, cloned or downloaded by you) and point the
CLI at it:

```bash
python -m tapegraph.bench solvers     --bench boxoban_file --boxoban_file path/to/000.txt --n 20 --out boxoban_real
python -m tapegraph.bench agents      --bench boxoban_file --boxoban_file path/to/000.txt --n 20 --episodes 20 --no_ilp --out boxoban_real
python -m tapegraph.bench constrained --bench boxoban_file --boxoban_file path/to/000.txt --n 20 --out boxoban_real
```

`--bench boxoban_file` and `--boxoban_file PATH` must be given together, and the benchmark exists only then (it is not
part of `all`). Each level starts with a `; <index>` line followed by its grid (`#` wall, space floor, `.` goal, `$` box,
`@` player, `*` box on goal, `+` player on goal). The loader is strict: a level that is not rectangular, has no or
several players, a different number of boxes and goals, an unknown character, or is not enclosed by walls stops the run
with an error naming the level's index. With this benchmark `--n` is the maximum number of levels used (the first `n`
in the file) instead of instances per `T*` bucket, and `--seed` has no effect. `T*` is computed by the A* oracle (node
cap 300,000). A level the oracle cannot solve, or that is already solved (all boxes on goals, `T*` = 0), is not dropped: every CSV gets a `solver=skipped` (`method=skipped` for
agents) row for it with `T=-1` and the oracle's status (`no_path`, `node_limit` or `already_solved`); rows for loaded levels also carry
an `index` column (position in the file). A tiny hand-made 3-level sample in this format is in
`tests/data/boxoban_sample.txt`. **No results on real Boxoban levels are included in this repository**; the published
tables use only the generated benchmarks.

Notes: the validator checks rectangular rows, legal characters, one player, as many boxes as goals, and that the player
cannot reach the grid border. It does not require 10x10, does not accept `-` as a floor character, and does not check
that boxes are reachable: a level with an unreachable box simply comes back as a `skipped` row (`no_path` or
`node_limit`). Output files are named `<command>_boxoban_file.csv`, so two different level files written to the same
`--out` overwrite each other; use a separate `--out` per file.

## Layout

See `docs/superpowers/specs/2026-10-22-tape-graph-design.md`. The measured tables from the run described below are
in `docs/results.md`.

## Figures

`docs/figures/*.svg` are drawn from the committed CSVs under `docs/data` by `python scripts/make_figures.py`
(`--data docs/data --out docs/figures`; stdlib and numpy only, no plotting library, output is byte-identical on re-run).
Per benchmark: agent success vs `T*` with 95% Wilson bands, solver nodes and seconds vs `T*` (log y; failed rows
are hollow crosses in a strip above the plot, never dropped), the ILP solve rate vs `T*`, the ILP-vs-A* seconds
scatter for each `c_slack` of the binding constrained design, and the solve rate by `c_slack`. Directories that land
later (for example `docs/data/new_agents`) are picked up on the next run.

## How the results were produced

Single machine, seed = CLI default (1). Defaults for everything not listed: budget `B = T* + 2`
(`--slack 2`), `--max_nodes 500000`, ILP `time_limit` 10 s per solve (the limit applies to the solver; graph construction and model building add to the wall-clock, so recorded `timeout` rows take 10 to 21 s), `--delta 0.16`, `--eta 0.04`, `--N 16`,
`--res_frac 0.9`. The solvers, agents and `frac` constrained runs used `--n 5` instances per `T*` target for every benchmark (the `bind` runs use other `--n`, see below; River 6 targets = 30 instances, Sokoban
25, Boxoban 20, Cube 25). Instances are accepted within +-1 of the target and reported under their true `T*`, so
rows in the tables are keyed by actual `T*` and have 1 to 5 instances each.

| benchmark | solvers | agents | constrained |
|---|---|---|---|
| river | `solvers --bench river --n 5` (4 s) | `agents --bench river --n 5 --episodes 100` (238 s) | `constrained --design frac --bench river --n 5` (4 s) |
| sokoban | `solvers --bench sokoban --n 5` (12 s) | `agents --bench sokoban --n 5 --episodes 100` (367 s) | `constrained --design frac --bench sokoban --n 5` (13 s) |
| boxoban | `solvers --bench boxoban --n 5` (140 s) | `agents --bench boxoban --n 5 --episodes 20 --no_ilp` (2267 s) | `constrained --design frac --bench boxoban --n 5` (136 s) |
| cube2 | `solvers --bench cube2 --n 5` (228 s) | `agents --bench cube2 --n 5 --episodes 30 --no_ilp` (812 s) | `constrained --design frac --bench cube2 --n 5` (171 s) |

The constrained column is the `frac` design (see below for `bind`). Times are from the run logs. The solvers and constrained runs were done sequentially (about 710 s in total). The
agents runs were **re-run after a seeding fix** (commit b7f6106: before it, every instance in a benchmark received the
same noise draws; now each instance gets its own seed `seed + 7919 * index`, shared by all methods of that instance so
the comparison stays paired). The first agents results were discarded. The four re-runs ran as parallel processes
(longest 2267 s), so their `seconds` columns are slightly inflated by contention. Also, `react` and `tape` `seconds`
include Oracle distance computations (A*, 300k node cap, on off-path states; e.g. 14 to 17 s per episode on one
Boxoban `T*` 7 instance, against about 0.002 s for `ours_astar`), so they are not comparable to the `ours_*` times.
Then `python -m tapegraph.bench report`.

Deviations from the nominal loop above:

- **Fewer episodes for the two expensive benchmarks.** Boxoban agents used `--episodes 20` and Cube agents
  `--episodes 30` instead of 100. With 20 to 30 episodes a success rate has a standard error of roughly 0.05 to
  0.09 per instance, and the Boxoban and Cube buckets have 1 to 5 instances each.
- **ILP disabled in the Boxoban and Cube agents runs.** Those two runs were started through a small uncommitted wrapper
  that set `ilp.ORTOOLS_AVAILABLE = False` before calling `bench.main()` (now the `--no_ilp` flag; see Run). Consequences: (a) there are **no `ours_ilp` rows**
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
- Constrained, `frac` design (below): A* had 1 `node_limit` (Cube `T*` 11); the ILP had 5 `too_large` and 2 `timeout` on the 7 Cube
  instances it was run on, and 0 successes.

**3. Constrained, `frac` design: ILP vs resource-constrained A*.** (The redesigned `bind` experiment is a separate section below.) The resource budget is `floor(0.9 x resource of the unconstrained
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
- The ILP never solved more instances than A* in the constrained table, and was faster only in a row where it solved 0 of 5 (Cube `T*` 11: 2.17 s vs 5.59 s, failing fast with `too_large`).

**4. Success within budget under noise** (`delta` 0.16 planning error, `eta` 0.04 execution noise; episodes: 100 River
and Sokoban, 30 Cube, 20 Boxoban; each instance has its own noise seed, shared by the methods). Smallest and largest
`T*` bucket:

| bench | T* | react | tape | ours_astar | ours_ilp |
|---|---|---|---|---|---|
| river | 4 / 14 | 0.752 / 0.246 | 0.996 / 0.922 | 0.996 / 0.94 | 0.998 / 0.938 |
| sokoban | 5 / 23 | 0.66 / 0.05 | 0.98 / 0.755 | 0.98 / 0.81 | 0.98 / 0.80 |
| boxoban | 7 / 21 | 0.533 / 0.05 | 0.983 / 0.80 | 0.983 / 0.817 | none |
| cube2 | 3 / 11 | 0.84 / 0.32 | 1.0 / 0.947 | 1.0 / 0.94 | none |

Averaged over instances (the `tape` rows use the real ILP for River and Sokoban but BFS on the folded graph for
Boxoban and Cube), success is react / tape / ours_astar / ours_ilp: River 0.455 / 0.951 / 0.954 / 0.959,
Sokoban 0.248 / 0.862 / 0.872 / 0.874, Boxoban 0.225 / 0.850 / 0.855 / none, Cube 0.539 / 0.967 / 0.965 / none.

`python -m tapegraph.bench report` appends three sections after all older ones: 95% Wilson intervals per (bench, `T*`,
method) bucket, the same pooled per benchmark, and the paired differences `ours_astar - tape` and
`ours_astar - react` with a 95% percentile bootstrap CI. Pooling rule: successes = sum over instances of
round(success x episodes), trials = episodes x instances (the Wilson interval treats those trials as independent);
the instance is the unit of the paired bootstrap (the difference of the two methods' success on the same instance,
resampled over instances). Skipped levels (`T` = -1) are excluded and counted; CSVs without an `episodes` column use
100/100/20/30 episodes (River/Sokoban/Boxoban/Cube), and the report says so.

- ReAct-sim falls with `T*` overall (not monotonically on Boxoban: 0.20 at `T*` 8, 0.30 at 9, 0.35 at 11, 0.225 at 15,
  with few instances per bucket) and is far below the others from the first bucket (0.53 to 0.84 at the smallest `T*`,
  0.05 to 0.32 at the largest). `tape`, `ours_astar` and `ours_ilp` are within a few points
  of each other everywhere (largest `tape` vs `ours_astar` gap: 0.055 at Sokoban `T*` 23). Per instance, `tape` has
  higher success than `ours_astar` on 10 of 100 instances, lower on 23, equal on 67, so `ours_astar` >= `tape` on 90
  of 100. This slightly favours `ours_astar`, but the pooled margins are small (0.1 to 1.0 percentage points per
  benchmark; Cube is the one where `tape` is ahead, by 0.1) and not shown to matter. Note the `tape` rows use the real
  ILP for River and Sokoban but BFS on the folded graph for Boxoban and Cube. `tape` runs more
  solves per episode at large `T*` (Sokoban `T*` 23: 5.04 vs 3.24 for `ours_astar`). `ours_ilp` tracks `ours_astar`:
  higher on 14 and lower on 5 of 30 River instances (pooled 0.959 vs 0.954), higher on 3 and lower on 2 of 25 Sokoban
  instances (0.874 vs 0.872), so no meaningful difference, and it takes far longer per episode (River `T*` 14: 0.065
  vs 0.0012 s; Sokoban `T*` 23: 0.2037 vs 0.0068 s).
- `tape` and `ours_astar` are close by construction, not by coincidence: `TapeSim` draws its rollouts from an exact
  oracle with 16% injected errors, folds 16 of them, and takes a shortest path in that folded graph, so its plan is
  (close to) an optimal path of the true graph, and `ours_astar` then follows an optimal path of the true graph. The
  data agree: `tape` and `ours_astar` have identical success on 67 of the 100 instance rows (River 19/30, Sokoban
  10/25, Boxoban 16/20, Cube 22/25) and their mean steps per benchmark differ by at most 0.015 (River 9.495 vs 9.483,
  Sokoban 14.624 vs 14.623, Boxoban 14.69 vs 14.675, Cube 7.408 vs 7.408). The 43 to 63 point pooled gap to ReAct-sim
  (River 0.496, Sokoban 0.614, Boxoban 0.625, Cube 0.428) comes from the modelling assumption that planning errors are
  injected unfiltered into every recommendation and never corrected. So the real difference between `ours` and
  TAPE-sim in these experiments is cost (no oracle, no rollouts, no ILP), not success rate.
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
  are roughly consistent with a separate 200-episode check I ran earlier on the old seeding (`ours_astar`, `T*` 5: about
  0.99, `T*` 7: about 0.96, `T*` 9: 0.92 to 0.94); that check is not in the repository and cannot be reproduced from it.

**Does the ILP win anywhere?** Not in any regime tested here (with the thin-data caveats below). The regime where it might help, a resource budget that forces a longer path, was barely exercised by the `frac` design and is exercised on River and Cube, only thinly on Sokoban and Boxoban, by the redesigned `bind` design.
- Unconstrained: the ILP is the slowest of the five solvers in every `(benchmark, T*)` bucket except Cube `T*` 11 (34 to
  136 times slower than A* on River and Sokoban). Its node count is below BFS in some Sokoban and Boxoban buckets, but
  ILP "nodes" is the size of the bounded subgraph it builds. The Cube `T*` 11 exception (ILP 3.3 s vs A* 4.4 s) is a
  bucket where it solved 0 of 5 and failed fast with `too_large`.
- Constrained, `frac` design, main table (`res_frac` 0.9): the ILP never solved more instances than A*, and was faster only in a row
  where it solved 0 of 5 (Cube `T*` 11). **But the resource budget never lengthened the optimal path in any solved
  instance:** all 30 instances A* solved (River 24, Cube 6) have `cost == T*`, and the 24 the ILP solved (all River) too.
  In the supplementary runs exactly 3 solved instance-runs were forced to a longer path (Sokoban `T*` 17 at 0.95, and
  `T*` 17 and `T*` 21 at 0.97, cost `T*` + 2 each; the two `T*` 17 runs are the same instance, so 2 distinct instances),
  and the ILP matched A* on all of them. So for the `frac` design, the case a resource-constrained ILP is meant for (a
  budget that forces a trade-off against length) was effectively not exercised; that statement is about this design
  and its original resources only. The `bind` design below does exercise it (131 A* rows and 110 ILP rows with the
  optimum strictly longer than `T*`), and there the ILP again matched A* where it solved and was slower, except on rows
  where it failed fast.
- Why Sokoban and Boxoban are infeasible below the optimum's resource (`frac` design, original resources): the resource is steps plus 2 per push (a push
  costs 3, a walking move 1). With length slack 2, a path can only use fewer resource units than the length-optimal
  path by using fewer pushes (each saved push saves 2 units; extra walking only adds), and `floor(X * resource of the
  optimum)` for X below 1 already needs at least one unit saved. A path with fewer pushes than the length-optimal one
  and at most 2 extra moves almost never exists, which matches the data (69 of 69 skipped rows in the main run are
  `infeasible` for A*; River and Cube resources are not tied to pushes and are infeasible only on the shorter buckets).
  I checked this structurally (the argument above) and by A* and the ILP agreeing on 8 spot-checked instances, not by
  enumerating push counts.
- The ILP's result on skipped rows was not stored in the published CSVs (A* alone decided `infeasible`). The current code
  records it as `ilp_status` on every skipped-infeasible row and `report` counts the rows where `ilp_status` is `ok` (a
  disagreement, expected 0); the published CSVs have none recorded (`0 of 69` in `docs/results.md`).
- Fairness caveat in both directions: the ILP's subgraph is the `{g + h <= T* + slack}` ball, which is larger than the
  `f <= T*` region A* expands (the spec's "same subgraph A* would expand" is only approximately true); its Python graph
  build counts toward its time; and CP-SAT runs with 8 workers against single-threaded A*.

### Supplementary: constrained at res_frac 0.95

The main constrained table uses `--res_frac 0.9` and leaves Sokoban and Boxoban with no solved instance. Extra runs
for Sokoban and Boxoban (`constrained --design frac --bench {sokoban,boxoban} --n 5 --res_frac X --out results_rfNN`, tables in
`docs/results_rf95.md`; same instances as the main run; run concurrently with other jobs, so timings are a little
inflated) show that **it is still almost all infeasible** just below the optimum's resource: only 3 of the 90 Sokoban/Boxoban
instance-runs at 0.95 and 0.97 were feasible (1 + 2, all Sokoban; see the structural explanation under the ILP
verdict).

| res_frac | sokoban skipped (infeasible) / solved | boxoban skipped / solved | ILP vs A* where solved |
|---|---|---|---|
| 0.95 | 24 / 1 | 20 / 0 | Sokoban `T*` 17: both cost 19, agree; A* 0.0047 s, ILP 0.1458 s |
| 0.97 | 23 / 2 | 20 / 0 | Sokoban `T*` 17 and 21: both agree on cost; A* 0.0064 to 0.0068 s, ILP 0.17 to 0.21 s |
| 1.0 (non-binding by construction) | 0 / 25 | 0 / 20 | Sokoban: both 25/25, agree 25/25; A* 0.0017 s vs ILP 0.1033 s mean. Boxoban: A* 20/20, ILP 14/20 (6 `timeout`, all at `T*` >= 16), all 14 ILP solutions agree with A*; on those 14, A* 0.028 s vs ILP 2.02 s |

So for Boxoban there is no instance at 0.95 or 0.97 where the resource budget binds and is still feasible, and for
Sokoban only 1 and 2 of 25. In those, the ILP agreed with A* and was slower. With a non-binding budget (1.0) the
pattern is the same as in the unconstrained table.

### Constrained experiment, redesigned so the budget binds

**Why.** The `frac` design above never forced a longer path in the main table (and in only 3 supplementary instance-runs).
The likely cause is that its resources (steps plus 2 per push, passengers carried, quarter-turn 1 / half-turn 2) rarely
trade off against length: the probe below supports this empirically (0 of 30 River, 0 of 8 Cube2, 2 of 25 Sokoban and 0 of
3 Boxoban instances had a cheaper longer path), and for Sokoban and Boxoban the structural argument given under the ILP
verdict points the same way. I have not proven it in general. The redesign makes the resource constraint cut off every
length-optimal path while still leaving a feasible, longer one.

**Probe: do the resources trade off against length at all?** For each instance: does a path of length <= `T*` + slack
exist with strictly less resource than every length-`T*` path? Counts are instances with a trade-off / instances in the
set. The probe ran slack 2, 4 and 8 for River and Sokoban but only 2 and 4 for Cube2 and Boxoban; on the benchmarks and
resources where more than one slack was run the counts were identical across slacks, i.e. where a trade-off exists it
already existed at slack 2.

| benchmark (instance set) | resource | trade-off instances |
|---|---|---|
| River (30) | passengers carried (original) | 0 / 30 |
| River | missionaries x 3 | 0 / 30 |
| River | passengers squared | 7 / 30 |
| Cube2 (8; `T*` in {5, 7, 8}) | half-turn 2 / quarter-turn 1 (original) | 0 / 8 |
| Cube2 | quarter-turns only | 1 / 8 |
| Cube2 | half-turns only | 7 / 8 |
| Sokoban (25) | push 3 / move 1 (original) | 2 / 25 |
| Sokoban | pushes only | 2 / 25 |
| Boxoban (3 small instances; `T*` in {8, 12, 16}) | push 3 / move 1 (original) | 0 / 3 |
| Boxoban | pushes only | 0 / 3 |

These numbers come from a throwaway run of the same logic as `scripts/probe_resources.py` (seed 1, instance sets from
`make_instances`). Sample sizes: `n` = 5 per `T*` bucket for River and Sokoban, `n` = 4 for Cube2 filtered to `T*` in
{5, 7, 8}, `n` = 3 for Boxoban filtered to `T*` in {8, 12, 16}. The probe's A* node caps were 300k (River, Sokoban) and
200k (Cube2, Boxoban), against 500k in the actual runs; an instance where A* hit its cap is not counted. The run's output
was not saved, so the table is not reproducible from stored data; the script is committed and should regenerate it, but I
have not re-run it for this write-up. The Boxoban probe sample is tiny (3 instances) and says very little about Boxoban.

**Design** (`constrained --design bind --c_slack 4`; code: `bench.min_resource`, `bench.bind_budgets`,
`bench._constrained_bind`). For each instance, with `T*` the optimal length:
- `r_opt` = the minimum resource among paths of length <= `T*`; `r_min` = the minimum resource among paths of length
  <= `B = T* + c_slack` (default `c_slack` 4). Both come from bisection over A* calls with a resource budget, so the
  bisection runs only A*.
- If `r_min >= r_opt` the instance is skipped with status `no_tradeoff` (a `solver=skipped` row).
- Otherwise there are two levels. `bind`: `R = r_opt - 1`, so every length-`T*` path violates the budget and the
  optimum is strictly longer than `T*`. `tight`: `R = r_min`, the hardest feasible budget. `tight` is run only when
  `r_min < r_opt - 1`; otherwise `bind` already equals `r_min` (this is the case for 7 of the 18 Cube trade-off
  instances).
- A* and the CP-SAT ILP both run at `(B, R)` with the same `--max_nodes`. `forced_longer` = 1 when the returned cost is
  above `T*`.

**Resources used** (`res_bind`, applied through a `ResView` wrapper; the original `res` is unchanged and still used by
the `frac` design): Sokoban and Boxoban count **pushes only** (walking is free); River counts **passengers squared**
(crowded boats cost more); Cube counts **half-turns only** (quarter-turns are free). These were chosen *because* they
create trade-offs (see the probe). So this experiment tests solver behaviour under a binding resource budget; it says
nothing about which resource a real application would care about.

**Run**: seed 1, `--max_nodes 500000`, ILP 10 s limit, one process at a time (so the `seconds` columns are not
contended): River `--n 20` (8 s), Sokoban `--n 20` (19 s; it produced 90 instances instead of the nominal 100, because
`make_instances` warns on stderr and continues when a `T*` bucket under-fills), Boxoban `--n 10` (118 s), Cube2 `--n 4` (397 s). Tables:
`docs/results_bind.md`; raw rows: `docs/data/bind/constrained_<bench>.csv`.

**Results** (all counts recomputed from `docs/data/bind/*.csv`). A "row" is an `(instance, level)` pair: a trade-off
instance contributes a `bind` row and, when it exists, a `tight` row.

| bench | instances | with trade-off | `no_tradeoff` skips | A* rows ok (see caveat 1) | ILP rows ok | ILP failures | ok-vs-ok pairs with equal cost | mean seconds where both ok: A* / ILP (ratio) |
|---|---|---|---|---|---|---|---|---|
| river | 120 | 43 | 77 | 86 / 86 | 86 / 86 | none | 86 / 86 | 0.0007 / 0.0493 (66x) |
| sokoban | 90 | 7 | 83 | 14 / 14 | 14 / 14 | none | 14 / 14 | 0.0044 / 0.2152 (49x) |
| boxoban | 40 | 1 | 39 | 2 / 2 | 2 / 2 | none | 2 / 2 | 0.0730 / 7.3358 (100x) |
| cube2 | 20 | 18 | 2 | 29 / 29 | 8 / 29 | 15 `too_large`, 6 `timeout` | 8 / 8 | 0.0043 / 0.9769 (228x) |

- Overall there were 110 ok-vs-ok pairs and the two solvers returned the same cost in all 110. Every solved row (131 A*,
  110 ILP) has `forced_longer` = 1, but that is a sanity check of the construction, not a result: under `bind`,
  `R = r_opt - 1` makes every length-`T*` path infeasible, and under `tight`, `R = r_min < r_opt` does too, so any solved
  row must cost more than `T*`. The informative content is the size of the increase (`cost - T*`): +2 on all 86 River rows
  and all 14 Sokoban rows, +1 on the 2 Boxoban rows, and +1 (18 rows), +2 (8), +3 (2), +4 (1) on the 29 Cube A* rows.
  All 201 skips are `no_tradeoff`; none was skipped for `node_limit` or any other status.
- The ratio is, per benchmark, the ratio of the two mean seconds on rows where both solved (per row it ranges from 25x to
  152x on River, 28x to 76x on Sokoban, 80x to 134x on the two Boxoban rows, 44x to 1270x on Cube). Boxoban is a single
  instance at two levels. Cube's 228x rests on 8 rows (the easy buckets `T*` 3 and 5, 6 instances) with A* at about 4 ms.
  River's A* times (about 0.7 ms) are near timer and setup scale, so the River per-row ratios are noisy.
- Instances with a trade-off, by `T*`: River 14, 12, 0, 4, 13, 0 at `T*` 4, 6, 8, 10, 12, 14 (out of 20 per `T*`).
  Sokoban 1, 1, 1, 1, 2, 1 at `T*` 13, 14, 18, 19, 21, 22 (out of 90 instances across `T*` 5 to 23; the other nine `T*` values
  have none). Boxoban 1 instance, `T*` 12 (out of 40). Cube 3, 3, 4, 4, 4 at `T*` 3, 5, 7, 9, 11 (4 instances per `T*`;
  the 2 skips are one each at `T*` 3 and 5).
- Cube, ILP by `T*` (bind rows / tight rows ok): `T*` 3: 3 of 3 / none; `T*` 5: 3 of 3 / 2 of 2; `T*` 7: 0 of 4 / 0 of 2
  (all 6 `timeout`); `T*` 9: 0 of 4 / 0 of 3 (`too_large`); `T*` 11: 0 of 4 / 0 of 4 (`too_large`). So the ILP solved 6 of
  the 18 Cube trade-off instances (all at `T*` <= 5) and failed on the other 12 at every level run. Failed rows took 3.25 s
  on average for `too_large` and 20.17 s for `timeout` (the 10 s solver limit plus graph and model building).
- **The one place the ILP is faster than A*:** the 8 Cube `T*` 11 rows (4 instances, both levels). The ILP took 2.8 to 3.2 s
  against 7.9 to 9.6 s for A*, but it returned `too_large` on all 8 and A* solved all 8. A fast failure is not a win. There
  is no row where both solved and the ILP was faster; on every River, Sokoban and Boxoban row the ILP was slower.
- Node counts are not comparable between the two solvers (caveat 3). For reference, on the both-ok rows the means are
  A* 42.4 vs ILP 32.0 (River), 268.8 vs 397.1 (Sokoban), 1,261 vs 8,330 (Boxoban), 185.5 vs 2,832 (Cube).

**Findings.**
- The constrained regime is now exercised. On River (43 of 120 instances have a trade-off, 86 rows) and Cube (18 of 20, 29
  rows) every solved row has a strictly longer optimum, as the construction guarantees; the size of the increase (above) is the
  informative part. On Sokoban (7 of 90 instances) and Boxoban
  (1 of 40) trade-offs are rare under this resource, so those rows are thin: 14 and 2 rows, from 7 and 1 instances.
- The ILP still wins nowhere. Where both solved (110 pairs) it matched A* on cost every time and was 49x to 228x slower per
  benchmark (ratio of mean seconds on rows where both solved; Cube's 228x rests on 8 rows). On Cube it solved only 8 of 29 rows (6 of 18 instances) and failed on every row at `T*` >= 7. The only rows with
  the ILP faster are the Cube `T*` 11 failures.
- This is evidence about these four benchmarks, these resources, `c_slack` 4 and a 10 s ILP limit. It does not show that the
  ILP cannot win elsewhere (for example with a tighter `c_slack`, which I did not try).

**Caveats for this experiment.**
1. A* success at `tight` is partly tautological. The `tight` budget is `R = r_min`, and `min_resource` already ran A* at
   exactly `(B, r_min)` during bisection and got `ok`, so the A* call at `tight` repeats an answer already obtained (the same
   holds for `bind` on the 7 Cube instances where `r_min = r_opt - 1`). A* `ok` here must not be read as a headline solve
   rate; the informative quantity is the ILP's behaviour given that A* is feasible. Instances where A* hit `node_limit`
   during the bisection are skipped and would show in the failure breakdown, which biases the sample toward instances A*
   can handle. None occurred in this run (all 201 skips are `no_tradeoff`).
2. Small, skewed samples. Per-`T*` counts are listed above: River's trade-off instances sit at `T*` 4, 6, 10, 12 only,
   Sokoban has 7 instances over six `T*` values, Boxoban has one instance, and Cube has 18 trade-off instances (11 of them with a `tight` level).
   The unequal counts come from where trade-offs happen to exist, not from design.
3. Fairness asymmetries. The ILP's `max_nodes` counts states in the whole `g + h <= B` ball (no resource pruning; it grows
   with `c_slack`), while A* counts expansions after resource pruning and dominance. The ILP has a 10 s solver limit, which A*
   lacks. CP-SAT uses 8 workers against single-threaded A*. The bisection that picks `R` runs only A*. Some of the ILP's Cube
   `too_large` failures may come from `c_slack` 4 enlarging the ball; I did not test a smaller `c_slack`.
4. `agrees_with_astar` is 0 both when the ILP failed and when the costs differ. Here every row where both solvers returned
   a path is an ok-vs-ok pair (110 of them) and all 110 agree, so the 21 Cube zeros are ILP failures, not disagreements.
5. Sokoban and Boxoban `res_bind` is pushes only (walking is free), and Cube counts half-turns only. These are unusual
   resources chosen for having trade-offs (see the probe), not a realistic cost model.
6. The skipped rows record only A*'s bisection verdict (`no_tradeoff`); the ILP was not run on them.

## Caveats

- ReAct and TAPE are simulated with the paper's noise model, not real LLMs.
- The constrained ILP-vs-A* results come from two designs with different resources: `frac` (original resources, the budget rarely binds) and `bind` (resources chosen to create trade-offs; thin on Sokoban and Boxoban). See the caveats under "Constrained experiment, redesigned so the budget binds".
- Sokoban/Boxoban instances are rejection-sampled from long reverse random walks and reported by their true `T*`.
- TAPE-sim minimises path length in the folded graph, not TAPE's node-score objective.
- The ILP is an edge-flow formulation, not time-expanded.
- Cost means in the tables are over solved instances only.
- Buckets have 1 to 5 instances (and 20 to 100 episodes each), so success-rate differences of a few points are within
  noise.
- `Replan` still plays the first legal action when its solver returns a non-ok status (timeout, `too_large`,
  `node_limit`, or a legitimate `no_path`, e.g. when the remaining budget is exhausted off the plan), but the fallback is
  now counted: `solver_fail` is the episodes' mean number of solves whose status was not ok, written to the agents CSV and
  shown in the agents table of `report`. The published CSVs in `docs/data` predate the column; the earlier reading that
  `ours_ilp` is unaffected (it ran only on River and Sokoban, where the ILP never failed in the solvers table) rests on
  the solvers table, not on a recorded count.
- `TapeSim` re-plans only when the state deviates from its plan (per our spec), whereas TAPE-main's
  `OursGraphILPPolicy` re-folds and re-solves at every step, so `solves` and `seconds` are not directly comparable
  with the paper.
- `TapeSim` calls `solve_graph` without a length budget, whereas TAPE-main passes `budget=budget_remaining`.
