# tape-graph full project: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan
> task by task. Unlike the first plan, tasks here specify interfaces and acceptance tests rather than complete code;
> the implementer writes the code and the tests first (TDD) and a reviewer checks them against the acceptance list.

**Goal:** Turn `tape-graph` (v0: four benchmarks, five solvers, simulated ReAct/TAPE, a binding constrained
experiment) into a complete project: packaged and polished, with larger benchmarks and stronger statistical
evidence, publication-style figures and a paper-style write-up, all reproducible from one command.

**Scope chosen by the user:** (1) plots + paper-style write-up, (2) packaging and polish, (3) bigger benchmarks and
stronger evidence. **Not in scope:** real-LLM runs; downloading anything (a Boxoban loader for a user-supplied file is in
scope, the download is not).

**Spec:** `docs/superpowers/specs/2026-10-22-tape-graph-design.md`. **Prior plan:** `2026-10-22-tape-graph.md`.
**State at start:** commit `c61856d`, 83 tests, `docs/REPORT.md` section 9 lists the gaps this plan closes.

## Global Constraints

- Python 3.12; runtime deps stay `numpy` and `ortools`; `pytest` for tests. **No new dependencies** (in particular no
  matplotlib, pandas, or LaTeX). Figures are generated as SVG by a small dependency-free helper.
- Nothing is downloaded. Real Boxoban levels are supported only through a loader for a file the user supplies.
- `TAPE-main` is never modified. Published tables in `docs/results*.md` and CSVs in `docs/data/` are never edited by
  hand; new results go to new files/directories (`docs/data/<name>/`, `docs/results_<name>.md`).
- Failures stay visible (statuses are rows, never dropped); cost means over solved instances only; simulated ReAct/TAPE
  are always labelled simulated; every number in prose is recomputed from committed CSVs by the author and re-checked by
  a reviewer.
- Existing behaviour is preserved: all 83 tests keep passing; `--design frac` and the published commands still reproduce.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; commits use
  `git -c user.name="tape-graph" -c user.email="harshvardhanr264@gmail.com"`.
- Long experiments run one process at a time (timing columns must not be contended), writing to a fresh `--out` directory.

## File structure (additions)

```
pyproject.toml                       T1
.github/workflows/ci.yml             T1
tapegraph/__main__.py                T1   (python -m tapegraph == bench CLI)
tapegraph/stats.py                   T4   (Wilson interval, bootstrap helper)
tapegraph/plots.py                   T5   (dependency-free SVG charts)
tapegraph/problems/cube3.py          T3
tapegraph/problems/boxoban.py        T2   (adds load_boxoban_file)
scripts/make_figures.py              T5
scripts/make_paper.py                T5   (assembles docs/paper.md tables from CSVs)
docs/paper.md  docs/figures/*.svg    T5
tests/test_cube3.py test_stats.py test_plots.py test_polish.py ...
```

---

### Task 1: Packaging and polish

**Files:** create `pyproject.toml`, `tapegraph/__main__.py`, `.github/workflows/ci.yml`, `tests/test_polish.py`;
modify `tapegraph/bench.py`, `tapegraph/baselines/replan.py`, `tapegraph/execute.py`, `tapegraph/solvers/ilp.py`
(docstring), `scripts/probe_resources.py`, `README.md` (install/run section only).

**Acceptance:**
1. `pip install -e .` works (pyproject with setuptools, package `tapegraph`, console script `tapegraph` = bench `main`);
   `python -m tapegraph solvers --bench river --n 1 --out <tmp>` works; version string `tapegraph.__version__ = "1.0.0"`.
2. `bench` gets a subcommand `all --profile {smoke,full} --out DIR`: `smoke` runs solvers, agents, constrained(bind) and
   report on River and Cube2 with tiny `--n`/`--episodes` and finishes in under 3 minutes; `full` runs exactly the
   published commands from the README (solvers/agents/constrained-frac/constrained-bind on all four benchmarks with the
   documented `--episodes`, `--no_ilp` and `--n` values), sequentially, each into its own subdirectory of `--out`, and
   writes `run_manifest.json` (commands, parameters, wall-clock per step, git commit if available, python/ortools/numpy
   versions). `full` is not run in tests.
3. Every CSV row written by `solvers` and `constrained` (not only `agents`) carries the run parameters
   (`seed`, `slack`/`c_slack`, `max_nodes`, `n`, ILP `time_limit`); report/old-CSV handling still works on old CSVs.
4. Close the known test gaps with real assertions (tests fail if the logic is broken): BFS `node_limit`; IDA* iterative
   deepening on a toy graph where `h` underestimates (bound increases at least twice); a negative control: a Problem
   subclass with an inadmissible `h` makes A* return a longer path than BFS and the agreement check from the Sokoban test
   detects it; `make_instances` stderr warning when a bucket under-fills (use a benchmark/targets that cannot fill);
   weighted-A* `w` actually changes behaviour on a toy graph; mid-bisection abort in `min_resource`; the cube cache
   integrity branch (already tested) stays.
5. `Replan` counts solver failures (`solver_fail` attribute, non-ok solver status) and `evaluate`/`run_agents` write a
   `solver_fail` column (per episode mean) so silent fallbacks are visible; `ilp.solve` docstring no longer says "the same
   ball A* would expand".
6. `scripts/probe_resources.py` gets a `__main__` guard and an argparse (`bench` argument, `--n`), no import-time side
   effects, and reuses `bench.min_resource` instead of duplicating the bisection.
7. CI workflow (GitHub Actions, python 3.12, `pip install -e .[test]`, `pytest -q`, `tapegraph all --profile smoke`)
   committed (it cannot run here; validate the YAML parses with python).
8. README "Run" section updated: install, `tapegraph all --profile smoke|full`, and the single-command reproduction. 83+
   tests pass.

### Task 2: Multi-box Sokoban and a Boxoban file loader

**Files:** modify `tapegraph/benchmarks.py`, `tapegraph/problems/boxoban.py`; tests `tests/test_boxoban.py`,
`tests/test_bench.py`; fixture `tests/data/boxoban_sample.txt`.

**Acceptance:**
1. New registry entries `sokoban2` (7x9, 2 boxes) and `sokoban3` (8x10, 3 boxes), same generator as Sokoban; tune
   `T_targets` and `depth` so every bucket fills at `--n 5` within a minute each (record the numbers; drop a target rather
   than raising `max_tries`). Their agreement test (A*/IDA* vs BFS on nontrivial instances, as in `test_sokoban.py`) passes
   for `sokoban2` (BFS is feasible there) with a nontrivial-count assertion.
2. `load_boxoban_file(path) -> list[Sokoban-compatible (problem, start)]` for the DeepMind text format (lines starting
   with `;` start a level; 10x10 grids of `#`, space, `.`, `$`, `@`; some files also use `*`/`+`), with validation errors
   for malformed levels; a small hand-made fixture file (3 levels) in that format; `BENCHMARKS` gets a `boxoban_file`
   factory only when `--boxoban_file PATH` is given on the CLI (solvers/agents/constrained then use those levels; `T*`
   is computed by the oracle; levels the oracle cannot solve within the node cap are reported as skipped rows, not dropped).
3. README section "Using real Boxoban levels": how to obtain the file yourself and the command; states clearly that no
   real-level results are included.
4. All earlier tests pass; no network access anywhere.

### Task 3: Rubik's 3x3 (half-turn metric) with a corner pattern database

**Files:** create `tapegraph/problems/cube3.py`, `tests/test_cube3.py`; modify `tapegraph/benchmarks.py`.

**Design (given):**
- State: a hashable tuple `(corner_perm_index, corner_twist_index, edge_perm_tuple, edge_flip_tuple)` or an equivalent
  encoding; 18 moves (`U U2 U' D D2 D' L L2 L' R R2 R' F F2 F' B B2 B'`), unit cost; goal = solved. Standard cubie model
  (URF UFL ULB UBR DFR DLF DBL DRB / UR UF UL UB DR DF DL DB FR FL BL BR). Resource for the binding experiment
  (`res_bind`): half-turns only; `res` (original): half-turn 2, quarter-turn 1.
- Heuristic: corner pattern database (corner permutation 8! x twist 3^7 = 88,179,840 states, depth <= 11) built by a
  chunked, vectorised BFS using the independent-coordinate trick used in `cube2.py` (corner permutation and twist
  evolve independently under every move: next index = `PM[p,m]*2187 + TM[t,m]`); stored as `uint8`/`int8` (~88 MB) and
  cached under `.cache/` with the same integrity check as `cube2.py`. Chunk the frontier (e.g. 2M states) so peak memory
  stays under ~1 GB. `h(s) = pdb[corner index of s]` (admissible). Optionally `max` with an edge-orientation/permutation
  small database if it helps; not required.
- `random_start(rng, depth)`: a random walk of `depth` moves that never undoes the previous face (no immediate
  reversals, no same-axis repeats); true `T*` comes from the Oracle (A* with the PDB, `max_nodes` cap). Benchmark entry
  `cube3` with `T_targets` that fill at `--n 5` within a few minutes (expect roughly 3 to 8; record them).
- Prune: none. `exact_dist`: not available.

**Acceptance:**
1. BFS over the full state reproduces the known half-turn counts of distinct states at depth 1..4: 18, 243, 3240, 43239
   (a strong check of the move tables, including edges).
2. Moves are inverses (`U` then `U'`, `R2` twice), 4 quarter-turns of any face return to the same state, and the 8 corner
   cubies / 12 edge cubies stay valid (permutation of the same multiset, twist sum mod 3 == 0, flip sum mod 2 == 0) after
   100 random moves.
3. The PDB is admissible on instances: for 200 random scrambles of depth <= 5, `h(s) <= BFS distance` (BFS depth cap),
   the PDB depth histogram has `max == 11` and `pdb[0] == 0`, and its total entry count is 88,179,840; building it
   takes under ~5 minutes and the cache is reused on the second run (test the cache path with a monkeypatched small
   variant or check timing, not by rebuilding in CI; mark the full build test `slow` and skip it unless `--runslow`).
4. A*/IDA* with the PDB solve scrambles of depth 5 to 7 with cost equal to BFS where BFS is feasible (depth <= 5), and
   `T* <= scramble depth`; report node counts and seconds for depths 5..8 in your report.
5. `cube3` appears in `BENCHMARKS`; `bench solvers --bench cube3 --n 1` runs end to end; the CSV reports BFS `node_limit`
   as a row. Existing tests pass.

### Task 4: Statistics and more evidence tooling

**Files:** create `tapegraph/stats.py`, `tests/test_stats.py`; modify `tapegraph/bench.py` (report only),
`tapegraph/execute.py` if needed.

**Acceptance:**
1. `wilson_interval(successes, trials, z=1.96)` and `bootstrap_ci(values, stat=mean, B=2000, seed=0)` with tests against
   hand-computed values and edge cases (0/n, n/n, n = 0 returns NaN).
2. `report` adds, for the agents section, 95% Wilson intervals for success per (benchmark, T*, method) bucket computed
   from `successes = success_rate * episodes * instances` when the CSV carries `episodes` (old CSVs: use the documented
   episode counts from a lookup keyed by benchmark; document this) and a pooled-per-benchmark table with interval and
   the paired difference `ours_astar - tape` and `ours_astar - react` with a bootstrap 95% CI resampled over instances.
3. The failure breakdown and all old tables are unchanged for old CSVs (golden test on `docs/data/main`: regenerating
   the report into a temp dir reproduces `docs/results.md` byte-for-byte except the newly added sections, which are
   appended at the end).
4. `agents` can run `--episodes` per instance with `--instance_seed_offset`-free per-instance seeds exactly as before
   (no change to existing results).

### Task 5: Figures and the paper-style write-up

**Files:** create `tapegraph/plots.py`, `scripts/make_figures.py`, `scripts/make_paper.py`, `tests/test_plots.py`,
`docs/figures/*.svg`, `docs/paper.md`.

**Acceptance:**
1. `plots.py` provides `line_chart`, `bar_chart` and `scatter` (log axes optional) producing valid, self-contained SVG
   strings (axes, ticks, legend, title, colour-blind-safe palette, CI whiskers or bands, text escaping); tests parse the
   SVG as XML, check element counts for known inputs, escaping of `<`/`&`, log-axis tick values, empty-series handling.
2. `make_figures.py` reads only committed CSVs (`docs/data/**`) and writes the figures: (a) success vs `T*` per method per
   benchmark with Wilson bands; (b) unconstrained solver nodes and seconds vs `T*` (log y) with failure markers
   (`node_limit`/`too_large`/`timeout` shown, not hidden); (c) constrained bind: ILP vs A* seconds per row with failure rows
   marked, and the `c_slack` sweep; (d) ILP success rate vs `T*` per benchmark. Deterministic output (byte-identical on
   re-run).
3. `make_paper.py` assembles `docs/paper.md` from a template with tables and numbers generated from the CSVs (no
   hand-typed numbers in generated tables); sections: abstract, algorithm, related work (TAPE, ReAct, A*/IDA*/CP-SAT),
   method, benchmarks, experiments, results, limitations, reproducibility. Prose claims are limited to what the generated
   tables show; every limitation from `docs/REPORT.md` section 7 is carried over; simulated baselines are labelled.
4. A reviewer can regenerate figures and paper with one command and `git diff` shows no change.

### Task 6 (controller): experiments, README/REPORT refresh, final review, tag

Run (sequentially, new `--out` dirs, results copied to `docs/data/<name>/` and `docs/results_<name>.md`): solvers/agents/
constrained(bind) on `sokoban2`, `sokoban3`, `cube3`; bind c_slack sweep {2, 4, 8} on river, sokoban, sokoban2, cube2 (larger `--n`);
agents on River/Sokoban with `--episodes 300` for tighter intervals. Then refresh `README.md`/`docs/REPORT.md`
(new benchmarks, evidence, CIs, figures, paper), run the whole-branch review on the most capable model, fix, tag `v1.0.0`.
