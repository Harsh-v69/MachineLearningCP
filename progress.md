# Progress: TAPE Extension — Adaptive Graph Validation & Solver Generalization

**Overall status: all six phases have working code and results (about 97% of the plan). Phases 1 to 5 are the pipeline. Phase 6 (evaluation) has its core experiments done: ablation, memory test, weight tuning, proposer-quality sweep, and the Boxoban benchmark. The guide ruled out LLMs, so real-LLM runs and TAPE's LLM-native benchmarks are dropped (Sec 15). 66 tests pass, and everything is pushed to GitHub.**

**Status at a glance**

| Area | State |
|---|---|
| Pipeline (Phases 1 to 5) | Done, tested |
| Benchmarks | Sokoban (4 hand-made levels), River Crossing, Rush Hour, and Boxoban (3000 real levels, three difficulty sets) |
| Evaluation (Phase 6) | Ablation (Sec 14), experience store under state-dependent slip (14.1), ScoreWeights tuning (14.2), proposer sweep (14.3), Boxoban (Sec 16) |
| Demo | Guided walkthrough `demo/index.html` with a project map, three playable games, and a results page (Sec 11) |
| Main findings | The checker gives safety (River Crossing 0% to 100% safe) and better search (Boxoban solves 3 to 28 points more at the top budget). The adaptive solver cuts planning time where one piece moves. Memory helps on two games. Tuning found nothing better than defaults. |
| Open | Paper writing, optional extra Boxoban files, a learned (non-LLM) proposer if the guide allows it |


This document is meant to be read start to finish by a teammate who has not touched the code yet, and to be enough on its own to explain the project to the teacher. It covers what the project is, what's been built, why each piece exists, how to run it, and exactly what's left.

**[`docs/pipeline_diagram.html`](docs/pipeline_diagram.html)** is a system flow diagram covering the same ground visually: environment state in, validated optimal path out, with every stage in between labeled by phase.

---

## 1. What this project is

We are extending **TAPE** (Tool-Guided Adaptive Planning with Constrained Execution, Jeong et al. 2026), an LLM-agent framework that:

1. Asks an LLM for several *candidate plans* to solve a task.
2. Merges them into a single **plan graph** (shared states become shared nodes).
3. Uses an external solver (ILP/CP-SAT) to pick the best feasible path through that graph.
4. Executes that path with constrained decoding.
5. If the real world doesn't match what the graph predicted, it **replans** from the real state.

TAPE's own authors flag two things they did *not* solve:
- The plan graph is only as good as the LLM's raw candidates — nothing checks a candidate transition against the environment's actual rules before it's trusted.
- The solver is fixed and pre-specified per task, with no way to adapt.

Our project builds five extensions addressing these gaps, on top of a faithful reproduction of the TAPE baseline. The full 6-phase plan (see the roadmap artifact shared earlier) allocates roughly:

| Phase | Weight | Status |
|---|---|---|
| 1 — TAPE Baseline | 25% | ✅ Done |
| 2 — Adaptive Graph Validation | 20% | ✅ Done |
| 3 — Self-Improving Graph | 15% | ✅ Done |
| 4 — Dynamic Reachability/Utility Score | 15% | ✅ Done |
| 5 — Adaptive Path Selection (A*/AO* vs solver) | 15% | ✅ Done |
| 6 — Evaluation & Ablations | 10% | ✅ Core done (Sec 14 to 16); optional extras open |

**Phases 1 to 5 sum to 90%. Phase 6's core is done; what is left is listed in Sec 13.**

---

## 2. Repository layout

```
MachineLearningCP/
├── ML_CP.docx                 # original project proposal (source of truth for scope)
├── requirements.txt           # networkx, ortools, pytest (the Gemini client uses urllib, no SDK)
├── data/boxoban/              # three Boxoban level files, 1000 levels each (Sec 16)
├── results/                   # tables written by the Phase 6 experiments (ablation, memory, tuning, sweeps, Boxoban)
├── .env.example                # GEMINI_API_KEY (copy to .env, fill in, do not commit)
├── src/tape/
│   ├── env_base.py              # the Environment protocol every benchmark implements (see §8.0)
│   ├── envs/
│   │   ├── sokoban.py                   # benchmark 1 (Phase 1)
│   │   ├── boxoban.py                   # loader for the public Boxoban level files (Sec 16)
│   │   ├── river_crossing.py            # benchmark 2 (§8.1): missionaries and cannibals
│   │   ├── river_crossing_validator.py  # its Phase 2 validator: RiverSafetyValidator
│   │   ├── rush_hour.py                 # benchmark 3 (§8.2): sliding-vehicle traffic jam
│   │   └── rush_hour_validator.py       # its Phase 2 validator: RowGridlockValidator (§8.2.1)
│   ├── llm.py                  # candidate plan generation: MockLLMClient, AdversarialMockLLMClient, QualityProposer, GeminiClient (unused)
│   ├── search_proposer.py       # weighted A* proposer for levels too big for BFS (Sec 16)
│   ├── graph.py                # plan graph construction + validation/scoring hooks
│   ├── solver.py                # CP-SAT path selection (OR-Tools)
│   ├── executor.py             # constrained execution + mismatch-triggered replanning
│   ├── validator.py             # Phase 2: CornerDeadlockValidator (Sokoban)
│   ├── experience.py             # Phase 3: sqlite-backed ExperienceStore
│   ├── scoring.py                # Phase 4: score_transition() (regression, confidence, budget)
│   ├── path_selector.py          # Phase 5: astar_select_path(), decide_method(), select_path_adaptive()
│   └── metrics.py                # aggregate metrics across episodes
├── experiments/
│   ├── run_baseline.py          # CLI: Sokoban episode sweeps with any combination of extensions
│   ├── run_river_crossing.py     # CLI: same pipeline, river crossing
│   ├── run_rush_hour.py          # CLI: same pipeline, Rush Hour
│   ├── stress_test.py            # Phase 2 adversarial stress test (see §4.1)
│   ├── run_ablation.py           # Phase 6: 5 configs x 6 benchmarks x 2 proposers (Sec 14)
│   ├── run_experience_test.py    # Phase 6: experience store under state-dependent slip (Sec 14.1)
│   ├── tune_weights.py           # Phase 6: ScoreWeights grid search with held-out check (Sec 14.2)
│   ├── run_proposer_sweep.py     # Phase 6: benefit vs proposer quality (Sec 14.3)
│   ├── run_boxoban.py            # Phase 6: Boxoban benchmark (Sec 16)
│   └── export_demo.py            # regenerates demo/index.html from a live pipeline run
├── demo/                         # template.html (hand-written) and index.html (generated), see §11
└── tests/                        # 66 tests, all passing (see §9)
```

Everything under `src/tape` is a plain Python package (no install step needed beyond the venv) — scripts add `src/` to `sys.path` themselves.

---

## 3. Phase 1 — TAPE Baseline (reproduction)

**Goal:** get the actual TAPE pipeline working end to end, so every later extension has something honest to be compared against.

**Benchmark:** we implemented **Sokoban** first (of the four TAPE benchmarks — Sokoban, ALFWorld, MuSiQue, GSM8K-Hard) because it is small, self-contained, fully deterministic, and requires no external dataset or environment package. This was a scope decision to get a working, testable pipeline before spending time on heavier benchmark integrations (ALFWorld needs a simulator install, MuSiQue/GSM8K-Hard need dataset downloads) — **the other three benchmarks are not yet implemented.**

**What was built** (`src/tape/envs/sokoban.py`, `llm.py`, `graph.py`, `solver.py`, `executor.py`, `metrics.py`):

- **Environment** — a minimal grid Sokoban: walls, boxes, goals, player. `step(state, action)` is the single source of truth for legality (returns unchanged state + `moved=False` for an illegal move, so illegal actions surface as data rather than exceptions).
- **Candidate plan generation** — an `LLMClient` interface with two backends:
  - `MockLLMClient`: no API key needed. Generates one BFS-optimal solving sequence plus several noisy, goal-biased-random-walk sequences, so the graph has a realistic mix of one good plan buried among imperfect/dead-ending ones — used for all automated tests and offline development.
  - `GeminiClient`: calls the Gemini REST API directly via `urllib` (deliberately **not** the `google-generativeai` SDK, which pulls in a multi-hundred-MB grpc/protobuf dependency chain for what is a single HTTP POST — this also matters practically, since we hit a disk-space wall installing it during setup).
- **Plan graph construction** (`build_plan_graph`) — simulates every candidate action-by-action from the current real state; identical resulting states across different candidates collapse onto the same graph node (the "merging" TAPE describes). A candidate step that turns out illegal simply stops being extended (dead-ends in the graph) — there is deliberately no separate validator at this stage; that is exactly the baseline's "trust the LLM, discover problems structurally" behaviour that Phase 2 improves on.
- **Solver-based path selection** (`solver.py`) — phrased as a min-cost single-unit flow problem and solved with **OR-Tools CP-SAT**: one unit of flow from the start node to a virtual sink wired from every goal node, minimizing total edge cost. This is a real ILP-style solver call, not a shortest-path shortcut.
- **Constrained execution + replanning** (`executor.py`) — executes the solved path action by action; after each action, compares the real resulting state to what the graph predicted. A mismatch aborts the current plan and triggers a fresh planning round from the real state (capped at `max_replans`). Mismatches are not hypothetical here: the executor supports an injectable random "slip" probability that forces a real action to silently fail, which is what actually exercises the replanning logic in tests and CLI runs.
- **Metrics** (`metrics.py`) — aggregates success rate, average replans, invalid-transition rate, planning time, and execution cost across a batch of episodes — these are exactly the columns Phase 6's evaluation will compare across baseline vs. extensions.

**Verified behaviour:** on the `simple` level with zero slip probability, 30/30 episodes succeed with the optimal 9-action solution (hand-verified). With `slip=0.2`, replanning correctly engages (~1.9 replans/episode average) and the success rate stays high (~97%) rather than collapsing, showing the replanning loop actually recovers from mismatches rather than just detecting them.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 30 --slip 0.0
python experiments/run_baseline.py --level simple --episodes 30 --slip 0.2
```

---

## 4. Phase 2 — Adaptive Graph Validation

**The gap this targets:** TAPE's own paper identifies that plan-graph accuracy depends entirely on the LM correctly structuring states — a transition can be *physically legal* per the environment and still be a planning error the baseline has no way to see until much later (or never, if the solver just quietly fails to find a path).

**Concrete example in Sokoban:** pushing a box into a corner that is not a goal cell is a completely legal move — `level.step()` reports `moved=True` — but it is *unrecoverable*: no future sequence of moves can ever get that box out of the corner. The Phase 1 baseline has no way to distinguish this from a perfectly fine push.

**What was built** (`src/tape/validator.py`):

- A `GraphValidator` protocol: `validate(level, from_state, action, to_state) -> ValidationResult(accept, confidence, reason)`.
- `CornerDeadlockValidator`: rejects outright any transition that leaves a non-goal box wedged against two perpendicular walls (a corner). A box merely resting against **one** wall (not a corner) is not rejected — it's accepted but flagged **uncertain**, with confidence 0.5 rather than 1.0, per TAPE's own language ("uncertain ones receive lower confidence" rather than a hard binary).
- `build_validated_plan_graph()` in `graph.py`: identical to the Phase 1 graph builder, except every physically-legal step is also passed through the validator before being added as an edge. A rejected step dead-ends that candidate right there, instead of silently entering the graph. An accepted-but-uncertain step is still added, but its edge cost is inflated so the confidence penalty makes it more expensive than a fully-trusted step — meaning the **same CP-SAT solver from Phase 1**, unmodified, naturally prefers fully-trusted paths over uncertain ones. No solver changes were needed for this. (At the time Phase 2 was built, that inflation was a simple `cost = round(1/confidence)`; Phase 4, §6 below, later replaced that formula with a richer multi-factor score, but the underlying mechanism — lower confidence means higher cost — is unchanged.)
- Wired into `run_episode()` / `run_baseline.py` as an optional `validator=` parameter / `--validator corner-deadlock` CLI flag, so **baseline vs. validated is a flip of one flag** — this is exactly the controlled ablation the evaluation plan (Phase 6) needs.

**Verified behaviour:** `tests/test_validator.py` constructs an exact corner-deadlock scenario (`#####` / `#   #` / `#$  #` / `#@ .#` / `#####`, pushing the box up wedges it at (1,1), a corner off the goal at (3,3)) and confirms:
- The Phase 1 baseline graph accepts this push as a normal edge (`invalid_transitions == 0`).
- The Phase 2 validator rejects it (`validator_rejections == 1`, the edge never enters the graph).
- Pushing a box directly onto a goal is never mistakenly flagged as a deadlock.
- A box against one wall (not a corner) is accepted with confidence 0.5, which produces a higher-cost edge.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 30 --slip 0.1 --validator corner-deadlock
```

### 4.1 Stress test: does the validator actually matter in aggregate?

On the normal goal-biased `MockLLMClient`, corner deadlocks basically never happen by chance (its candidates are always steered toward reducing distance to the goal), so running the CLI above shows identical metrics with the validator on or off. Rather than leave that as an open question, we built a deliberate stress test (`experiments/stress_test.py`, automated as `tests/test_stress.py`):

- **`AdversarialMockLLMClient`** — a new, much dumber candidate generator: pure uniform-random legal moves, with **no guaranteed correct plan mixed in** (unlike `MockLLMClient`, which always includes one BFS-optimal candidate as a safety net). This is an honest stress test, not a claim about how a real LLM behaves — it exists purely to make the failure condition the validator is supposed to catch actually happen often enough to measure.
- Ran 30 trials × 150 adversarial candidates each on the two-box level (`LEVEL_MULTI`), comparing the Phase 1 baseline graph against the Phase 2 validated graph.
- **Result:**

  | Metric | Value |
  |---|---|
  | Total transitions attempted | 54,000 |
  | Baseline invalid-transition rate | **0.00%** (corner deadlocks are physically legal moves — invisible to it by construction) |
  | Validator rejections | **200** (0.37% of attempted transitions) |
  | Independently verified as true dead ends | **200 / 200** (zero false positives) |

  The "independently verified" number matters most: each of the 200 rejected transitions was checked with a plain breadth-first search (nothing to do with the validator's own corner-detection rule) confirming no sequence of moves from that state can ever reach the goal. So this isn't the validator grading its own homework — it's an outside check confirming every rejection is a genuine planning error the baseline's own metric was structurally blind to.
- **The real finding:** it's not that the validator changes whether episodes succeed (the guaranteed-optimal candidate in normal `MockLLMClient` runs makes that metric insensitive to this by construction — see §4 above). It's that **the baseline's own "invalid transition" metric silently undercounts real planning errors**, because it only catches syntactic illegality (walls, double boxes), not semantic/domain violations (corners). The validator makes a previously invisible category of error visible and preventable.

Reproduce it: `python experiments/stress_test.py`

---

## 5. Phase 3 — Self-Improving Graph

**The gap this targets:** TAPE's baseline replans on a mismatch but throws the information away afterward — the same LLM mistake can recur in a later episode with no memory of it having failed before.

**What was built** (`src/tape/experience.py`):

- `ExperienceStore`: records, for every executed `(level, state, action)` transition, whether the real environment's result **matched** what the plan graph predicted (a success signal) or **mismatched** (a failure signal) — this is literally TAPE's own mismatch/replanning check, just persisted instead of discarded.
- Confidence from history is Laplace-smoothed (`(successes + 1) / (total + 2)`) so a single early failure doesn't permanently zero out a transition, and a transition with no history at all defers entirely to the validator/environment (confidence 1.0).
- Storage is **sqlite3 (Python's standard library)**, not the PostgreSQL mentioned in the original tech list — a handful of `(level, state, action) → counts` rows doesn't justify running a database server for this project, and it keeps everything runnable with zero extra infrastructure. (If experience data volume or query complexity ever outgrows this, swapping in Postgres is a small, isolated change — `ExperienceStore`'s interface doesn't leak sqlite specifics.)
- `build_validated_plan_graph()` was extended to accept an optional `experience` argument: when given, it **multiplies** the validator's confidence by the experience-store confidence for that exact transition, before computing edge cost. So a transition that has repeatedly mismatched execution in earlier episodes becomes progressively less trusted in later ones — even if the validator has no objection to it at all.
- Wired through `run_episode()` / `--experience` on the CLI (stacks with `--validator`; the two extensions are independent and composable, which also matters for Phase 6's ablations).

**Verified behaviour:** `tests/test_experience.py` confirms confidence starts at 1.0 with no history, that five recorded failures push confidence below 0.5 while five recorded successes push it above 0.5, and — most importantly — an actual multi-episode `run_episode()` loop (with forced mismatches via `slip_prob=1.0`) correctly accumulates failure history in the store that persists and is queryable across those episodes.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 25 --slip 0.15 --validator corner-deadlock --experience --seed 5
```

---

## 6. Phase 4 — Dynamic Reachability/Utility Score

**The gap this targets:** every edge in the validated graph up to this point cost either a flat 1 (baseline) or `1/confidence` (Phase 2/3) — a purely "how much do we trust this transition" number. TAPE's own plan describes something richer: a per-state score built from goal proximity, accumulated cost, remaining budget, and confidence together, not confidence alone. A transition can be perfectly legal and fully trusted and still be a bad idea, for example if it walks a box away from every goal for no reason.

**What was built** (`src/tape/scoring.py`):

- `goal_distance(level, state)`: sum, over every box not already on a goal, of its Manhattan distance to the nearest goal.
- `score_transition(level, from_state, to_state, step_index, max_depth, confidence, weights)`: computes a `TransitionScore` combining four factors into one edge cost:
  - **regression** — how much this step increased goal distance (a move that makes no progress or gets closer costs nothing extra here; only genuine backward movement is penalized).
  - **confidence penalty** — same confidence signal from Phase 2/3, scaled by `(1 - confidence)`.
  - **budget pressure** — grows as `(step_index / max_depth)²`, so a transition late in an already-long candidate costs more than the same transition taken early, discouraging the solver from preferring paths that eat deep into the planning budget.
  - a base step cost of 1, same as the baseline.
- The four factors are summed with configurable weights (`ScoreWeights`) and scaled by 10 before rounding, since OR-Tools CP-SAT requires integer coefficients and a flat round-to-nearest-integer would collapse every fractional difference to the same cost.
- `build_validated_plan_graph()` now calls `score_transition()` for every accepted edge instead of the old `max(1, round(1/confidence))` formula — the same CP-SAT solver from Phase 1, completely unmodified, now minimizes a genuinely multi-factor cost instead of a confidence-only one.

**Verified behaviour:** `tests/test_scoring.py` proves each factor moves cost in the expected direction in isolation (a regressing transition costs more than a progressing one at equal confidence; lower confidence costs more at equal progress; a transition late in the step budget costs more than the identical one taken early) and that a real `build_validated_plan_graph()` run on the demo level's known candidates produces edges that all carry a valid non-negative `regression` value and a positive integer cost. 6 new tests.

**Honest note on the resulting numbers:** because of the ×10 integer scaling, solver costs under this formula are on a different, larger scale than Phases 1–3 (a full episode's cost can jump from single digits into the hundreds). That's expected and not evidence of a problem — it doesn't change which path the solver picks in the demo (the same optimal path is still chosen), only the number attached to trusting it. The demo (`demo/index.html`) explains this directly rather than leaving the jump unexplained.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 25 --validator corner-deadlock --experience
```
(scoring is active automatically whenever `--validator` is set; there's no separate flag for it, since it replaces the internal cost formula of the same validated-graph path)

---

## 7. Phase 5 — Adaptive Path Selection

**The gap this targets:** TAPE's second identified limitation. Every path-selection call up to this point, in the baseline and in every extension, goes through CP-SAT: a real ILP-style solver, formulated in `solver.py` as a min-cost flow problem. That's the right tool when a task has genuinely interacting hard constraints, but it's formal-optimization machinery brought to bear on graphs where a plain shortest-path search would find the identical answer. TAPE's own gap analysis names this directly: the framework depends on one pre-specified solver for every task, with no way to adapt.

**What was built** (`src/tape/path_selector.py`):

- `astar_select_path(level, plan_graph)`: a standard A* search over the same plan graph CP-SAT already solves. The g-cost is the sum of Phase 4's edge costs (identical units, so the two methods are directly comparable); the heuristic is `goal_distance` (Phase 4's own Manhattan-distance-to-nearest-goal function) scaled to match. It returns the same `PlanSolution` type `select_path()` does, so callers don't need to know which method actually ran.
- `decide_method(level, plan_graph)`: the actual adaptive rule, generalized (see §8 below) to call `level.complexity(state)` rather than reading Sokoban's box count directly. A puzzle with one independently-movable piece is a pure shortest-path problem, nothing needs to be jointly coordinated, so A* is enough. More than one means those pieces' moves have to be planned together (progress on one can conflict with another), which is exactly the kind of interacting constraint CP-SAT exists for. The rule is one line: `complexity(state) > 1` routes to CP-SAT, otherwise A*.
- `select_path_adaptive(level, plan_graph)`: calls `decide_method` and dispatches, returning `(solution, method_used)` so the caller (and the metrics) can see which one actually ran.
- Wired into `run_episode()` via a `path_selection` argument (`"cp_sat"` default, `"astar"`, or `"adaptive"`) and `--path-selection` on the CLI. `EpisodeResult.path_selection_methods` records which method every planning round in the episode actually used.

**Verified behaviour:** `tests/test_path_selector.py` confirms A* finds a path on a trivial one-step level, that it produces the *same cost* as CP-SAT on a richer multi-candidate graph (not just "a" path, the same optimal one), that it correctly returns `None` when the graph has no path to a goal, and that `decide_method` routes every single-box level tested to A* and the two-box level to CP-SAT. `tests/test_pipeline.py` adds three end-to-end checks: a full episode solved with `path_selection="astar"`, one with `"adaptive"` on a single-box level confirming every round used A*, and one with `"adaptive"` on the two-box level confirming every round used CP-SAT. 10 new tests (7 + 3).

**Does it actually help, or just match?** Measured directly via the CLI on 20 episodes of the `simple` level: CP-SAT averages 0.0201s of planning time per episode; A* averages 0.0027s, roughly 7x faster, for the identical execution cost (9.0) and 100% success rate in both cases. `adaptive` correctly selects A* on `simple` (single box) and CP-SAT on `multi` (two boxes), succeeding both times. This is the concrete evidence for Phase 5's claim: adaptive selection gets the speed benefit where the task is simple enough to allow it, without giving up the solver's guarantees where the task actually needs them.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 20 --path-selection cp_sat
python experiments/run_baseline.py --level simple --episodes 20 --path-selection astar
python experiments/run_baseline.py --level multi --episodes 20 --candidates 20 --max-depth 14 --path-selection adaptive
```

---

## 8. Beyond Sokoban: two more benchmarks, not just box-pushing

Phases 1–5 above were all built and verified against Sokoban. The pipeline diagram (`docs/pipeline_diagram.html`) claimed everything left of the validated-optimal-path box is benchmark-agnostic — this section is where that claim stopped being architecture and started being three real benchmarks passing the same tests.

### 8.0 Making the pipeline actually generic

Before any new benchmark could plug in, several pipeline modules had to stop assuming a Sokoban-shaped state (an object with `.player`/`.boxes` fields). `src/tape/env_base.py` defines the interface every environment now implements:

- `step(state, action) -> (next_state, legal)`, `is_goal(state)`, `render(state)`, `ACTIONS` — already generic (Phases 1–3 never touched box/goal internals directly).
- `heuristic(state) -> int` — a "distance to solved" estimate, 0 at the goal. Sokoban's is the Manhattan-distance calc that used to live directly in `scoring.py`; it moved into `SokobanLevel.heuristic()`, and `score_transition()` now calls `level.heuristic(...)` instead of a Sokoban-only free function.
- `complexity(state) -> int` — how many independently-movable pieces this puzzle instance has. Sokoban: box count (unchanged behaviour — `decide_method` used to read `state.boxes` directly; now it calls `level.complexity(state) > 1`, same threshold, same result for every existing Sokoban test).

`experience.py`'s state-keying also assumed `.player`/`.boxes`; it now uses `repr(state)`, which works for any hashable state (verified that two frozensets with identical elements but different construction order produce identical reprs, so this doesn't silently fragment history).

**A real bug this generalization surfaced, not introduced by it:** `MockLLMClient`'s "guaranteed good candidate" (a plain BFS ignoring domain rules) and its goal-biased noisy candidates had no way to know about a validator's rules. This never mattered for Sokoban, because corner-deadlock states are *structural* dead ends — a plain shortest-path search naturally never routes through them, since they can't reach the goal either way. River crossing broke that assumption (see §8.1): its unsafe states are *not* dead ends and often look heuristically attractive, so the naive "optimal" candidate cheerfully cheated through a fatal configuration and found a 9-move "solution" that isn't a real solution to the actual puzzle. Fixed by giving `_bfs_plan()` and `MockLLMClient` an optional `validator` to consult (default `None`, so Sokoban's behaviour and all 40 prior tests were unaffected) — modeling an LLM that has been told a rule, as distinct from `AdversarialMockLLMClient`, which never is.

All 40 prior Sokoban tests passed unchanged after this refactor before any new benchmark was added, confirming it was genuinely invisible to existing behaviour rather than a rewrite in disguise.

### 8.1 River crossing (missionaries and cannibals)

**Why this one:** a classic AI-planning textbook problem, and a mechanic with nothing in common with Sokoban — no grid, no walls, the entire state is two headcounts and which bank the boat is on. It's also a second, cleaner example of Phase 2's validator pattern: `RiverCrossingLevel.step()` allows any physically possible boat trip and deliberately does **not** enforce the safety rule (cannibals must never outnumber missionaries on either bank while any missionaries are present) — exactly like Sokoban's corner deadlock, a physically legal move that is still a fatal, unrecoverable domain violation. `RiverSafetyValidator` (`src/tape/envs/river_crossing_validator.py`) is the Phase 2 analog of `CornerDeadlockValidator` for this domain.

`complexity(state)` returns `1`: unlike Sokoban's independently-pushable boxes, people here never move independently of each other — every crossing is a single sequential decision about the one boat — so this always routes to A*, never CP-SAT.

**Verified against an independent ground truth, not just internal consistency:** the textbook answer for 3 missionary/cannibal pairs with a 2-seat boat is 11 one-way trips. A validator-aware `_bfs_plan()` finds exactly 11. (The validator-*unaware* physical-only BFS finds a 9-move "solution" that passes through a fatal state — see §8.0 — which is exactly why the fix mattered.)

**The validator's necessity is immediate here, unlike Sokoban.** Sokoban needed a dedicated adversarial stress test (§4.1) before the validator's aggregate effect became visible, because its guaranteed-good candidate already avoided the failure case by construction. River crossing has no such luck: an `AdversarialMockLLMClient` (pure random legal moves, no knowledge of the safety rule) run for 20 episodes with the validator active still succeeds **0/20** — this puzzle is essentially unsolvable by an agent that hasn't been told the rule, which is the whole point of Phase 2 existing.

6 tests (`tests/test_river_crossing.py`).

**Run it:**
```bash
python experiments/run_river_crossing.py --episodes 20
python experiments/run_river_crossing.py --llm adversarial --episodes 20 --candidates 50
```

### 8.2 Rush Hour

**Why this one:** a very well-known commercial sliding-block puzzle (ThinkFun, 1996) and a third, structurally distinct mechanic — vehicles occupy multiple cells with a fixed orientation and length, not a single position like a Sokoban box or a headcount like river crossing's people. State is a frozenset of `(vehicle_id, anchor_row, anchor_col)`; each vehicle's own orientation and length are fixed level metadata parsed once from the board, not part of the state that changes. `step()` enforces board bounds and vehicle-vehicle collision (every cell a vehicle would newly occupy must be empty or already its own).

`complexity(state)` returns the vehicle count. Getting the target vehicle out almost always means moving one or more blockers out of its way, in the right order — independently-movable pieces whose routes can conflict, the same shape of problem as Sokoban's multiple boxes — so it correctly routes to CP-SAT via the *same* adaptive rule already used for the other two benchmarks, no special-casing needed.

**Verified against a hand-worked solution:** the demo board has a vertical blocker (`B`) directly in the target's exit row, and an uninvolved decoy vehicle (`A`) that never needs to move (same as real Rush Hour boards usually have pieces that are irrelevant to the solution). BFS confirms the optimal solution is exactly 6 actions — move `B` down twice to clear the row, then slide the target right four times — matching a hand-traced solution, not just "the code agrees with itself."

8 tests (`tests/test_rush_hour.py`), including two that confirm level construction actually rejects malformed boards (a disconnected same-letter run; a vertical target vehicle).

#### 8.2.1 `RowGridlockValidator`

**Why this needed more care than Sokoban's corner check:** gridlock in Rush Hour is *not* locally decidable in general. A vehicle with zero legal moves right now can still be freed several moves later by an unrelated vehicle elsewhere on the board moving out of the way first — unlike Sokoban, where walls never move, so "boxed by two walls" really is permanent. A naive "is anything stuck" rule would be unsound: Rush Hour puzzles routinely *start* with the target vehicle blocked (that's the puzzle), so such a rule would reject the opening move of nearly every solvable board.

**What was actually built** (`src/tape/envs/rush_hour_validator.py`), two honestly-different tiers instead of one guess:

- **Hard reject, provably sound:** a *sealed row* — every cell in the target's row is occupied, and every vehicle contributing to that row is horizontal (none vertical). This is a genuine certificate: sliding needs an empty cell in the same row, none exists, and none ever can appear, because a vertical vehicle is the only kind of neighbor that could vacate a row-cell by leaving the row entirely. If the row is packed with only horizontal vehicles, nothing in it can ever move again, period.
- **Soft "uncertain" (confidence 0.5, not a reject):** the target is blocked, and that specific blocking vehicle currently has zero legal moves of its own. This is a real, worth-distrusting signal — but explicitly *not* proof of a permanent deadlock, since a third vehicle might still rescue the blocker later. Kept as a confidence penalty, never a hard reject, exactly matching how Sokoban's own "box against one wall" case is treated.

**Verified rigorously, not just spot-checked:** replaying the known 6-move optimal solution produces zero rejections and zero confidence penalties end to end (`test_optimal_solution_never_gets_rejected_or_downweighted`) — including at the very first state, where the target genuinely has no legal move (blocked by `B`) but `B` itself can still move, so neither tier fires. A constructed sealed-row board (`XXCCCC` exactly filling a 6-wide row) triggers the hard reject; the *same* occupancy pattern with one vehicle made vertical instead of horizontal does **not** trigger it (confirming the rule keys on orientation, not just "no gaps"), and correctly falls through to the soft "uncertain" tier instead, since the blocked target's blocker also has no move in that specific constructed case.

6 tests (`tests/test_rush_hour_validator.py`). `--validator row-gridlock` on the CLI.

**Run it:**
```bash
python experiments/run_rush_hour.py --episodes 20
python experiments/run_rush_hour.py --episodes 20 --validator row-gridlock
```

### 8.3 What "any benchmark" means now, honestly

Three benchmarks (Sokoban, river crossing, Rush Hour) now share Phases 1–5 unchanged, which is real evidence the architecture generalizes — not just the claim the pipeline diagram made before this work. What hasn't changed: TAPE's own four benchmarks (Sokoban, ALFWorld, MuSiQue, GSM8K-Hard) are still three-quarters unimplemented — river crossing and Rush Hour are *additional* benchmarks proving generality, not substitutes for the ones the original project scope named. If cross-benchmark generalization against TAPE's own suite specifically is expected for the final deliverable, ALFWorld/MuSiQue/GSM8K-Hard are still the gap to close, not river crossing/Rush Hour.

---

## 9. Test coverage (66 tests, all passing)

```
tests/test_sokoban.py       4  — environment legality: pushes, walls, box-into-wall, rendering
tests/test_graph.py         2  — candidate merging onto shared nodes; illegal steps become dead ends
tests/test_solver.py        3  — shortest path found, cheaper of two candidates preferred, infeasible → None
tests/test_pipeline.py      7  — end-to-end: mock LLM solves trivial/simple/two-box levels, slips trigger replanning and still recover, astar/adaptive path selection solve correctly
tests/test_validator.py     4  — corner-deadlock rejected, goal-push never falsely flagged, wall-hug is "uncertain" not rejected, baseline accepts what the validator rejects
tests/test_experience.py    3  — no-history = full trust, failures lower confidence below successes, cross-episode persistence actually happens
tests/test_stress.py        1  — at scale (not just one example): adversarial candidates trigger real deadlocks, and every rejection is independently BFS-verified as a true dead end
tests/test_scoring.py       6  — regression, confidence, and budget pressure each move cost in the right direction in isolation; a real graph build produces valid scores on every edge
tests/test_hard_level.py     3  — the tougher Sokoban level: BFS-verified 29-move optimum, full pipeline solves it (cp_sat on three boxes, zero false validator rejections), recovers from random slips
tests/test_path_selector.py 7  — A* finds the same-cost optimal path CP-SAT does, returns None when infeasible, decide_method routes single-box to A* and multi-box to CP-SAT, adaptive selection solves both correctly
tests/test_river_crossing.py 6  — matches the textbook 11-move answer, step() doesn't self-enforce safety, validator rejects/accepts correctly, complexity is always 1, full pipeline solves it, and fails without an aware LLM
tests/test_rush_hour.py      8  — 6-move hand-verified optimal solution, target blocked by a vehicle ahead, can't drive off the board, complexity is the vehicle count, full pipeline solves it via CP-SAT, malformed boards rejected
tests/test_export_demo.py     3  — for each game the demo data is sound: the good plan solves, the checker flags the bad plan, replanning after a slip produces a path
tests/test_boxoban.py         3  — level blocks parse, the real file has 1000 ten-by-ten four-box levels, the search proposer solves a real level and pruning never expands more nodes
tests/test_rush_hour_validator.py 6  — zero false rejects/downweights along the real solution, pipeline still solves with it active, hard-rejects a genuinely sealed row, does NOT reject the same pattern with a vertical vehicle instead, flags (not rejects) a suspicious-but-unproven double-lock, doesn't flag a blocker that can still move
```

Run everything:
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/ -q
```

---

### 9.1 The hard level (`--level hard`)

`LEVEL_HARD` is a 9x7 room with an internal wall and three boxes. Its optimal solution is 29 moves (verified by BFS), versus 9 for `simple` and 11 for `multi`. The full pipeline (validator, experience, scoring, adaptive selection) solves it in exactly 29 actions, routes it to CP-SAT because it has three boxes, and the validator never falsely rejects the optimal path. With a 5% random slip it still succeeds after replanning.

**Honest limitation:** this is not hard for the *pipeline*, because the normal mock LLM always plants one BFS-optimal candidate. The real difficulty shows against the random-candidate generator (`AdversarialMockLLMClient`, 200 candidates, 20 episodes each): `simple` succeeds 4/20, `multi` 0/20, `hard` 0/20. That gap is what a real LLM's candidate quality will be measured against in Phase 6.

```bash
python experiments/run_baseline.py --level hard --episodes 5 --candidates 8 --max-depth 32 --validator corner-deadlock --experience --path-selection adaptive
```

---

## 10. Setup notes for teammates

- Needs Python 3.11+, a venv (`python -m venv .venv`), then `pip install -r requirements.txt`.
- `GEMINI_API_KEY` (copy `.env.example` to `.env` and fill in) is only needed for `--llm gemini`; all tests and the default `--llm mock` run with zero API keys or network access.
- We hit a real disk-space wall during setup (the `google-generativeai` SDK alone pulled the free space on one machine from ~3GB to negative) — this is why Gemini is called directly over HTTP instead of through the SDK. If you `pip install google-generativeai` anyway for some other reason, budget several hundred MB.

---

## 11. The live demo (for the mid-semester presentation)

`demo/index.html` is a guided walkthrough called **Plan Check**, built so the guide can go through the project on their own. A route map on the left shows where you are: Start, Pick a game, then five pipeline steps, then Results. Arrow keys and the Back/Next buttons move between them.

- **Pick a game:** Sokoban (one box), River Crossing, Rush Hour. Each has its own board.
- **Propose:** two plans from the planner, Plan A (good) and Plan B (has a bad move). Play or step through each on the board.
- **Merge:** the plans drawn as one graph. States both plans reach are shared nodes.
- **Check:** switch the rule checker Off and On for Plan B. Off, the plan runs and nothing warns you. On, the bad move is rejected (Sokoban corner, River Crossing outnumbered) or kept with low trust (Rush Hour, confidence 0.50). The graph is recolored by verdict.
- **Choose:** A* and CP-SAT timed on the graph, which one the adaptive rule picked and why, and the cheapest path played on the board.
- **Run:** a move slips, the world does not change, the system replans from the real state, and the slipped move's trust drops from 1.00 to 0.33 in the experience store.
- **Results:** four charts (safety, speed, real levels on Boxoban, memory) and a short list of what the data does not show. The numbers are read from `results/ablation.csv` and `results/experience_test.md`.

**It is generated, not hand-authored.** `demo/template.html` is the hand-written page. `python experiments/export_demo.py` runs the real pipeline for all three games (finds a bad move by search, builds the graph, times both solvers, forces a slip and replans) and writes `demo/index.html`. Rerun it whenever the pipeline or the results files change. Edit `demo/template.html`, never `index.html`. `tests/test_export_demo.py` checks that every game's data is sound.

**Opening it:** double-click `demo/index.html`, or serve it with `.claude/launch.json` (`python -m http.server 8000 --directory demo`) and open `http://localhost:8000`. Deep links work, for example `#river-check`. The page uses Google Fonts when online and falls back to system fonts offline. It follows the system light or dark theme. The template declares `<meta charset="utf-8">` because Python's HTTP server sends no charset and non-ASCII text would otherwise turn into garbage.

---

## 12. Is this reinforcement learning?

No. This project is closer to classical AI planning (graph search plus constraint solving) with an LLM bolted on for candidate generation. Worth stating explicitly, since Phase 3's experience mechanism can look RL-ish at a glance if the teacher asks — it isn't, and it's worth being precise about why not, and about what actually replaces each piece an RL system would have.

**Where it clearly isn't RL:**
- No reward signal is being maximized. There is no objective function the system optimizes across episodes.
- Nothing is learned in the parametric sense — the LLM's weights never update, and there is no policy network or value function being trained.
- Path selection (A*/CP-SAT) is classical deterministic search/optimization, not a learned policy.
- There is no exploration-exploitation tradeoff being managed, which is central to almost every RL formulation.

**What replaces each of those four pillars here:**

| Instead of... | We do... |
|---|---|
| Maximizing a reward signal over episodes | A fixed, hand-designed cost function (`score_transition()` in `scoring.py`: regression + confidence penalty + budget penalty) computed once per planning round and minimized in that one shot. No accumulation across episodes, no discounting, no return being optimized — each round is a fresh minimization problem. |
| Learning parameters from experience | Direct frequency counting. `ExperienceStore` (`experience.py`) keeps a per-`(state, action)` success/failure tally in sqlite and computes confidence as `(successes + 1) / (total + 2)` — Laplace-smoothed lookup, not gradient descent. Nothing generalizes to unseen states; it is memorization, not function approximation. |
| A learned policy choosing actions | Classical deterministic search over an explicitly built graph. `astar_select_path()` and `select_path()` (CP-SAT) both search the *same* plan graph to optimality given its current edge costs, recomputed fresh every round. Swapping the graph's costs doesn't require "relearning" anything — the search just resolves. |
| Managing exploration vs. exploitation | The LLM samples multiple candidate plans per round (`generate_candidate_plans(..., n)` in `llm.py`) — that's where behavioral diversity comes from, not a bandit-style epsilon-greedy or UCB strategy. When execution diverges from the plan, replanning is unconditional and deterministic (the mismatch check in `executor.py`), not a policy deciding whether to explore further. |

**The one RL-adjacent piece, and why it still isn't RL:** Phase 3's `ExperienceStore` records per-transition success/failure counts and uses that to bias future planning — a loose cousin of how tabular Q-learning updates value estimates from past outcomes. But it's exact-match memorization of specific `(state, action)` pairs with frequency counting, not a value function that generalizes across states, and there is no reward being propagated backward through a trajectory (no Bellman-style credit assignment).

**The honest framing for a report or in front of the teacher:** this is planning-based, not learning-based. An LLM proposes candidate plans, those become a graph, a validator and a hand-written scoring function judge the graph, and a classical solver (A* or CP-SAT) finds the optimal path through it — the same intellectual lineage as A* and constraint programming, with the LLM replacing hand-written plan generation, not a trained agent replacing a hand-written policy.

---

## 13. What's left

Done since the last version of this section: the Phase 6 core (ablation, state-dependent memory test, ScoreWeights tuning, proposer-quality sweep) and the Boxoban benchmark. Remaining, in rough order of value:

- **Write the paper.** The claim the data supports is narrow (Sec 14.3): the layer gives safety and fewer wasted replans, and the checker makes a search proposer solve more real levels (Sec 16). It does not raise the goal-reach rate when the proposer is already decent, and merging plans did not shorten paths.
- **A learned, non-LLM proposer** (imitation or RL policy) for more realistic proposer errors than our synthetic ones. Ask the guide whether learned models are allowed.
- **More Boxoban:** other files in each set, and a second checker rule beyond dead corners (for example frozen boxes) to see whether the gain grows.
- **Scope gap to state plainly:** TAPE's ALFWorld, MuSiQue and GSM8K-Hard need an LLM and are dropped by the guide's decision. River Crossing, Rush Hour and Boxoban show the architecture generalizes; they are not substitutes for TAPE's own suite, so numbers are not comparable to the paper.
- **Known weaknesses:** proposers are synthetic, the experience store only helps when candidates contain a detour, and `ScoreWeights` defaults were kept because tuning found nothing better (a null result, not a proof they are optimal).

---

## 14. Phase 6: ablation results (first pass)

`python experiments/run_ablation.py --episodes 30` runs 5 configs (baseline, +validator, +validator+experience, +adaptive, full) x 6 benchmarks x 2 LLM conditions (goal-biased mock, adversarial random) at slip 0.15. Full tables with 95% Wilson intervals: `results/ablation.md` / `.csv`. It is 30 episodes per cell, so intervals are wide (a 100% cell means only "at least 89%").

**Metric note:** we report *safe success* (goal reached AND no executed move rejected by an independent domain auditor, `run_episode(auditor=...)`) next to raw success. Without it, River Crossing's baseline looks perfect (100%) while walking through unsafe states, because that environment does not enforce safety itself.

**What the data supports:**
1. **Validators matter where the environment permits illegal-but-legal-looking moves.** River Crossing goal-biased: baseline 0% safe success, +validator 100% (raw success is 100% in both). This is the clearest result.
2. **Adaptive solver cuts planning time at identical quality.** Same success and same action count, but planning drops: trivial 16.9 -> 0.2 ms, simple 52 -> 7.6 ms, river 62 -> 3.6 ms (baseline vs +adaptive). On the hard level the gain is small (4.3 s vs 3.8 s) because time is dominated by candidate generation.
3. **Sokoban hard is the real difficulty:** about 53% success for every config. None of our extensions changes it.

**What the data does NOT support (say this if asked):**
- **The experience store (Phase 3) shows no measurable benefit under uniform-random slip.** Differences (e.g. multi 97% vs 100%) are within noise, because there is no state-dependent failure pattern to learn. The follow-up test in Sec 14.1 uses state-dependent slips.
- **Under the adversarial LLM the validator prunes bad transitions but cannot rescue a plan**: River Crossing 0% safe success in every config because no candidate is safe. Validators filter, they do not plan.
- All results use mock LLMs, not a real model. Real-LLM runs (Gemini client exists) are still to do.

**Still open for Phase 6:** see Sec 14.3 and 15 (the guide ruled out LLMs, so real-LLM runs and TAPE's LLM-native benchmarks are dropped).

### 14.1 Experience store under state-dependent slip

`python experiments/run_experience_test.py --runs 20 --episodes 30` (full table: `results/experience_test.md`). A fixed ~25% of (state, action) pairs are "hazards" that slip with probability 0.7; everything else never slips. Both arms use the validator and see identical hazards and seeds per run, so we report a paired difference (+experience minus validator only) with its standard error over 20 runs. Negative replans = the store helps. 30 candidates per planning round.

| benchmark | late-half replans diff (mean +/- SE) | success diff |
|---|---|---|
| sokoban-simple | -0.56 +/- 0.18 | +5.5% |
| river-crossing | -0.54 +/- 0.15 | +5.0% |
| rush-hour | -0.17 +/- 0.11 | +1.2% |
| sokoban-multi | +0.06 +/- 0.03 | -0.2% |

**Reading it honestly:**
- On simple Sokoban and River Crossing the store cuts replans by about 13% (roughly 3 standard errors) and raises success by about 5 points. That is real but modest.
- Rush Hour leans the same way but is not distinguishable from noise.
- Two-box Sokoban shows no help (slightly worse). Our reading, not tested: with more possible routes, the 30 mock candidates rarely contain a detour around a learned hazard, and the store can only re-weight edges that already exist in the plan graph.
- So Phase 3 is supported when failures are state-dependent and the candidates contain an alternative route, and not otherwise. This is still mock LLMs and synthetic hazards; a claim about real environments needs real failure data.

### 14.2 Tuning ScoreWeights

`python experiments/tune_weights.py` (table: `results/weight_tuning.md`). Grid of 80 weight triples (regression x confidence x budget penalty) in the state-dependent-slip setting with validator + experience store. Objective = replans + 3*(1 - success), averaged over the 4 benchmarks, lower is better. Fit on 8 train seeds; the top 3 and the defaults were then re-run on 16 unseen held-out seeds.

| config (regression, confidence, budget) | train objective | held-out objective | held-out diff vs default |
|---|---|---|---|
| (0, 16, 2) best on train | 3.906 | 4.298 | +0.122 +/- 0.111 (worse) |
| (3, 4, 0) | 3.961 | 4.098 | -0.078 +/- 0.123 (noise) |
| (0, 16, 4) | 3.967 | 4.287 | +0.112 +/- 0.167 (noise) |
| **default (1.5, 4, 2)** | 4.219 (rank 23/80) | 4.176 | 0 |

**Result: tuning found no defensible improvement.** The best train point did not hold up on held-out seeds, and none of the three candidates beats the defaults beyond one standard error. So we keep the defaults, and can now say they were checked rather than merely assumed: within this setting the cost is fairly flat over a wide range of weights (train objectives 3.9 to 4.2 for most of the grid; the worst corner is 5.1). Caveats: mock LLM, synthetic hazards, and only 8 train seeds, so the grid ranking itself is noisy. `run_episode` now accepts `weights=` so this can be re-run against real-LLM candidates.

### 14.3 Proposer-quality sweep (no LLM)

`python experiments/run_proposer_sweep.py [guided|corrupt]` (tables: `results/proposer_sweep_guided.md`, `results/proposer_sweep_corrupt.md`). `QualityProposer` in `llm.py` is an LLM-free candidate generator with a quality dial. Both arms run under the state-dependent slip of Sec 14.1: `baseline` (graph + CP-SAT) vs `full` (validator + experience store + adaptive solver). Metric: safe success, paired difference over 10 hazard seeds x 20 episodes.

- **guided mode** (mix of goal-biased and random walks, no planted optimal plan): floor effect. Sokoban-simple tops out at 17%, multi and hard at 0%, in both arms. This proposer is too weak for the pipeline to have anything to select from.
- **corrupt mode** (optimal plan, each step randomized with probability 1-quality, 30 candidates): the informative one. Highlights: Sokoban-simple 75-78% and Sokoban-multi 55-70% at quality 0.7 and above, hard 13-14% at 0.9-0.95.

**What corrupt mode shows, honestly:**
1. **The extra layers barely move success** on Sokoban and Rush Hour: almost every paired difference is within one or two standard errors of zero. The one nominal exception, Sokoban-multi at quality 0.7 (+5.0% +/- 2.0%), is one of about 25 comparisons and should not be presented as a finding.
2. **River Crossing is 0% safe success in both arms at every quality.** The proposer is validator-unaware, and its optimal plan is the unsafe 9-move one. The validator correctly rejects it (and cuts replans by roughly 2.7 to 3.4 per episode at quality 0.7 and above, because unsafe plans fail fast instead of being executed), but it cannot invent the safe 11-move plan. **A validator filters proposals; it does not create coverage.** Whether the pipeline succeeds depends on the proposer containing a valid plan.
3. Rush Hour leans positive at some qualities (+6.5% at 0.5, +5.0% at 0.95) but every difference is inside its noise band.

**Bottom line for the write-up:** with a heuristic proposer instead of an LLM, the contribution shows up as (a) safety, meaning no unsafe execution where the baseline silently executes unsafe plans, and (b) fewer wasted replans, not as a higher goal-reach rate. That is a narrower claim than "improves the planner", and it is what the data supports.

---

## 15. How the guide's no-LLM decision affected the project

Context: the original TAPE paper uses an LLM to propose candidate plans. Our guide decided we may not use LLMs. Consequences, stated plainly so nobody overclaims:

**Lost**
- **Direct comparison to TAPE.** Its benchmarks (ALFWorld, MuSiQue, GSM8K-Hard) are LLM-native, so they are dropped, and our numbers cannot be compared to the paper's.
- **The "LLM agent" framing** of the paper, and the venues that go with it.
- **Realism of the proposer.** Every candidate generator we have (`MockLLMClient`, `AdversarialMockLLMClient`, `QualityProposer`) is synthetic. Its failure modes are ones we designed, not ones a real planner shows. The unused `GeminiClient` is dead code.
- **Some benefit in the results.** Without an LLM's structured mistakes, the validator and experience store mostly show up in safety and replans, not success rate (Sec 14.3).

**Gained**
- **Fully reproducible experiments**: no API cost, no rate limits, no model drift; every result is re-runnable from a seed.
- **A controllable proposer.** The quality-sweep in Sec 14.3 is something an LLM API would not let us do cleanly.

**How we adapted**
- The claim moves from "improves LLM agents" to "a proposer-agnostic verification and selection layer".
- Evidence uses controlled proposers with a quality dial, paired statistics, held-out seeds, and negative results kept in.
- The class names `MockLLMClient`/`AdversarialMockLLMClient` are historical; they are simply proposers.

**Recommended next steps:** standard non-LLM benchmarks (Boxoban Sokoban levels, Rush Hour configuration database, IPC PDDL domains), classical baselines (plain A*, proposer alone), and a learned non-LLM proposer if the guide allows learned models.

---

## 16. Boxoban benchmark (standard external levels)

Boxoban is DeepMind's public Sokoban level set (`github.com/google-deepmind/boxoban-levels`). We use one file from each of its three difficulty sets (`unfiltered/valid/000.txt`, `medium/valid/000.txt`, `hard/000.txt`): 1000 levels each, 10x10, 4 boxes, stored in `data/boxoban/`. It uses the same character grammar as our own levels, so `tape.envs.boxoban.load_boxoban()` turns each block into a `SokobanLevel`. This is the first benchmark we did not write ourselves.

**Proposer (no LLM):** blind BFS cannot solve 4-box levels, so `tape.search_proposer.WeightedAStarProposer` runs weighted A* (weights 1, 2, 4, 8) under a per-search node budget and returns the plans that finish. Optionally the Phase 2 corner-deadlock checker prunes the search.

**Experiment:** `python experiments/run_boxoban.py --levels 1000 [--file data/boxoban/<set>.txt --out <name>.md]` (tables: `results/boxoban_unfiltered.md`, `results/boxoban.md` for medium, `results/boxoban_hard.md`). Use `--workers` to limit processes; 40 at once ran out of resources. All 1000 levels of each file were run (3000 levels, about 18 minutes). Solve rate is the share of levels where any of the four searches finds a plan within the node budget. No pruning vs with the checker:

| nodes per search | unfiltered | medium | hard |
|---|---|---|---|
| 2,000 | 57% vs 65% | 14% vs 23% | 6% vs 13% |
| 5,000 | 73% vs 82% | 29% vs 45% | 16% vs 29% |
| 10,000 | 84% vs 92% | 46% vs 65% | 27% vs 49% |
| 20,000 | 92% vs 96% | 61% vs 82% | 44% vs 70% |
| 30,000 | 95% vs 98% | 71% vs 88% | 54% vs 82% |

**Reading it:**
- The checker solves more levels at every budget in every set. The 95% intervals do not overlap in any of the 15 cells, and no-pruning never solved a level the checker missed (0 of 1000 in all 15 cells).
- The gain is largest where levels are harder: at 10,000 nodes it is 8 points on unfiltered, 19 on medium, 22 on hard. At 30,000 nodes it is 3, 17 and 28 points.
- It also expands fewer nodes per level at the full budget: 20% fewer on unfiltered, 25% on medium, 23% on hard.
- **This is not a new idea.** Pruning dead corners is standard in Sokoban solvers. What the result shows is that our Phase 2 checker works as that pruner on real external levels, not just on levels we wrote.
- **Merging did not shorten paths.** Across all three sets (unfiltered 981 solved, medium 882, hard 817) the merged path was shorter than the best single plan on 1 level in total (2 moves saved) and longer on 19, 9 and 5 levels. The pipeline picks the cheapest path by Phase 4 cost (progress, trust, budget), not by move count, so a longer path can win. We report this as measured.
- Limits: one file per set (`000.txt`; the `valid` split for unfiltered and medium), one checker rule, a search-based proposer we wrote. The `train` splits were not used, and other files in each set were not run. A first run on only the first 200 levels of each file gave the same picture, with wider intervals.
