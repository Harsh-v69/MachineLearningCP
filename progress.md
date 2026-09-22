# Progress: TAPE Extension — Adaptive Graph Validation & Solver Generalization

**Overall status: ~90% complete (Phases 1–5 of 6), well ahead of the mid-semester checkpoint, now verified across three benchmarks (Sokoban, river crossing, Rush Hour) instead of one.**

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
| 6 — Evaluation & Ablations | 10% | ⏳ Not started |

**Phases 1–5 sum to 90%, which is where the project currently stands.**

---

## 2. Repository layout

```
MachineLearningCP/
├── ML_CP.docx                 # original project proposal (source of truth for scope)
├── requirements.txt           # networkx, ortools, google-generativeai, pytest
├── .env.example                # GEMINI_API_KEY (copy to .env, fill in, do not commit)
├── src/tape/
│   ├── env_base.py              # the Environment protocol every benchmark implements (see §8.0)
│   ├── envs/
│   │   ├── sokoban.py                   # benchmark 1 (Phase 1)
│   │   ├── river_crossing.py            # benchmark 2 (§8.1): missionaries and cannibals
│   │   ├── river_crossing_validator.py  # its Phase 2 validator: RiverSafetyValidator
│   │   ├── rush_hour.py                 # benchmark 3 (§8.2): sliding-vehicle traffic jam
│   │   └── rush_hour_validator.py       # its Phase 2 validator: RowGridlockValidator (§8.2.1)
│   ├── llm.py                  # candidate plan generation: MockLLMClient, AdversarialMockLLMClient, GeminiClient
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
│   └── export_demo.py            # regenerates demo/index.html from a live pipeline run
├── demo/index.html               # standalone interactive replay for presenting to the teacher (see §11)
└── tests/                        # 60 tests, all passing (see §9)
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

## 9. Test coverage (60 tests, all passing)

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

`demo/index.html` is a standalone, interactive replay built specifically for showing this to the teacher. It requires no server, no internet, and no setup — open it directly in any browser. It shows, side by side in three columns (one per extension):

- **Phase 1 (Baseline)** and **Phase 2 + 4 (Validated)**: the exact same hand-verified adversarial candidate plan run through both. Baseline accepts a corner-deadlock push silently; the validator flags and rejects it ("corner deadlock, never added to plan graph"), with a synced step/play control across all three columns.
- **Phase 3 (With experience)**: the identical plan and steps a second time, except one earlier "episode" already recorded a mismatch on the plan's first uncertain (wall-hugging) step. That step's confidence visibly drops further here than in the plain Phase 2 column (0.50 → 0.17 in the current build) even though the validator's own verdict on it is unchanged — a small purple dot on the chain node and an on-page note both mark which step this is.
- Every accepted step in the Phase 2+4 and Phase 3 columns shows its full Phase 4 score breakdown underneath the badge: goal-distance change, regression, percent of the step budget used, and the resulting edge cost, not just a single confidence number.
- A toggle to switch to the optimal candidate instead, showing it solve the puzzle end to end in all three columns.
- The real solver output (graph node/edge counts, chosen path, cost) for all three graphs, pulled from an actual pipeline run, not typed in by hand.
- The Phase 2 stress-test numbers from §4.1 above, rendered as stat cards.
- **Phase 5 (same graph, two solvers):** a dedicated section below the stress-test stats, showing CP-SAT's and A*'s measured average planning time over 20 real episodes each (0.0176s vs 0.0027s, ~6.6x, in the current build), plus two cards showing which method adaptive selection actually picked on a single-box level (`astar`) versus a two-box level (`cp_sat`) — all pulled from a live 20-episode run per method, not hand-typed.
- **"Watch each solver work"**: two boards animating the *actual winning solution* on each level, independently steppable/playable. The single-box board just walks toward the goal (A*). The two-box board is the point: watching CP-SAT interleave two pushes (partway on one box, switch to the other, come back) makes "joint constraint coordination" concrete instead of an abstract phrase — and visibly, one box reaching its goal (solid teal fill) while the other is still in progress (amber) is the moment that actually shows why a single-box shortest-path search wouldn't be enough here.
- **River crossing section**: a two-column comparison (no grid at all — just left/right bank head counts and a boat indicator that slides side to side) replaying the exact fatal shortcut from §8.1: baseline accepts taking 2 missionaries across first, validated rejects it ("cannibals outnumber missionaries"). Below that, a full independently-steppable animation of the real 11-move safe solution.
- **Rush Hour section**: a full animation of the actual 6-move solution with real multi-cell vehicles (rendered as CSS grid items spanning their true length and orientation, not single-cell boxes) sliding on the board — the most visually distinct proof that this isn't Sokoban. Below that, a two-column comparison for the soft "uncertain" validator tier (§8.2.1) using the constructed example where `D` is boxed between the target and a vertical vehicle `E` that also can't move away yet; the page states directly that the hard-reject tier is a static level-design property, not something demonstrated as a live "move causes deadlock" moment, since that would misrepresent what it actually checks.

**It is generated, not hand-authored.** `demo/template.html` is the hand-written page (layout, styling, JS logic) with a placeholder where the data goes. Running `python experiments/export_demo.py` re-executes the real pipeline (baseline graph build, validated graph build, an experience-primed graph build, the Phase 2 stress test, the Phase 5 timing comparison, and the river crossing / Rush Hour builders) and bakes the fresh output into `demo/index.html`. **Whenever the pipeline changes** (as it did for Phase 4 — the solver-cost numbers on the page jumped from single digits into the hundreds because of the new scoring formula), rerun this script before presenting, or the demo will show stale numbers that no longer match the code. Do not hand-edit `demo/index.html` directly; edit `demo/template.html` instead.

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

## 13. What's left to reach 100% (Phase 6, not started)

- **Phase 6 — Evaluation & ablations:** run baseline vs. Phase 2 vs. Phase 3 vs. Phase 4 vs. Phase 5 vs. combined across all implemented levels *and now all three benchmarks* (Sokoban, river crossing, Rush Hour), with the aggregate metrics already being tracked in `metrics.py` and `EpisodeResult.path_selection_methods`.
- **Scope gap to flag to the teacher directly:** TAPE's own four named benchmarks are ALFWorld, MuSiQue, GSM8K-Hard, and Sokoban. Only Sokoban is implemented; river crossing and Rush Hour (§8) are additional benchmarks that prove the architecture generalizes, not substitutes for TAPE's own suite. If the final deliverable specifically needs generalization against TAPE's own benchmarks, ALFWorld/MuSiQue/GSM8K-Hard are still the gap, not river crossing/Rush Hour.
- **Tuning gap worth naming honestly:** `ScoreWeights`' default values (regression penalty 1.5, confidence penalty 4.0, budget penalty 2.0) were chosen to be directionally sensible, not fit to data. Phase 6 would be a natural place to actually tune them, or at least justify them empirically, rather than leaving them as reasonable-looking defaults.
