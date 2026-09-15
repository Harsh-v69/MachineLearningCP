# Progress: TAPE Extension — Adaptive Graph Validation & Solver Generalization

**Overall status: ~60% complete (Phases 1–3 of 6), on schedule for the mid-semester checkpoint.**

This document is meant to be read start to finish by a teammate who has not touched the code yet, and to be enough on its own to explain the project to the teacher. It covers what the project is, what's been built, why each piece exists, how to run it, and exactly what's left.

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

Our project builds three extensions addressing these gaps, on top of a faithful reproduction of the TAPE baseline. The full 6-phase plan (see the roadmap artifact shared earlier) allocates roughly:

| Phase | Weight | Status |
|---|---|---|
| 1 — TAPE Baseline | 25% | ✅ Done |
| 2 — Adaptive Graph Validation | 20% | ✅ Done |
| 3 — Self-Improving Graph | 15% | ✅ Done |
| 4 — Dynamic Reachability/Utility Score | 15% | ⏳ Not started |
| 5 — Adaptive Path Selection (A*/AO* vs solver) | 15% | ⏳ Not started |
| 6 — Evaluation & Ablations | 10% | ⏳ Not started |

**Phases 1–3 sum to 60%, which is where the project currently stands.**

---

## 2. Repository layout

```
MachineLearningCP/
├── ML_CP.docx                 # original project proposal (source of truth for scope)
├── requirements.txt           # networkx, ortools, google-generativeai, pytest
├── .env.example                # GEMINI_API_KEY (copy to .env, fill in, do not commit)
├── src/tape/
│   ├── envs/sokoban.py         # the benchmark environment (Phase 1)
│   ├── llm.py                  # candidate plan generation: MockLLMClient, GeminiClient
│   ├── graph.py                # plan graph construction + validation hook
│   ├── solver.py                # CP-SAT path selection (OR-Tools)
│   ├── executor.py             # constrained execution + mismatch-triggered replanning
│   ├── validator.py             # Phase 2: CornerDeadlockValidator
│   ├── experience.py             # Phase 3: sqlite-backed ExperienceStore
│   └── metrics.py                # aggregate metrics across episodes
├── experiments/run_baseline.py  # CLI to run episode sweeps with any combination of extensions
└── tests/                        # 20 tests, all passing (see §6)
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
- `build_validated_plan_graph()` in `graph.py`: identical to the Phase 1 graph builder, except every physically-legal step is also passed through the validator before being added as an edge. A rejected step dead-ends that candidate right there, instead of silently entering the graph. An accepted-but-uncertain step is still added, but its edge cost is inflated (`cost = round(1/confidence)`) — meaning the **same CP-SAT solver from Phase 1**, unmodified, naturally prefers fully-trusted paths over uncertain ones, purely because of how the cost is computed. No solver changes were needed for this.
- Wired into `run_episode()` / `run_baseline.py` as an optional `validator=` parameter / `--validator corner-deadlock` CLI flag, so **baseline vs. validated is a flip of one flag** — this is exactly the controlled ablation the evaluation plan (Phase 6) needs.

**Verified behaviour:** `tests/test_validator.py` constructs an exact corner-deadlock scenario (`#####` / `#   #` / `#$  #` / `#@ .#` / `#####`, pushing the box up wedges it at (1,1), a corner off the goal at (3,3)) and confirms:
- The Phase 1 baseline graph accepts this push as a normal edge (`invalid_transitions == 0`).
- The Phase 2 validator rejects it (`validator_rejections == 1`, the edge never enters the graph).
- Pushing a box directly onto a goal is never mistakenly flagged as a deadlock.
- A box against one wall (not a corner) is accepted with confidence 0.5, which produces a higher-cost edge.

**Honest limitation:** on the levels currently implemented (single-box `simple`, and the newly added two-box `LEVEL_MULTI`), the goal-biased mock LLM's noisy candidates rarely happen to wander into a corner by chance — so aggregate metrics (success rate, etc.) look identical with the validator on or off in our current test runs. The validator's *unit-level* correctness is proven directly (above); its *aggregate* payoff would show up more clearly against a noisier candidate source (a real LLM's mistakes, or an adversarially-random one) or a level shaped so a corner sits directly on a natural-looking path. This is flagged here rather than papered over — it's a fair question a teacher could ask.

**Run it:**
```bash
python experiments/run_baseline.py --level simple --episodes 30 --slip 0.1 --validator corner-deadlock
```

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

## 6. Test coverage (20 tests, all passing)

```
tests/test_sokoban.py     4  — environment legality: pushes, walls, box-into-wall, rendering
tests/test_graph.py       2  — candidate merging onto shared nodes; illegal steps become dead ends
tests/test_solver.py      3  — shortest path found, cheaper of two candidates preferred, infeasible → None
tests/test_pipeline.py    5  — end-to-end: mock LLM solves trivial/simple/two-box levels, slips trigger replanning and still recover
tests/test_validator.py   4  — corner-deadlock rejected, goal-push never falsely flagged, wall-hug is "uncertain" not rejected, baseline accepts what the validator rejects
tests/test_experience.py  3  — no-history = full trust, failures lower confidence below successes, cross-episode persistence actually happens
```

Run everything:
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/ -q
```

---

## 7. Setup notes for teammates

- Needs Python 3.11+, a venv (`python -m venv .venv`), then `pip install -r requirements.txt`.
- `GEMINI_API_KEY` (copy `.env.example` to `.env` and fill in) is only needed for `--llm gemini`; all tests and the default `--llm mock` run with zero API keys or network access.
- We hit a real disk-space wall during setup (the `google-generativeai` SDK alone pulled the free space on one machine from ~3GB to negative) — this is why Gemini is called directly over HTTP instead of through the SDK. If you `pip install google-generativeai` anyway for some other reason, budget several hundred MB.

---

## 8. What's left to reach 100% (Phases 4–6, not started)

- **Phase 4 — Dynamic reachability/utility score:** replace the current flat edge cost (1, or `1/confidence`) with a proper per-state score combining goal proximity, accumulated cost, remaining budget, and confidence.
- **Phase 5 — Adaptive path selection:** use that score as an A*/AO* heuristic where feasible, keeping CP-SAT for tasks that genuinely need hard-constraint optimization, and choose between them per task.
- **Phase 6 — Evaluation & ablations:** run baseline vs. Phase 2 vs. Phase 3 vs. combined across all implemented levels (and, time permitting, additional benchmarks beyond Sokoban), with the aggregate metrics already being tracked (§1 in `metrics.py`).
- **Scope gap to flag to the teacher directly:** ALFWorld, MuSiQue, and GSM8K-Hard (three of TAPE's four benchmarks) are not implemented. If cross-benchmark generalization is expected for the final deliverable, at least one more environment should be added before Phase 6.
