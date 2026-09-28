# Context prompt: TAPE extension project

Paste or upload this whole file at the start of a new chat. It brings you up to date on a university ML research project and its exact current state, so you can continue as if you had been in the earlier conversation.

## How to behave

- You are helping a student team (the user) with a semester ML research project. Their guide (teacher) approves the scope.
- Be direct and concise. Give a recommendation, not a survey of options.
- Report negative and null results as plainly as positive ones. This project deliberately keeps honest limits in its write-ups. Do not overclaim or round results up.
- When asked to explain, the user sometimes wants "explain like I'm 10". Use plain words and small examples.
- For any user-facing web copy: no em dashes, little text, and a look that does not seem AI-made.
- Before saying something exists or works, check the repository. Numbers below were true at the time of writing; if the repo disagrees, the repo wins.

## The project in one paragraph

We extend **TAPE** (Tool-Guided Adaptive Planning with Constrained Execution, Jeong et al. 2026). TAPE asks an LLM for several candidate plans, merges them into one **plan graph** (identical states share a node), lets an external solver (ILP/CP-SAT) pick the best path, executes it, and replans from the real state when the world does not match the graph. TAPE's authors name two unsolved problems: nothing checks a candidate move against the environment's real rules before it is trusted, and the solver is fixed per task. Our project adds five extensions and then evaluates them.

**Key constraint: the guide does not allow LLMs.** So there is no LLM anywhere in the experiments. "Proposers" (the thing that suggests candidate plans) are synthetic programs. This narrows the claim from "improves LLM agents" to "a proposer-agnostic checking and selection layer". A `GeminiClient` exists in the code but is unused. Class names `MockLLMClient` and `AdversarialMockLLMClient` are historical; they are simply proposers.

## The pipeline (one episode)

1. **Propose**: a proposer returns several candidate plans (action sequences).
2. **Merge**: each plan is simulated move by move; equal states become one node in a networkx DiGraph. Illegal moves end that plan early.
3. **Check** (Phase 2, 3): a per-game validator judges each move: reject (never enters the graph), accept with confidence 1.0, or accept with lower confidence (for example 0.5). The Phase 3 experience store multiplies in a learned trust from past failures.
4. **Choose** (Phase 4, 5): each edge gets an integer cost from progress toward the goal, confidence and step budget (cost x10 for CP-SAT). One moving piece uses A*; several pieces use CP-SAT (`level.complexity(state) > 1`).
5. **Run**: execute the chosen path; if a move's real result differs from the prediction, record the failure and replan from the real state.

## The six phases and their status

| Phase | Weight | What it is | Status |
|---|---|---|---|
| 1 | 25% | TAPE baseline: candidates, plan graph, CP-SAT, constrained execution, replanning | Done |
| 2 | 20% | Adaptive graph validation: domain validators (hard reject, or soft "uncertain" at confidence 0.5) | Done |
| 3 | 15% | Self-improving graph: sqlite `ExperienceStore`, Laplace-smoothed confidence per (state, action) | Done |
| 4 | 15% | Dynamic score per transition: goal-distance regression, confidence penalty, budget pressure | Done |
| 5 | 15% | Adaptive path selection: A* vs OR-Tools CP-SAT chosen by task complexity | Done |
| 6 | 10% | Evaluation and ablations | Core done; extras open |

About 97% of the plan is complete. All code is pushed. 66 automated tests pass.

## Benchmarks

All implement one interface (`src/tape/env_base.py`: `ACTIONS`, `step`, `is_goal`, `heuristic`, `complexity`, `render`).

- **Sokoban**: four hand-made levels (trivial, simple, multi with 2 boxes, hard with 3 boxes and a 29-move optimum). Validator: `CornerDeadlockValidator` (box pushed into a non-goal corner is rejected; box against a wall is "uncertain" at 0.5).
- **River Crossing** (missionaries and cannibals, 3 pairs, 2-seat boat, 11-move optimum). `step()` does not enforce the safety rule on purpose; `RiverSafetyValidator` does (cannibals outnumbering missionaries on either bank).
- **Rush Hour**: multi-cell sliding vehicles (6-move solution on the demo board). `RowGridlockValidator`: rejects a provably sealed row, gives "uncertain" (0.5) for a blocker that is itself stuck. The hard-reject rule is a static property of the level, not something a move creates, so the demo shows only the "uncertain" case for this game.
- **Boxoban**: DeepMind's public Sokoban levels (github.com/google-deepmind/boxoban-levels). Three files used, 1000 levels each, 10x10, 4 boxes: `unfiltered/valid/000.txt`, `medium/valid/000.txt`, `hard/000.txt`, stored in `data/boxoban/`. Proposer is weighted A* (weights 1, 2, 4, 8) under a per-search node budget (`src/tape/search_proposer.py`).

TAPE's other benchmarks (ALFWorld, MuSiQue, GSM8K-Hard) need an LLM and are dropped. Our numbers are therefore not comparable to the paper's.

## Results so far (all with synthetic proposers)

**1. Ablation** (`results/ablation.md`, 30 episodes per cell, slip 0.15, goal-biased mock proposer). Metric "safe success" = goal reached and no executed move rejected by an independent auditor.
- River Crossing: baseline 0% safe success (it reaches the goal every time but through forbidden states), with the validator 100%.
- Adaptive solver cuts planning time at identical quality where one piece moves: Sokoban trivial 16.9 to 0.2 ms, Sokoban simple 52 to 7.6 ms, River Crossing 62 to 3.6 ms. Rush Hour and two-box Sokoban: no gain (36.2 vs 36.1 ms, 99.9 vs 96.4 ms).
- Hard Sokoban is about 53% success in every configuration; none of our extensions changes it.

**2. Experience store under state-dependent slip** (`results/experience_test.md`; 25% of transitions slip with probability 0.7; 20 paired runs). Change in late-half replans per episode, store minus no store (negative is better): Sokoban simple -0.56 +/- 0.18, River Crossing -0.54 +/- 0.15, Rush Hour -0.17 +/- 0.11 (noise), two-box Sokoban +0.06 +/- 0.03 (no help). Under uniform-random slip the store showed no benefit, because there was nothing state-dependent to learn.

**3. ScoreWeights tuning** (`results/weight_tuning.md`): 80-point grid, fit on train seeds, checked on held-out seeds. Null result. The best train point was worse on held-out seeds (+0.122 +/- 0.111 against the defaults 1.5, 4.0, 2.0, which ranked 23 of 80 on train). Defaults kept.

**4. Proposer-quality sweep** (`results/proposer_sweep_*.md`, `QualityProposer`): a "guided" mix of goal-biased and random walks hit a floor (almost nothing solvable, so uninformative). In "corrupt" mode (an optimal plan with each step randomized with probability 1 - quality) the extra layers barely change success rate. River Crossing stays 0% safe in both arms because the proposer never knows the safety rule and a validator cannot invent a plan; the validator does cut replans by about 2.7 to 3.4 per episode at quality 0.7 and above. **Conclusion: the layer's value is safety and fewer wasted replans, not a higher goal-reach rate.**

**5. Boxoban, 1000 levels per set** (`results/boxoban*.md`). Solve rate within a node budget per search, no pruning vs with the corner-deadlock checker pruning the search:

| nodes | unfiltered | medium | hard |
|---|---|---|---|
| 2,000 | 57% vs 65% | 14% vs 23% | 6% vs 13% |
| 5,000 | 73% vs 82% | 29% vs 45% | 16% vs 29% |
| 10,000 | 84% vs 92% | 46% vs 65% | 27% vs 49% |
| 20,000 | 92% vs 96% | 61% vs 82% | 44% vs 70% |
| 30,000 | 95% vs 98% | 71% vs 88% | 54% vs 82% |

The checker wins in all 15 cells (95% intervals do not overlap) and never missed a level the no-pruning search solved. It expands 20%, 25% and 23% fewer nodes per level. This is standard Sokoban dead-corner pruning; the result shows our Phase 2 checker works as that pruner on real external levels, not that pruning is new. **Merging plans did not shorten paths:** across the three sets the merged path was shorter than the best single plan on 1 level in total and longer on 19, 9 and 5 levels, because the solver minimizes the Phase 4 cost, not move count.

## Decisions and their reasons (do not re-litigate without cause)

- No LLM: the guide's decision. All proposers are synthetic.
- The effect of a checker is measured as "safe success", because plain success hides rule-breaking in games whose `step()` does not enforce rules (River Crossing).
- Rush Hour's demo shows the "uncertain" tier only, because its hard-reject is a static level property and staging a fake "move causes deadlock" moment would misrepresent it.
- Uniform slip was replaced by state-dependent slip for testing the experience store, because uniform slip gives it nothing to learn.
- Boxoban search proposer uses weighted A* because blind BFS cannot solve 4-box levels.
- Default `ScoreWeights` kept after a null tuning result. This is not a proof they are optimal.

## Repository map

Repo: https://github.com/Harsh-v69/MachineLearningCP (branch `main`). Windows machine; use `.venv\Scripts\python.exe`.

- `src/tape/`: `env_base.py`, `envs/` (sokoban, river_crossing, rush_hour, boxoban, plus validators), `llm.py` (proposers, `_bfs_plan`), `search_proposer.py`, `graph.py`, `solver.py` (CP-SAT), `path_selector.py` (A*, `decide_method`), `scoring.py`, `experience.py`, `validator.py`, `executor.py` (`run_episode`, has `weights=`, `auditor=`, `slip_fn=`), `metrics.py`.
- `experiments/`: `run_baseline.py`, `run_river_crossing.py`, `run_rush_hour.py`, `stress_test.py`, `run_ablation.py`, `run_experience_test.py`, `tune_weights.py`, `run_proposer_sweep.py`, `run_boxoban.py` (use `--workers`; 40 at once ran out of resources), `export_demo.py`.
- `results/`: tables written by the experiments. `data/boxoban/`: level files.
- `demo/template.html` (hand-written) and `demo/index.html` (generated by `python experiments/export_demo.py`; never edit it by hand). `docs/pipeline_diagram.html`: system flow diagram.
- `progress.md`: the full write-up, written to be read on its own by teammates. **Read it for detail beyond this file.**
- `tests/`: 66 tests. Run with `python -m pytest tests/ -q`.

## The demo ("Plan Check")

A guided walkthrough, one screen at a time: Start (with an interactive project map: Input, Preparation, What we changed, Algorithms, Outcomes, Pipeline changes), Pick a game (Sokoban, River Crossing, Rush Hour), then Propose, Merge, Check (rule checker on/off), Choose (A* vs CP-SAT timings and pick), Run (a forced slip, replan, and trust dropping to 0.33), then Results (safety, speed, real Boxoban levels with a set switcher, memory, and a "what this does not show" list). Every board and number comes from a live run of the code. Open `demo/index.html`, or serve it with `python -m http.server 8000 --directory demo`. Published artifact (private until shared): https://claude.ai/artifact/QKMajmwWBLJcgEhd4sANX1

## What is still open

- Write the paper. The supported claim is narrow (see result 4 and 5).
- A learned non-LLM proposer (imitation or RL policy) for more realistic errors. Needs the guide's approval, since it is unclear whether learned models count as allowed.
- More Boxoban: other files per set, a second checker rule (for example frozen boxes).
- Known weaknesses: synthetic proposers, the experience store only helps when candidates contain a detour, merging did not shorten paths.

## Timeline

Mid-semester review needs about 60% progress and a demonstration. The end-semester review needs the final deliverable. The project is now well past the mid-semester bar.

## Two tips learned the hard way

- A page served by `python -m http.server` needs `<meta charset="utf-8">`, or non-ASCII text turns to garbage.
- Do not describe pruning, or any Sokoban technique, as a new contribution. Frame it as validation on real levels.
