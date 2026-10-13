# A Validation and Adaptive-Selection Layer for Plan-Graph Planning

> **Format.** The Word version (`paper/paper.docx`) follows the ICCISD two-column IEEE template and is generated from this file by `paper/build_paper_docx.py`; figures come from `paper/make_figures.py`. Every number comes from a file in `results/`. Section numbers and subsection letters are added by the builder. Items marked **[TODO]** need a decision before submission.

## Abstract

Plan-graph planners such as TAPE merge several candidate plans into one graph and let an external solver choose a path. Two weaknesses remain: a move is trusted without being checked against the rules of the environment, and one solver is used for every task. This paper describes a checking and selection layer that validates every move with a per-game rule checker, scales trust by a persistent record of past failures, scores each move from goal progress, confidence and budget, and chooses between A* and a constraint solver according to how many pieces can move. No language model is used. The layer is evaluated on seven games: Sokoban, River Crossing, Rush Hour, Peg Solitaire, the 24-puzzle, the Rubik's cube, and 3,000 levels of the public Boxoban set. The checker raises River Crossing from 0% to 100% safe success and, used to prune search, solves more Boxoban levels at every node budget in every difficulty set (54% to 82% on the hard set at 30,000 nodes). Adaptive selection cuts planning time where one piece moves, and failure memory reduces replans when failures depend on the state. A comparison of search methods shows that depth-first search helps only on Peg Solitaire, and that AO* does not apply to deterministic games. Several expected effects did not appear and are reported: tuning the cost weights found nothing better than the defaults, and merging plans did not shorten paths.

Keywords: plan graph, rule validation, adaptive solver selection, A* search, constraint programming, puzzle benchmarks, safe planning.

## Introduction

Long-horizon planning is hard because a single plan often fails midway. A recent framework, TAPE [1], responds by generating several candidate plans, merging the states they share into one plan graph, selecting a feasible path with an external solver, executing it under constrained decoding, and replanning when the observed state differs from the predicted one. The authors of TAPE name two open problems: the graph is only as reliable as the plans behind it, and the solver is fixed in advance.

This work builds on TAPE and targets both problems. Nothing in the original pipeline checks a proposed move against the rules of the environment before the move is trusted, so an illegal or fatal move is found only when execution fails. Past failures are forgotten between episodes, and the same solver is used whether a task needs it or not. These weaknesses are easy to see in simple puzzles. In River Crossing a plan can reach the goal while breaking the safety rule on the way. In Sokoban a box pushed into a corner can never be recovered. In Rush Hour two blocked vehicles can seal a row.

The contributions of this paper are: (i) a per-game move validator that rejects moves the rules forbid and lowers confidence in risky ones before they enter the graph; (ii) an experience store that scales confidence by the history of each state and move; (iii) one move score combining goal progress, confidence and step budget; (iv) adaptive path selection, with A* when one piece can move and a constraint solver when several must be coordinated; and (v) an evaluation on seven games, including 3,000 externally defined levels and three harder puzzles, with an independent safety audit, held-out checks, a comparison of search methods, and negative results reported next to positive ones. The plan proposers in this work are programs, not language models, which makes every experiment reproducible and lets the quality of the proposer be controlled.

## Literature Review

Several lines of work combine reasoning with action. ReAct [2] interleaves reasoning with actions and observations. Tree of Thoughts [3] searches a tree of reasoning steps with look-ahead and backtracking, and Graph of Thoughts [4] generalizes this to an arbitrary graph in which paths can merge. Reflexion [5] uses verbal feedback from past failures, Toolformer [6] teaches models to call tools, and chain-of-thought prompting [7] elicits step-by-step reasoning. Plan-and-Solve [8] and ReWOO [9] separate planning from execution. TAPE [1] combines a merged plan graph with an external solver and evaluates on Sokoban, ALFWorld [10], MuSiQue [11] and GSM8K-Hard, a harder variant of GSM8K [12].

These systems check a plan mainly by acting on it. None validates a proposed move against known environment rules before trusting it, feedback from failures is textual rather than a per-move confidence, and the solver in TAPE is fixed per task. There is therefore little guidance on how to catch a fatal move early, and how to choose a solver per task.

Search and puzzle complexity provide the background for the evaluation. A* [13] is the standard heuristic shortest-path method, and weighted A* [18] trades plan quality for speed by inflating the heuristic. Iterative-deepening A* [19] made optimal sliding-tile solving practical, pattern databases did the same for the Rubik's cube [20], and the cube has diameter twenty [21]. Sokoban [14] and Rush Hour [15] are PSPACE-complete, which makes them hard, structured test beds. Pruning dead corners is a standard Sokoban solver technique, used here as a validator and measured, without claiming it as new. Peg Solitaire has a classical tool for proving a position lost, the pagoda function [22], [23]. AO* solves AND/OR graphs, where an action has several possible outcomes, and LAO* [24] extends it to graphs with loops. The public Boxoban level set [16] and the OR-Tools CP-SAT solver [17] are used in the experiments.

## Methodology

The methodology adds a checking and selection layer to the TAPE pipeline. All games implement one interface (actions, a step function, a goal test, a heuristic distance, and a count of independently movable pieces), so a new game plugs into the pipeline without changing it. The layer is proposer-agnostic: it takes candidate plans from any source.

### System Architecture Overview

Given the current state, the pipeline proceeds in five stages, shown in Fig. 1. The proposer returns several candidate plans. Each plan is simulated move by move, and equal states merge into one node of a plan graph. The checker judges every move and the experience store adjusts its confidence. Each remaining move receives a cost, and a solver finds the cheapest path to the goal. The path is executed, and on a mismatch between the predicted and the real state the failure is recorded and planning restarts from the real state. The proposing, merging and executing stages reproduce TAPE, and the checking and choosing stages are the additions.

![Fig. 1. The pipeline. Check (rules and experience memory) and Choose (move score, A* or CP-SAT) are the additions to TAPE. A mismatch during Run triggers a replan from the real state.](figures/pipeline.png)

### Move Validation

A validator returns, for a move from state s to s', either reject, or accept with a confidence in (0, 1]. A rejected move is never added to the graph, so any candidate plan that uses it ends there. One validator was written for each game.

For Sokoban, pushing a box into a corner that is not a goal is rejected, since it can never be recovered, and a box resting against a wall off a goal is accepted at confidence 0.5. For River Crossing, a state in which cannibals outnumber missionaries on either bank is rejected. The step function deliberately does not enforce this rule, so it lives only in the validator. For Rush Hour, a row filled entirely by horizontal vehicles that block the target is rejected, and a blocker that is itself stuck is accepted at confidence 0.5.

For Peg Solitaire the checker uses pagoda functions. A pagoda is a weight w(p) >= 0 per hole with w(a) + w(b) >= w(c) for every jump of a over b into c. A jump removes the pegs at a and b and adds one at c, so the total weight of the pegs never rises. A position whose total is below the weight of the goal, one peg in the centre, cannot win and is rejected. Twelve pagodas are obtained from a small linear programme and every inequality is re-checked after solving. For the 24-puzzle a move is rejected if the resulting arrangement is unsolvable by the inversion-parity rule. For the Rubik's cube a state is rejected if it breaks any of four cubie invariants: every slot holds a real cubie once, corner twists sum to 0 mod 3, edge flips sum to 0 mod 2, and corner and edge permutations have equal parity. The last two rules are never broken by a legal move, so they only fire on an unsolvable start.

### Experience Store

A SQLite table records successes and failures per level, state and move. Confidence is Laplace-smoothed, where s and f are the recorded successes and failures:

EQ: confidence = (s + 1) / (s + f + 2) | (1)

With no history the confidence is one, and it multiplies the validator's confidence. One recorded failure lowers trust from 1.00 to 0.33.

### Move Score

Each accepted move receives an integer cost, scaled by ten for the integer solver:

EQ: cost = 10 [ 1 + 1.5 r + 4.0 (1 - c) + 2.0 (t / T)^2 ] | (2)

where r = max(0, h(s') - h(s)) is how much the move increases the heuristic distance to the goal, c is the confidence, and t / T is the share of the step budget used. The weights are defaults; Section V-C tests whether tuning improves them.

### Adaptive Path Selection and Replanning

Path selection is A* with the same cost when the state has one independently movable piece, such as a single Sokoban box or the River Crossing boat, and CP-SAT when it has several, such as several boxes or vehicles whose routes can conflict. The chosen path is executed move by move. On a mismatch the failure is recorded in the experience store and planning restarts from the real state, up to a replan limit.

## Performance Measure and Evaluation

The evaluation asks which of the additions change the outcome, on which games, and by how much. Every experiment is a controlled comparison in which only the studied component differs.

### Benchmarks

Seven games share the interface. Sokoban has four hand-made levels with one to three boxes, the hardest with a 29-move optimum. River Crossing has three missionary-cannibal pairs and a two-seat boat, with an 11-move optimum. Rush Hour is a six-move board. Boxoban [16] contributes one file from each difficulty set (unfiltered, medium and hard), 1,000 ten-by-ten levels with four boxes each, 3,000 levels in total. Three harder games are added: Peg Solitaire on the English board (about 3.6 million reachable positions), the 24-puzzle (about 7.8 x 10^24 states) and the 3x3x3 Rubik's cube (about 4.3 x 10^19 states).

### Plan Proposers

No language model is used. A goal-biased proposer returns one breadth-first-search plan plus noisy walks, so its absolute success rates are optimistic. An adversarial proposer returns uniformly random moves. A quality proposer mixes guided and random walks, or takes an optimal plan and randomizes each step with probability one minus the quality. A weighted A* proposer runs under a per-search node budget and is used for Boxoban, Peg Solitaire and the 24-puzzle. A meet-in-the-middle proposer searches from the start and from the solved state at once and is used for the cube. Plain BFS and DFS proposers are used in Section V-G.

### Metrics

Safe success means the goal is reached and no executed move is rejected by an independent domain auditor, whether or not the configuration used a validator. This matters because plain success hides rule-breaking in games such as River Crossing, whose step function does not enforce its rules. Replans per episode, planning time, and, for Boxoban, the share of levels solved within a node budget are also reported.

### Statistical Treatment

Proportions carry 95% Wilson intervals. Paired comparisons report the mean difference and its standard error over seeds, with identical failures and seeds in both arms. The weight search is fitted on training seeds and checked on unseen seeds.

### Evaluation Scope

The evaluation measures system-level behavior on synthetic proposers. It does not use a language model and cannot be compared with the numbers reported for TAPE, whose benchmarks ALFWorld, MuSiQue and GSM8K-Hard require one.

## Results and Discussion

A summary of the main measurements is presented in Table 1. The sections below give the experiments behind each row, including the ones where the extensions did not help.

TABLE: SUMMARY OF KEY RESULTS
| Measurement | Without | With |
|---|---|---|
| River Crossing, safe success | 0% | 100% |
| Planning time, one-box Sokoban (ms) | 51.8 | 7.6 |
| Boxoban hard set, solved at 30k nodes | 54% | 82% |
| Peg Solitaire start, nodes to a plan | 139,048 | 82,009 |
| Peg Solitaire start, A* against DFS (nodes) | 139,048 | 10,845 |
| Replans, one-box Sokoban (change) | 0 | -0.56 |

### Safety and Speed

Five configurations were compared: the baseline, with the validator, with the validator and the experience store, with adaptive selection, and with everything. They ran on six benchmarks, 30 episodes per cell, with a 15% slip probability and the goal-biased proposer. On River Crossing the baseline reaches the goal in every episode but never safely: safe success is 0%, and with the validator it is 100% while raw success is unchanged. The validator converts unsafe successes into safe ones. Adaptive selection saves time where one piece moves and ties elsewhere, with identical success and action counts, as Table 2 shows. Hard Sokoban stays near 53% in every configuration, so none of the extensions changes it.

TABLE: PLANNING TIME PER EPISODE (MS)
| Benchmark | Always CP-SAT | Adaptive |
|---|---|---|
| Sokoban, one box | 51.8 | 7.6 |
| River Crossing | 62.1 | 3.6 |
| Sokoban, two boxes | 99.9 | 96.4 |
| Rush Hour | 36.2 | 36.1 |

### Experience Store Under State-Dependent Failure

With uniform random slips the store gave no benefit, since there is nothing state-dependent to learn. Therefore 25% of the state and move pairs were made to slip with probability 0.7, and validator-only was compared with validator plus store, paired over 20 hazard seeds of 30 episodes (Table 3). The store reduces replans by roughly 14% on two games and does nothing on the others. A possible reason, not tested here, is that with more routes the candidates rarely contain a detour around a learned hazard, and the store can only reweight edges already in the graph.

TABLE: EXPERIENCE STORE UNDER STATE-DEPENDENT SLIP
| Benchmark | Replans (late) | Success |
|---|---|---|
| Sokoban, one box | -0.56 +/- 0.18 | +5.5 pts |
| River Crossing | -0.54 +/- 0.15 | +5.0 pts |
| Rush Hour | -0.17 +/- 0.11 | +1.2 pts |
| Sokoban, two boxes | +0.06 +/- 0.03 | -0.2 pts |

### Tuning the Score Weights

Eighty combinations of the three penalty weights were searched on 8 training seeds, and the top three and the defaults were re-run on 16 unseen seeds. The objective was replans plus three times the failure rate, averaged over four benchmarks. The best training point had objective 3.906 against 4.219 for the defaults, which ranked 23rd of 80, but it was worse on held-out seeds (+0.122 +/- 0.111). No candidate beat the defaults by more than one standard error. The defaults are kept; this is a null result, not proof that they are optimal.

### Proposer Quality

To see how much the layer helps as proposer quality changes, the baseline was compared with the full layer under the state-dependent failure model. A proposer built only from random and guided walks hit a floor (at most 17% success on the easiest non-trivial level) and was uninformative. With a proposer that corrupts an optimal plan, the extra layers barely change the goal-reach rate on Sokoban and Rush Hour: almost every paired difference is within two standard errors of zero. River Crossing stays at 0% safe success in both arms, because this proposer never learns the safety rule, so its optimal plan is the unsafe one and the validator correctly rejects it. The validator does cut replans by 2.7 to 3.4 per episode at quality 0.7 and above. A validator filters proposals; it does not create them.

### Boxoban

Solve rate is the share of 1,000 levels per set for which any of four searches finds a plan within the node budget. Without pruning the search is unaware of dead corners, and with the checker it prunes them (Fig. 2, Table 4). The checker wins in all 15 cells, the 95% intervals do not overlap in any of them, and pruning never missed a level that no-pruning solved. The gain grows with difficulty: at 10,000 nodes it is 8, 19 and 22 points, and at 30,000 nodes 3, 17 and 28 points. The checker also expands 20%, 25% and 23% fewer nodes per level at the full budget. Merging plans did not shorten paths: the merged path was shorter than the best single plan on one level in total and longer on 19, 9 and 5 levels across the three sets, because the solver minimizes the cost of Section III-D, not move count.

![Fig. 2. Boxoban: share of 1,000 levels solved against the node budget, with the corner checker (solid) and without pruning (dashed).](figures/boxoban.png)

TABLE: BOXOBAN LEVELS SOLVED (%), NO PRUNING / CHECKER
| Nodes | Unfiltered | Medium | Hard |
|---|---|---|---|
| 2,000 | 57 / 65 | 14 / 23 | 6 / 13 |
| 5,000 | 73 / 82 | 29 / 45 | 16 / 29 |
| 10,000 | 84 / 92 | 46 / 65 | 27 / 49 |
| 20,000 | 92 / 96 | 61 / 82 | 44 / 70 |
| 30,000 | 95 / 98 | 71 / 88 | 54 / 82 |

### Harder Games

Peg Solitaire is the one game where the checker helps during play. A test confirms by exhaustive search that every sampled position the pagoda checker rejects is truly unsolvable. From the real start the checker cuts the search from 139,048 to 82,009 nodes, 41% fewer. On positions built by playing jumps backwards from the goal, so each is solvable, within 60,000 nodes it solves 98% against 93% at 22 jumps and 75% against 58% at 26 jumps, using 19 to 31% fewer nodes, and it never lost a position the plain search solved (Fig. 3, Table 5).

![Fig. 3. Peg Solitaire on positions built backwards from the goal: share solved (top) and mean nodes per search (bottom, log scale).](figures/peg.png)

TABLE: PEG SOLITAIRE, SOLVED (%) AND MEAN NODES
| Jumps | No checker | Checker | Nodes (no / with) |
|---|---|---|---|
| 12 | 100 | 100 | 296 / 237 |
| 18 | 100 | 100 | 2,776 / 1,914 |
| 22 | 93 | 98 | 13,780 / 9,663 |
| 26 | 58 | 75 | 39,170 / 31,817 |

For the 24-puzzle and the Rubik's cube the parity rule and the cubie invariants change no result on a solvable start, which was verified. They guard the input: on an unsolvable start, with two tiles swapped or one corner twisted, the plain search spends its whole budget of 60,000 and 400,000 nodes, and the check stops it after at most one node. Weighted A* solves random-walk scrambles of the 24-puzzle 100%, 95%, 73% and 57% of the time at 20, 40, 60 and 80 moves, and the meet-in-the-middle search solves every cube scramble of 4 to 8 moves. For these two games the checker is a start gate, not a planning improvement.

### Search Methods

BFS, DFS, weighted A* and meet in the middle were compared on every game each can run on, with no checkers so that only the algorithm differs (budget 100,000 nodes; one instance for the small games, 20 for the rest). The result is summarized in Table 6 and Fig. 4; each cell is the percentage solved and the mean nodes, with k for thousands.

TABLE: SEARCH METHODS: SOLVED (%) AND MEAN NODES
@search_table

![Fig. 4. Share of instances solved within 100,000 nodes, by search method.](figures/search_methods.png)

Depth-first search helps in one game, by a wide margin. Every Peg Solitaire solution is exactly 31 jumps, so a depth-first search that never revisits a state loses nothing. From the real start it needs 10,845 nodes, against 139,048 for weighted A*, while BFS finds nothing in 400,000. With the pagoda checker pruning, DFS needs 6,455. On positions 22 jumps from the goal, weighted A* is slightly better (95% against 85%). BFS helps only where the state space is tiny, and is the only method that always returns a shortest plan. Weighted A* is the best general choice; DFS finds Boxoban plans about 2.5 times longer. Meet in the middle guarantees a shortest plan but used more nodes than A* on short cube scrambles and ran out on the 40-move 24-puzzle.

AO* does not help here. It plans over graphs where an action can have several outcomes. Every game in this work is deterministic, so its graph has no AND nodes and AO* reduces to A*. It could matter for the slip model, where a move sometimes does nothing, but the slip returns to the same state and creates a loop, for which the relevant algorithm is LAO* [24]. It was not implemented. Node counts are expansions for BFS, DFS and A* and generated states for meet in the middle, so they should be compared loosely.

### Integrated Interpretation

The value of the layer depends on the proposer. Where the environment allows moves that are legal but forbidden by a rule, checking is decisive: River Crossing goes from 0% to 100% safe. Used as a pruner inside a search, the same idea solves substantially more real Boxoban levels within a fixed budget, and more so on harder sets. Adaptive selection is a plain efficiency gain. Failure memory helps only when failures are state-dependent and the candidates contain an alternative. On the harder games the checker is a different tool: for Peg Solitaire it is a proof that prunes during play, and for the 24-puzzle and the cube it stops an unsolvable start from consuming the search budget. Among search methods no single one dominates. When the proposer is already competent, the layer does not raise the goal-reach rate; its contribution is safety and fewer wasted replans.

### Limitations and Threats to Validity

There are some limitations to consider. First, the proposers are synthetic and no language model was used, so the results say nothing about real model failures. The goal-biased proposer plants a breadth-first plan, which inflates absolute success rates in Sections V-A and V-B, although the paired comparisons are less affected. Second, corner pruning is standard in Sokoban solvers, so Section V-E shows that the validator works as that pruner on external levels, not that pruning is new. Third, coverage is limited: one file per Boxoban set, one checker rule, and hand-made levels elsewhere. The harder games use random-walk scrambles, easier than uniformly random instances, and the cube is tested only to 8-move scrambles. Fourth, the numbers cannot be compared with TAPE's, since its benchmarks need a language model. Fifth, the weight search used 8 training seeds, so its ranking is noisy, and the search comparison has small instance counts and non-optimal plans from weighted A*. Last, merged paths were not shorter than the best single plan, so no claim is made that graph merging improves plan quality in these settings.

## Future Scope

The framework provides a base for several extensions. As an immediate next step, a learned proposer, such as an imitation or reinforcement-learning policy, would give more realistic proposer errors than the synthetic ones used here (**[TODO]** confirm with the guide whether learned models are allowed). A second Sokoban rule, such as frozen boxes, and the remaining Boxoban files would show whether the gain grows. The slip model could be planned for, rather than replanned after, with an AND/OR search that handles loops such as LAO*. The same checking layer could be tested on benchmarks such as ALFWorld, MuSiQue and GSM8K-Hard once a language model proposer is allowed, which would also allow a direct comparison with TAPE. Finally, a written soundness argument for each validator, and stronger classical baselines such as a standard planner, would strengthen the claims.

## Conclusion

A validation and adaptive-selection layer was built on the TAPE pipeline and evaluated on seven games without any language model. Rule checking made plans safe and made search solve more real levels, choosing the solver per task saved planning time, and failure memory reduced replans when failures depend on the state. A comparison of search methods found that depth-first search suits Peg Solitaire and weighted A* suits the rest, and that AO* does not apply to deterministic games. The framework does not claim to raise the goal-reach rate of a competent proposer; its contribution is safety, fewer wasted replans, and earlier detection of positions that cannot be won. Several hoped-for effects did not appear, and they are reported with the rest. Collectively, these results support a proposer-agnostic checking layer as a practical addition to plan-graph planners, to be validated further with learned proposers.

## References

[1] J. Jeong, J. Kim, and K. Lee, "TAPE: Tool-guided adaptive planning and constrained execution in language model agents," *arXiv preprint* arXiv:2602.19633, 2026.
[2] S. Yao *et al.*, "ReAct: Synergizing reasoning and acting in language models," *arXiv preprint* arXiv:2210.03629, 2022.
[3] S. Yao *et al.*, "Tree of thoughts: Deliberate problem solving with large language models," *arXiv preprint* arXiv:2305.10601, 2023.
[4] M. Besta *et al.*, "Graph of thoughts: Solving elaborate problems with large language models," *arXiv preprint* arXiv:2308.09687, 2023.
[5] N. Shinn *et al.*, "Reflexion: Language agents with verbal reinforcement learning," *arXiv preprint* arXiv:2303.11366, 2023.
[6] T. Schick *et al.*, "Toolformer: Language models can teach themselves to use tools," *arXiv preprint* arXiv:2302.04761, 2023.
[7] J. Wei *et al.*, "Chain-of-thought prompting elicits reasoning in large language models," *arXiv preprint* arXiv:2201.11903, 2022.
[8] L. Wang *et al.*, "Plan-and-solve prompting: Improving zero-shot chain-of-thought reasoning by large language models," *arXiv preprint* arXiv:2305.04091, 2023.
[9] B. Xu *et al.*, "ReWOO: Decoupling reasoning from observations for efficient augmented language models," *arXiv preprint* arXiv:2305.18323, 2023.
[10] M. Shridhar *et al.*, "ALFWorld: Aligning text and embodied environments for interactive learning," *arXiv preprint* arXiv:2010.03768, 2020.
[11] H. Trivedi, N. Balasubramanian, T. Khot, and A. Sabharwal, "MuSiQue: Multihop questions via single-hop question composition," *arXiv preprint* arXiv:2108.00573, 2021.
[12] K. Cobbe *et al.*, "Training verifiers to solve math word problems," *arXiv preprint* arXiv:2110.14168, 2021.
[13] P. E. Hart, N. J. Nilsson, and B. Raphael, "A formal basis for the heuristic determination of minimum cost paths," *IEEE Transactions on Systems Science and Cybernetics*, 1968.
[14] J. Culberson, "Sokoban is PSPACE-complete," Tech. Rep. TR97-02, University of Alberta, 1997.
[15] G. W. Flake and E. B. Baum, "Rush Hour is PSPACE-complete, or why you should generously tip parking lot attendants," *Theoretical Computer Science*, vol. 270, no. 1-2, pp. 895-911, 2002.
[16] DeepMind, "Boxoban levels," github.com/google-deepmind/boxoban-levels.
[17] L. Perron and V. Furnon, "OR-Tools," Google, developers.google.com/optimization.
[18] I. Pohl, "Heuristic search viewed as path finding in a graph," *Artificial Intelligence*, vol. 1, no. 3-4, pp. 193-204, 1970.
[19] R. E. Korf, "Depth-first iterative-deepening: An optimal admissible tree search," *Artificial Intelligence*, vol. 27, no. 1, pp. 97-109, 1985.
[20] R. E. Korf, "Finding optimal solutions to Rubik's Cube using pattern databases," in *Proc. AAAI-97*, 1997, pp. 700-705.
[21] T. Rokicki, H. Kociemba, M. Davidson, and J. Dethridge, "The diameter of the Rubik's Cube group is twenty," *SIAM Journal on Discrete Mathematics*, vol. 27, no. 2, pp. 1082-1105, 2013.
[22] J. D. Beasley, *The Ins and Outs of Peg Solitaire*. Oxford University Press, 1985.
[23] E. R. Berlekamp, J. H. Conway, and R. K. Guy, *Winning Ways for your Mathematical Plays*. Academic Press, 1982.
[24] E. A. Hansen and S. Zilberstein, "LAO\*: A heuristic search algorithm that finds solutions with loops," *Artificial Intelligence*, vol. 129, no. 1-2, pp. 35-62, 2001.
