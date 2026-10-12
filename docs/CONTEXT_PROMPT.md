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

About 97% of the plan is built, but only about 55% of the way to a publishable paper (see progress.md Sec 17: experiments need classical baselines and a stronger rule-checked game, the paper needs figures and a verification pass, and the novelty claim needs sharpening). All code is pushed. 90 automated tests pass.

## Benchmarks

All implement one interface (`src/tape/env_base.py`: `ACTIONS`, `step`, `is_goal`, `heuristic`, `complexity`, `render`).

- **Sokoban**: four hand-made levels (trivial, simple, multi with 2 boxes, hard with 3 boxes and a 29-move optimum). Validator: `CornerDeadlockValidator` (box pushed into a non-goal corner is rejected; box against a wall is "uncertain" at 0.5).
- **River Crossing** (missionaries and cannibals, 3 pairs, 2-seat boat, 11-move optimum). `step()` does not enforce the safety rule on purpose; `RiverSafetyValidator` does (cannibals outnumbering missionaries on either bank).
- **Rush Hour**: multi-cell sliding vehicles (6-move solution on the demo board). `RowGridlockValidator`: rejects a provably sealed row, gives "uncertain" (0.5) for a blocker that is itself stuck. The hard-reject rule is a static property of the level, not something a move creates, so the demo shows only the "uncertain" case for this game.
- **Boxoban**: DeepMind's public Sokoban levels (github.com/google-deepmind/boxoban-levels). Three files used, 1000 levels each, 10x10, 4 boxes: `unfiltered/valid/000.txt`, `medium/valid/000.txt`, `hard/000.txt`, stored in `data/boxoban/`. Proposer is weighted A* (weights 1, 2, 4, 8) under a per-search node budget (`src/tape/search_proposer.py`).

- **Peg Solitaire** (English board, about 3.6M reachable positions): checker = pagoda bound (provable mid-play pruning) plus a soft "isolated peg" tier. Weighted A* proposer.
- **24-puzzle** (5x5 sliding tiles, about 7.8e24 states): checker = parity rule; it only guards the start (legal moves never break parity). Weighted A* proposer.
- **Rubik's cube** 3x3x3 (and 2x2x2), moves built from geometry: checker = cubie invariants (twist, flip, parity); guards the start only. Meet-in-the-middle proposer (`src/tape/bidirectional.py`), reaches 8-move scrambles.

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

**6. Harder games** (`results/hard_games.md`, 60 instances per row, 30 for the cube; progress.md Sec 18). Peg Solitaire: the pagoda checker cuts the real start position's search from 139,048 to 82,009 nodes, and on solvable positions built backwards from the goal it solves 98% vs 93% (22 jumps) and 75% vs 58% (26 jumps), using about 20 to 30% fewer nodes; it never lost a position the plain search solved. 24-puzzle: weighted A* solves random-walk scrambles of 20, 40, 60, 80 moves 100%, 95%, 73%, 57%. Rubik's cube: all scrambles of 4 to 8 moves solved. For the 24-puzzle and the cube the checker changes no result on a solvable start; on an unsolvable start it saves the whole search (60,000 and 400,000 nodes vs 1 and 0). Caveats: scrambles are random walks (easier than random instances), the cube is only tested to 8-move scrambles, and for these two games the checker is a start gate, not a planning improvement.

**7. Other search methods** (`results/search_methods.md`, progress.md Sec 19). DFS helps in exactly one game: Peg Solitaire from the real start (10,845 nodes against 139,048 for weighted A*; BFS finds nothing). BFS is enough only on River Crossing and Rush Hour. Weighted A* is the best general choice. AO* does not apply because every game is deterministic (it reduces to A*); LAO* would only matter for the slip model, and is not implemented.

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
- `tests/`: 90 tests. Run with `python -m pytest tests/ -q`.

## The demo ("Plan Check")

A tabbed walkthrough with a Light / Dark switch. Tabs: Overview (game tiles, interactive project map, table of the six phases), Sokoban, River Crossing, Rush Hour, Peg Solitaire, 24-Puzzle, Rubik's Cube (each runs five steps: Propose, Merge, Check with the rule checker on and off, Choose with A* vs CP-SAT timings, Run with a forced slip and replan), Boxoban (one real level replayed with and without the checker, plus the 3,000-level solve-rate chart with a set switcher), and Results (safety, speed, harder games, memory, and what the data does not show). On the 24-Puzzle and Rubik's Cube the Check step shows an unsolvable start instead of a rejected move. The cube, Peg Solitaire and 24-puzzle are animated, draggable 3D objects (CSS 3D, no library). The cube tab has a Randomize button that scrambles and solves in the browser (JavaScript copy of the meet in the middle search). Every board and number comes from a live run of the code. Open `demo/index.html`, or serve it with `python -m http.server 8000 --directory demo`. Published artifact (private until shared): https://claude.ai/artifact/QKMajmwWBLJcgEhd4sANX1

## Demo detail worth knowing

Every game is a draggable 3D board (CSS 3D, no library). Propose names what produced each plan; Peg Solitaire's Plan B is a greedy walk. Run offers a slip or a wrong move; the wrong move is the worst alternative found per game: lost (checker flags it, River Crossing), deadend (only a full search shows it, Peg Solitaire and Sokoban), or detour (24-puzzle, cube, Rush Hour). The cube and the 24-puzzle have a Randomize button that scrambles and solves in the browser (progress.md Sec 21).

## Documents

`docs/CP_Project_Review.pptx` is the 20 slide review deck (subject Machine Learning, guide Dr. Premanand P Ghadekar, Group 3: Divyanshu Gajbhiye, Vidhi Hadoltikar, Harshvardhan Rawat, Nirmit Hatti). `paper/paper.md` is the paper source, with `paper/paper.docx` as the Word version and figures in `paper/figures/`. Both are generated from the results files by scripts (`docs/build_review_ppt.py`, `paper/build_paper_docx.py`, `paper/make_figures.py`); edit the scripts or the markdown, then rebuild.

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
