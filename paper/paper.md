# A Validation and Adaptive-Selection Layer for Plan-Graph Planning: An LLM-Free Extension of TAPE

**Authors:** Divyanshu Gajbhiye, Vidhi Hadoltikar, Harshvardhan Rawat, Nirmit Hatti
**Guide:** Dr. Premanand P Ghadekar
**Course:** Machine Learning, Year 3, Semester 1 (Group 3)

> **Draft status.** First full draft written from the project's measured results. Every number below comes from a file in `results/` and can be regenerated with the commands in the Appendix. Items marked **[TODO]** need a decision or more work before submission. Sections 1 to 9 follow a conventional conference layout; reformat to the target venue's template at the end.

---

## Abstract

Plan-graph planners such as TAPE merge several candidate plans into one graph and let an external solver pick a path. Two weaknesses remain: a move is trusted without being checked against the environment's rules, and a single solver is used for every task. We add a layer that (i) validates each move with a per-game checker that rejects impossible moves and downweights doubtful ones, (ii) scales trust by a persistent record of past failures, (iii) scores each move from goal progress, confidence and budget, and (iv) chooses between A\* and a constraint solver according to how many pieces can move. No language model is used; candidate plans come from synthetic and search-based proposers. We evaluate on Sokoban, River Crossing, Rush Hour and 3,000 levels of the public Boxoban set. The checker turns River Crossing from 0% to 100% safe success and, used to prune search, raises Boxoban solve rates at every node budget in every difficulty set (for example 54% to 82% on the hard set at 30,000 nodes). Adaptive selection cuts planning time where one piece moves, and failure memory reduces replans when failures depend on the state. We also report what did not work: tuning the cost weights found nothing better than the defaults, merging plans did not shorten paths, and with a competent proposer the layer's benefit is safety and fewer wasted replans, not a higher goal-reach rate.

---

## 1. Introduction

Long-horizon planning is hard for language-model agents because a single plan often fails midway. TAPE [1] responds by generating several candidate plans, merging states they share into one **plan graph**, selecting a feasible path with an external solver, executing it under constrained decoding, and replanning when the observed state differs from the predicted one. The TAPE authors name two open problems: the graph is only as reliable as the plans behind it, and the solver is fixed in advance.

This project builds on TAPE and targets both problems, in a setting where the proposer of candidate plans is not a language model. Our contributions are:

1. **Move validation.** A per-game validator that rejects moves the rules forbid and lowers confidence in moves that look risky, before a move enters the graph.
2. **Experience-weighted trust.** A persistent store of successes and failures per (state, move) that scales confidence in later episodes.
3. **A move score.** One cost per move combining goal progress, confidence and step budget, minimized by the solver.
4. **Adaptive path selection.** A\* when one piece can move, a constraint solver (CP-SAT) when several must be coordinated.
5. **An evaluation across four benchmark families**, including 3,000 externally defined levels, with an independent safety audit, held-out checks, and negative results reported alongside positive ones.

The guide ruled out language models for this project. We treat that as a design constraint: the contribution is a proposer-agnostic checking and selection layer, evaluated with proposers whose quality we can control.

## 2. Related Work

**Reasoning and acting with language models.** ReAct [2] interleaves reasoning with actions and observations. Tree of Thoughts [3] searches a tree of reasoning steps with look-ahead and backtracking, and Graph of Thoughts [4] generalizes this to an arbitrary graph in which paths can merge. Reflexion [5] uses verbal feedback from past failures, Toolformer [6] teaches models to call tools, and chain-of-thought prompting [7] elicits step-by-step reasoning. Plan-and-Solve [8] and ReWOO [9] separate planning from execution. TAPE [1] combines a merged plan graph with an external solver and evaluates on Sokoban, ALFWorld [10], MuSiQue [11] and GSM8K-Hard (a harder variant of GSM8K [12]).

**Gap.** These systems check a plan mainly by acting on it. None validates a proposed move against known environment rules before trusting it, and feedback from failures is textual rather than a per-move confidence. TAPE's solver is fixed per task.

**Search and puzzle complexity.** A\* [13] is the standard heuristic shortest-path method. Sokoban [14] and Rush Hour [15] are PSPACE-complete, which makes them hard, structured test beds. Pruning dead corners is a standard Sokoban solver technique; we use it as a validator and measure it, without claiming it as new. Boxoban [16] provides a public level set; we solve with OR-Tools CP-SAT [17].

## 3. Background: the TAPE pipeline

Given a state, TAPE (1) asks the proposer for candidate plans, (2) simulates each plan and merges equal states into one graph node, (3) assigns edge costs, (4) selects a path from the current state to a goal with an integer program, (5) executes it, and (6) replans from the real state if a move's result differs from the prediction. We reimplemented this pipeline as our baseline, with CP-SAT as the solver.

## 4. Method

All benchmarks implement one interface: `ACTIONS`, `step`, `is_goal`, `heuristic`, `complexity` and `render`. A new game therefore plugs into the pipeline without changing it.

### 4.1 Move validation

A validator returns, for a move from state *s* to *s'*, either **reject**, or **accept** with a confidence in (0, 1]. A rejected move is never added to the graph, so any candidate plan that uses it ends there. We implemented three validators:

- **Sokoban:** pushing a box into a corner that is not a goal is rejected (it can never be recovered); a box resting against a wall off a goal is accepted at confidence 0.5.
- **River Crossing:** a state in which cannibals outnumber missionaries (with at least one missionary present) on either bank is rejected. The environment's `step` deliberately does not enforce this, so the rule lives only in the validator.
- **Rush Hour:** a row filled entirely by horizontal vehicles that block the target is rejected; a blocker that is itself stuck is accepted at confidence 0.5.

### 4.2 Experience store

A SQLite table records successes and failures per (level, state, move). Confidence is Laplace-smoothed:

confidence = (successes + 1) / (successes + failures + 2)

with no history meaning full trust. It multiplies the validator's confidence. One recorded failure lowers trust from 1.00 to 0.33.

### 4.3 Move score

Each accepted move receives an integer cost (scaled by 10 for the integer solver):

cost = round(10 × [ 1 + 1.5 × regression + 4.0 × (1 − confidence) + 2.0 × (steps used / budget)² ]), at least 1,

where *regression* = max(0, h(s') − h(s)) is how much the move increases the game's heuristic distance to the goal. The weights are defaults; Section 6.3 tests whether tuning improves them.

### 4.4 Adaptive path selection

Path selection is A\* (using the same cost) when `complexity(state) = 1` (one independently movable piece: a single Sokoban box, the River Crossing boat) and CP-SAT when it exceeds 1 (several boxes or vehicles whose routes can conflict).

### 4.5 Execution and replanning

The chosen path is executed move by move. On a mismatch the failure is recorded in the experience store and planning restarts from the real state, up to a replan limit.

## 5. Experimental Setup

**Benchmarks.** Sokoban (four hand-made levels, from one to three boxes, the hardest with a 29-move optimum); River Crossing (three missionary-cannibal pairs, two-seat boat, 11-move optimum); Rush Hour (a six-move board); and **Boxoban** [16]: one file (`000.txt`) from each difficulty set (`unfiltered/valid`, `medium/valid`, `hard`), 1,000 ten-by-ten levels with four boxes each, 3,000 levels in total.

**Proposers (no language model).**
- *Goal-biased mock:* one BFS-optimal plan plus noisy goal-biased walks. Because it always plants a good plan, absolute success rates with it are optimistic (Section 8).
- *Adversarial:* uniform random moves with no guaranteed good plan.
- *Quality proposer:* mixes goal-biased and random walks ("guided"), or takes an optimal plan and randomizes each step with probability 1 − quality ("corrupt").
- *Weighted A\* proposer (Boxoban):* runs weighted A\* with weights 1, 2, 4, 8 under a per-search node budget and returns the plans that finish.

**Metrics.** *Safe success*: the goal is reached and no executed move is rejected by an independent domain auditor, whether or not the configuration used a validator. This matters because plain success hides rule-breaking in games such as River Crossing whose `step` does not enforce rules. We also report replans per episode, planning time, and (Boxoban) the share of levels solved within a node budget. Intervals are 95% Wilson intervals for proportions; for paired comparisons, mean difference ± standard error over seeds.

## 6. Results

### 6.1 Ablation: safety and speed

Five configurations (baseline; +validator; +validator+experience; +adaptive selection; all) were run on six benchmarks, 30 episodes per cell, 15% slip, goal-biased proposer.

| River Crossing | Safe success | Goal reached |
|---|---|---|
| Baseline (no validator) | 0% | 100% |
| With validator | 100% | 100% |

| Planning time per episode (ms) | Always CP-SAT | Adaptive |
|---|---|---|
| Sokoban, one box | 51.8 | 7.6 |
| River Crossing | 62.1 | 3.6 |
| Sokoban, two boxes | 99.9 | 96.4 |
| Rush Hour | 36.2 | 36.1 |

The validator converts unsafe successes into safe ones. Adaptive selection saves time where one piece moves and ties elsewhere, with identical success and action counts. Hard Sokoban stays near 53% in every configuration: none of the extensions changes it.

### 6.2 Experience store under state-dependent failure

With uniform random slips the store gave no benefit, since there is nothing state-dependent to learn. We therefore made 25% of (state, move) pairs slip with probability 0.7 and compared validator-only against validator plus store, paired over 20 hazard seeds of 30 episodes, 30 candidates per round.

| Benchmark | Late-half replans, store minus no store | Success difference |
|---|---|---|
| Sokoban, one box | −0.56 ± 0.18 | +5.5 points |
| River Crossing | −0.54 ± 0.15 | +5.0 points |
| Rush Hour | −0.17 ± 0.11 | +1.2 points |
| Sokoban, two boxes | +0.06 ± 0.03 | −0.2 points |

The store reduces replans by roughly 14% on two games and does nothing on the others. Our reading, not tested here, is that with more possible routes the candidates rarely contain a detour around a learned hazard, and the store can only reweight edges already in the graph.

### 6.3 Tuning the score weights

We searched 80 combinations of the three penalty weights (regression {0, 0.75, 1.5, 3}, confidence {0, 2, 4, 8, 16}, budget {0, 1, 2, 4}) on 8 training seeds and re-ran the top three and the defaults on 16 unseen seeds. The objective was replans + 3 × (1 − success) averaged over four benchmarks (lower is better). The best training point (0, 16, 2) had objective 3.906 against 4.219 for the defaults (rank 23 of 80) but was worse on held-out seeds (+0.122 ± 0.111). No candidate beat the defaults by more than one standard error. **We keep the defaults; this is a null result, not proof that they are optimal.**

### 6.4 Proposer quality

To see how much the layer helps as proposer quality changes, we compared baseline against the full layer under the state-dependent failure model (10 hazard seeds × 20 episodes, 30 candidates). The "guided" proposer hit a floor (at most 17% success on the easiest non-trivial level, none on the harder ones) and was uninformative. With the "corrupt" proposer, quality 0.5 to 0.95, the extra layers barely change the goal-reach rate on Sokoban and Rush Hour: almost every paired difference is within two standard errors of zero. River Crossing stays at 0% safe success in both arms because this proposer never learns the safety rule, so its optimal plan is the unsafe one and the validator, correctly, rejects it; the validator does cut replans by 2.7 to 3.4 per episode at quality 0.7 and above by rejecting unsafe plans early. **A validator filters proposals; it does not create them.**

### 6.5 Boxoban

Solve rate is the share of 1,000 levels per set for which any of the four searches finds a plan within the node budget. Without pruning the search is unaware of dead corners; with the checker it prunes them.

| Nodes per search | Unfiltered | Medium | Hard |
|---|---|---|---|
| 2,000 | 57% vs 65% | 14% vs 23% | 6% vs 13% |
| 5,000 | 73% vs 82% | 29% vs 45% | 16% vs 29% |
| 10,000 | 84% vs 92% | 46% vs 65% | 27% vs 49% |
| 20,000 | 92% vs 96% | 61% vs 82% | 44% vs 70% |
| 30,000 | 95% vs 98% | 71% vs 88% | 54% vs 82% |

Each cell is no pruning vs with checker. The checker wins in all 15 cells, the 95% intervals do not overlap in any of them, and pruning never missed a level that no-pruning solved (0 of 1,000 in every cell). The gain grows with difficulty: at 10,000 nodes it is 8, 19 and 22 points; at 30,000 nodes 3, 17 and 28 points. The checker also expands 20%, 25% and 23% fewer nodes per level at the full budget. **Merging plans did not shorten paths:** the merged path was shorter than the best single plan on one level in total (by two moves) and longer on 19, 9 and 5 levels across the three sets, because the solver minimizes the Section 4.3 cost, not move count.

## 7. Discussion

The layer's value depends on the proposer. Where the environment allows moves that are physically legal but forbidden by a rule, checking is decisive: River Crossing goes from 0% to 100% safe. Used as a pruner inside a search, the same idea solves substantially more real Boxoban levels within a fixed budget, and more so on harder sets. Adaptive selection is a plain efficiency gain. Failure memory helps only when failures are state-dependent and the candidates contain an alternative. When the proposer is already competent, the layer does not raise the goal-reach rate; its contribution is safety and fewer wasted replans.

## 8. Limitations and Threats to Validity

- **Synthetic proposers.** No language model was used, so results say nothing about real model failures. The goal-biased mock plants a BFS-optimal plan, which inflates absolute success rates in Sections 6.1 and 6.2; the paired comparisons are less affected but should be read in that light.
- **Corner pruning is not new.** It is standard in Sokoban solvers; Section 6.5 shows our validator works as that pruner on external levels, not that pruning is a contribution.
- **Coverage.** One file per Boxoban set, one checker rule, and hand-made levels elsewhere. Other files and other rules (for example frozen boxes) were not run.
- **Not comparable to TAPE.** ALFWorld, MuSiQue and GSM8K-Hard require a language model and are out of scope, so our numbers cannot be compared to the original paper's.
- **Tuning.** The weight search used 8 training seeds, so its ranking is noisy.
- **Merging.** Merged paths were not shorter than the best single plan, so we make no claim that graph merging improves plan quality in these settings.

## 9. Conclusion and Future Work

We built a validation and adaptive-selection layer on the TAPE pipeline and evaluated it on four benchmark families without any language model. Rule checking made plans safe and made search solve more real levels; choosing the solver per task saved planning time; failure memory reduced replans when failures depend on the state. Several hoped-for effects did not appear, and we report them. Next steps: a learned, non-LLM proposer with realistic errors (**[TODO]** confirm with the guide whether learned models are allowed), further Boxoban files and a second checker rule, and reformatting for the target venue.

## References

[1] J. Jeong, J. Kim, K. Lee, "TAPE: Tool-Guided Adaptive Planning and Constrained Execution in Language Model Agents," arXiv:2602.19633, 2026.
[2] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, Y. Cao, "ReAct: Synergizing Reasoning and Acting in Language Models," arXiv:2210.03629, 2022.
[3] S. Yao, D. Yu, J. Zhao, I. Shafran, T. L. Griffiths, Y. Cao, K. Narasimhan, "Tree of Thoughts: Deliberate Problem Solving with Large Language Models," arXiv:2305.10601, 2023.
[4] M. Besta et al., "Graph of Thoughts: Solving Elaborate Problems with Large Language Models," arXiv:2308.09687, 2023.
[5] N. Shinn, F. Cassano, E. Berman, A. Gopinath, K. Narasimhan, S. Yao, "Reflexion: Language Agents with Verbal Reinforcement Learning," arXiv:2303.11366, 2023.
[6] T. Schick et al., "Toolformer: Language Models Can Teach Themselves to Use Tools," arXiv:2302.04761, 2023.
[7] J. Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," arXiv:2201.11903, 2022.
[8] L. Wang et al., "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models," arXiv:2305.04091, 2023.
[9] B. Xu et al., "ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models," arXiv:2305.18323, 2023.
[10] M. Shridhar et al., "ALFWorld: Aligning Text and Embodied Environments for Interactive Learning," arXiv:2010.03768, 2020.
[11] H. Trivedi, N. Balasubramanian, T. Khot, A. Sabharwal, "MuSiQue: Multihop Questions via Single-hop Question Composition," arXiv:2108.00573, 2021.
[12] K. Cobbe et al., "Training Verifiers to Solve Math Word Problems," arXiv:2110.14168, 2021.
[13] P. E. Hart, N. J. Nilsson, B. Raphael, "A Formal Basis for the Heuristic Determination of Minimum Cost Paths," IEEE Trans. Systems Science and Cybernetics, 1968.
[14] J. Culberson, "Sokoban is PSPACE-complete," Technical Report TR97-02, University of Alberta, 1997.
[15] G. W. Flake, E. B. Baum, "Rush Hour is PSPACE-complete, or 'Why you should generously tip parking lot attendants'," Theoretical Computer Science 270(1-2):895-911, 2002.
[16] DeepMind, "Boxoban levels," https://github.com/google-deepmind/boxoban-levels.
[17] L. Perron, V. Furnon, "OR-Tools," Google, https://developers.google.com/optimization.

**[TODO]** Confirm publication details for [13] (volume and pages) and add the software version for [17] before submission. Verify against [1] how GSM8K-Hard relates to GSM8K [12], and cite the GSM8K-Hard source directly if [1] does.

## Appendix: reproducing the results

```bash
python -m pytest tests/ -q                                   # 66 tests
python experiments/run_ablation.py --episodes 30             # Section 6.1  -> results/ablation.md
python experiments/run_experience_test.py --runs 20 --episodes 30   # 6.2   -> results/experience_test.md
python experiments/tune_weights.py                           # 6.3          -> results/weight_tuning.md
python experiments/run_proposer_sweep.py corrupt             # 6.4          -> results/proposer_sweep_corrupt.md
python experiments/run_boxoban.py --levels 1000 --workers 12 --file data/boxoban/hard_000.txt --out boxoban_hard.md   # 6.5
```

Code and data: https://github.com/Harsh-v69/MachineLearningCP
