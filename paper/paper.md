# Rule Checking and Adaptive Solver Choice for Plan-Graph Planning

> Builder note, not part of the paper. paper.docx is generated from this file by build_paper_docx.py. Fig. 1 is drawn natively by the builder on a Word canvas. Every number below was copied from a file in results/.

## Abstract

TAPE merges several candidate plans into one graph and lets a solver choose the path. It never checks a move against the rules of the task, and the solver is the same for every problem. We added a rule checker for each game, a store of past move failures, and a cost rule that sends one-piece problems to A* and the rest to CP-SAT. The system contains no language model, since our guide ruled that out. On River Crossing the checker moved safe success from 0% to 100%. On 3,000 Boxoban levels it solved more levels at every node budget, reaching 82% on the hard set at 30,000 nodes against 54% without it. Using A* for single-piece games cut planning time on one-box Sokoban from 51.8 ms to 7.6 ms, and the failure store reduced replans on two of four games. We then added Peg Solitaire, the 24-puzzle and the Rubik's cube as harder tests. On the Peg Solitaire start, plain depth-first search needed 10,845 nodes where weighted A* needed 139,048. Tuning the cost weights and merging plans gave no gain.

Keywords: plan graph, rule validation, solver selection, A* search, constraint programming, puzzle benchmarks, safe planning.

## Introduction

TAPE [1] asks a language model for several plans, merges the states they share into a graph, and has an integer program pick the cheapest path. If the world disagrees with a prediction, it plans again from the real state. Its authors name two limits. The graph is only as good as the plans behind it, and the solver is fixed in advance.

Three small cases show what the first limit costs. In River Crossing a plan can reach the far bank after leaving more cannibals than missionaries on one side, and because our environment accepts every move, a pipeline that checks only legality reports success. In Sokoban one push into a corner ends the level, but the pipeline learns this only when the search returns nothing. In Rush Hour two stuck vehicles can seal a row for good. In all three a short rule check would have caught the problem before any search effort was spent.

We therefore put a checker for each game in front of the solver, gave the pipeline a memory of failed moves, and let the piece count decide between A* and CP-SAT. Four questions follow. Does the checker change outcomes? Does the memory reduce replans? Does choosing the solver save time? And would a better search method have done more than any of these? We answer them on seven games with proposers that are ordinary programs. Runs repeat exactly from a seed, and we can set how good the candidate plans are, which a language model would not allow.

## Literature Review

Agent work with language models splits into three groups that differ in where the plan comes from. ReAct [2] interleaves reasoning with tool calls, Reflexion [5] adds a written memory of past failures, and Toolformer [6] teaches a model when to call a tool. Tree of Thoughts [3] and Graph of Thoughts [4] search over reasoning steps instead; the graph version lets branches merge. Chain-of-thought [7], Plan-and-Solve [8] and ReWOO [9] fix the plan before acting. TAPE [1] sits between these: it merges plans into a graph and gives path choice to an external solver. Its tests were Sokoban, ALFWorld [10], MuSiQue [11] and GSM8K-Hard, which is derived from GSM8K [12].

All of these judge a plan by running it or by asking a model. None tests a step against a rule that the task's designer wrote down. Reflexion's memory is prose, so it cannot change the price of one particular move, and TAPE trusts every move it is shown. That is the gap we work on.

The search side is older. Weighted A* [18] trades plan length for speed. Iterative deepening [19] made optimal sliding-tile solving practical, pattern databases did the same for the cube [20], and the cube's diameter is twenty moves [21]. Sokoban [14] and Rush Hour [15] are PSPACE-complete. Dead-corner pruning is routine in Sokoban solvers, so we measure it as a baseline and do not claim it. Peg Solitaire has pagoda functions [22], [23], which we use as a checker. AO* handles actions with several outcomes and LAO* [24] handles loops among them; Section V-G explains why we did not need either. Levels come from the public Boxoban set [16] and the solver is OR-Tools CP-SAT [17].

## Methodology

Every game implements the same interface: a list of actions, a step function that returns the next state and whether the move was legal, a goal test, a heuristic distance, a count of independently movable pieces, and a text renderer. The rest of the pipeline never learns which game it is running. Adding a game means writing that interface and one checker.

### System architecture

Fig. 1 shows one planning round. The proposer returns candidate plans from the current state. Each plan is replayed move by move and identical states are merged into one node of a directed graph. The checker then judges every move and the experience store adjusts its confidence. Surviving moves get a cost, and the solver finds the cheapest path from the current state to a goal. The path is executed. When a move lands somewhere other than predicted, the failure is recorded and a new round starts from the real state. Proposing, merging and executing come from TAPE. Checking and the choice of solver by cost are ours.

![Fig. 1. One planning round. The shaded stages are our additions to TAPE. A move that does not land where predicted sends control back to the proposer, starting from the real state.](canvas:pipeline)

### Move validation

For a move from state s to state s', a validator either rejects it or accepts it with a confidence between 0 and 1. A rejected move never becomes an edge, so any plan containing it ends there. Each game has its own validator.

In Sokoban a push that leaves a box in a non-goal corner is rejected, since that box can never move again. A box against a wall away from any goal is accepted at confidence 0.5. In River Crossing a bank with more cannibals than missionaries, while a missionary is still there, is rejected. The step function allows such states on purpose, so the validator is the only place the rule lives. In Rush Hour a row completely filled by horizontal vehicles that blocks the target is rejected, and a blocker that is itself stuck is accepted at 0.5.

Peg Solitaire needed a proof tool. A pagoda function gives each hole a weight w(p) >= 0 such that w(a) + w(b) >= w(c) for every jump from a over b into c. A jump removes the pegs on a and b and adds one on c, so the total weight of the board cannot rise. A position already lighter than the goal, a single peg in the centre, can never reach it. A small linear program gives twelve pagodas, and we recheck every inequality after solving. For the 24-puzzle a move is rejected if its result is unsolvable by the inversion-parity rule. For the cube we reject a state that breaks one of four cubie invariants: each slot holds a real cubie once, corner twists sum to 0 mod 3, edge flips sum to 0 mod 2, and corner and edge permutations have equal parity. Legal moves never break the last two, so on these two games the checker only matters when the start itself is unsolvable.

### Experience store

A SQLite table counts successes s and failures f for each level, state and move. The count is Laplace-smoothed, so one early failure does not drive trust to zero:

EQ: confidence = (s + 1) / (s + f + 2) | (1)

A move with no history has confidence 1, and one recorded failure lowers it to 0.33. The value is multiplied by the validator's confidence.

### Move score

CP-SAT needs integer coefficients, so each accepted move gets an integer cost scaled by ten:

EQ: cost = 10 [ 1 + 1.5 r + 4.0 (1 - c) + 2.0 (t / T)^2 ] | (2)

Here r = max(0, h(s') - h(s)) is how much the move worsens the heuristic distance, c is the confidence, and t / T is the share of the step budget already used. The weights 1.5, 4.0 and 2.0 were our first guess. Section V-C describes the attempt to improve them.

### Path selection and replanning

With one independent piece, such as one Sokoban box or the River Crossing boat, the problem is a plain shortest path and we run A* on the cost above. With several pieces whose routes can interfere, we write the path as a one-unit flow and solve it with CP-SAT. The path is executed move by move. After a mismatch the failure goes into the store and we plan again from the real state, up to a fixed number of replans.

## Performance Measure and Evaluation

Each experiment changes one component and keeps the others fixed.

### Benchmarks

Sokoban has four hand-made levels with one to three boxes; the hardest has a 29-move optimum. River Crossing has three missionary and cannibal pairs and a two-seat boat, with an 11-move optimum. Rush Hour is a six-by-six board solved in six moves. From Boxoban [16] we take one file for each of its three difficulty sets (unfiltered, medium, hard), each holding 1,000 ten-by-ten levels with four boxes. Peg Solitaire is the English board with about 3.6 million reachable positions. The 24-puzzle has about 7.8 x 10^24 states and the 3x3x3 cube about 4.3 x 10^19.

### Plan proposers

Our first proposer hid a BFS shortest plan among noisy walks. On River Crossing that plan has nine moves and passes through unsafe states, because the step function allows them, so we made the hidden plan consult the validator. It then becomes the textbook 11-move answer. The adversarial proposer returns uniformly random moves. A quality proposer either mixes guided and random walks, or takes an optimal plan and randomizes each step with a set probability. Boxoban, Peg Solitaire and the 24-puzzle use weighted A* under a node budget, and the cube uses a search that grows from both the start and the solved cube until the two meet. Section V-G adds plain BFS and DFS.

### Metrics and statistics

An episode counts as a safe success when it reaches the goal and an independent auditor rejects none of the executed moves. The auditor applies the game's rules whatever configuration is being tested. Plain success would give River Crossing's baseline 100% although it breaks the rule in every episode. We also record replans per episode, planning time and, for Boxoban, the share of levels solved within a node budget. Proportions carry 95% Wilson intervals. Paired comparisons use identical hazards and seeds in both arms and give the mean difference with its standard error. The weight search was fitted on training seeds and then judged on seeds it had not seen.

## Results and Discussion

TABLE: SUMMARY OF RESULTS
| Measurement | Without | With |
|---|---|---|
| River Crossing, safe success | 0% | 100% |
| Planning time, one-box Sokoban (ms) | 51.8 | 7.6 |
| Boxoban hard set, solved at 30k nodes | 54% | 82% |
| Peg Solitaire start, nodes to a plan | 139,048 | 82,009 |
| Peg Solitaire start, A* against DFS (nodes) | 139,048 | 10,845 |
| Replans, one-box Sokoban (change) | 0 | -0.56 |

### Safety and speed

Table I lists the headline numbers. The first experiment ran five configurations on six benchmarks, 30 episodes per cell, with a 15% slip probability and the goal-biased proposer. The configurations were the baseline, validator only, validator plus store, adaptive selection only, and everything together. The baseline reaches the River Crossing goal every time and never does so safely. With the validator, safe success is 100% and raw success is unchanged. Adaptive selection saves time only where one piece moves (Table II), and leaves success and action counts identical. Hard Sokoban stayed near 53% in all five configurations.

TABLE: PLANNING TIME PER EPISODE (MS)
| Benchmark | Always CP-SAT | Adaptive |
|---|---|---|
| Sokoban, one box | 51.8 | 7.6 |
| River Crossing | 62.1 | 3.6 |
| Sokoban, two boxes | 99.9 | 96.4 |
| Rush Hour | 36.2 | 36.1 |

### Experience store under state-dependent failure

Under uniform random slips the store has nothing to learn, and it changed nothing. We then made 25% of the state and move pairs slip with probability 0.7, and compared validator only with validator plus store over 20 hazard seeds of 30 episodes each (Table III). Late-episode replans fell by about 14% on one-box Sokoban and River Crossing. Rush Hour did not separate from zero and two-box Sokoban did not change. We did not investigate why. Two-box levels have many routes and the 30 candidate plans may rarely contain a detour around a learned hazard, but we have not checked that. The store can only reweight edges already in the graph.

TABLE: EXPERIENCE STORE UNDER STATE-DEPENDENT SLIP
| Benchmark | Replans (late) | Success |
|---|---|---|
| Sokoban, one box | -0.56 +/- 0.18 | +5.5 pts |
| River Crossing | -0.54 +/- 0.15 | +5.0 pts |
| Rush Hour | -0.17 +/- 0.11 | +1.2 pts |
| Sokoban, two boxes | +0.06 +/- 0.03 | -0.2 pts |

### Tuning the score weights

We expected this to help. A search over 80 combinations of the three penalty weights on 8 training seeds found a best point scoring 3.906, against 4.219 for our defaults, which ranked 23rd. The objective was replans plus three times the failure rate, averaged over four benchmarks. We reran the top three and the defaults on 16 unseen seeds. The best training point came out worse than the defaults by 0.122 +/- 0.111, and nothing beat them by more than one standard error. We kept the defaults. This says the search found nothing better, and does not make them optimal.

### Proposer quality

The proposer built only from random and guided walks barely solved the easiest non-trivial level, 17% at best, so it taught us little. A proposer that corrupts an optimal plan was more useful. With it, the full layer and the baseline differed by less than two standard errors on almost every Sokoban and Rush Hour comparison. River Crossing stayed at 0% safe success in both arms, because this proposer never learns the safety rule and its best plan is the unsafe one, which the validator correctly rejects. The validator did remove 2.7 to 3.4 replans per episode at quality 0.7 and above. It discards bad plans but cannot supply a good one the proposer never produced.

### Boxoban

A level counts as solved if any of four searches finds a plan within the node budget. Without pruning the search knows nothing about dead corners. With the checker it skips them (Fig. 2, Table IV). The checker was ahead in all 15 combinations of set and budget, with non-overlapping 95% intervals, and never lost a level the unpruned search solved. The gap grows with difficulty. At 10,000 nodes it is 8, 19 and 22 points on the three sets, and at 30,000 nodes it is 3, 17 and 28. At the full budget the checker expands 20%, 25% and 23% fewer nodes per level. Merging plans did not shorten paths. Of 2,680 solved levels the merged path beat the best single plan on one and lost to it on 33, since the solver minimizes the cost in Eq. (2) and not the number of moves.

![Fig. 2. Boxoban levels solved out of 1,000 against the node budget, with the corner checker (solid lines) and without pruning (dashed).](figures/boxoban.png)

TABLE: BOXOBAN LEVELS SOLVED (%), NO PRUNING / CHECKER
| Nodes | Unfiltered | Medium | Hard |
|---|---|---|---|
| 2,000 | 57 / 65 | 14 / 23 | 6 / 13 |
| 5,000 | 73 / 82 | 29 / 45 | 16 / 29 |
| 10,000 | 84 / 92 | 46 / 65 | 27 / 49 |
| 20,000 | 92 / 96 | 61 / 82 | 44 / 70 |
| 30,000 | 95 / 98 | 71 / 88 | 54 / 82 |

### Harder games

Peg Solitaire is the one game where the checker helps during play. To test soundness we took positions the pagoda checker rejects and tried to prove each one unsolvable by exhaustive search. None was solvable. From the real start position the checker cut the search from 139,048 to 82,009 nodes, 41% fewer. Our first benchmark used positions reached by random play, and it failed. Most positions were out of reach inside the budget, the search could not say whether they were lost, and the two arms looked identical. We rebuilt the set by playing jumps backwards from the goal, which guarantees every position is solvable. Within 60,000 nodes the checker then solved 98% of positions 22 jumps out against 93% without it, and 75% against 58% at 26 jumps, with 19 to 31% fewer nodes (Fig. 3, Table V). It never lost a position the plain search solved.

![Fig. 3. Peg Solitaire on positions built backwards from the goal. Top, share solved. Bottom, mean nodes per search on a log scale.](figures/peg.png)

TABLE: PEG SOLITAIRE, SOLVED (%) AND MEAN NODES
| Jumps | No checker | Checker | Nodes (no / with) |
|---|---|---|---|
| 12 | 100 | 100 | 296 / 237 |
| 18 | 100 | 100 | 2,776 / 1,914 |
| 22 | 93 | 98 | 13,780 / 9,663 |
| 26 | 58 | 75 | 39,170 / 31,817 |

The 24-puzzle and the cube behave differently. Legal moves never break the parity rule or the cubie invariants, and the checks changed no result on a solvable start. They matter only when the input itself is unsolvable. With two tiles swapped, or one cube corner twisted, the plain search spent its entire budget (60,000 and 400,000 nodes) and the check stopped it after at most one. Weighted A* solved random-walk scrambles of the 24-puzzle at 100%, 95%, 73% and 57% for 20, 40, 60 and 80 moves, and meet in the middle solved every cube scramble of 4 to 8 moves.

### Search methods

We ran BFS, DFS, weighted A* and meet in the middle on every game each can handle, without checkers, at 100,000 nodes. The small games have one instance each and the others have 20 (Table VI, Fig. 4).

TABLE: SEARCH METHODS: SOLVED (%) AND MEAN NODES
@search_table

![Fig. 4. Share of instances solved within 100,000 nodes, by search method.](figures/search_methods.png)

DFS won one game by a wide margin. Every Peg Solitaire solution has exactly 31 jumps, so a depth-first search that never revisits a state loses nothing. From the real start it needed 10,845 nodes, or 6,455 with the pagoda checker. Weighted A* needed 139,048, and BFS found no plan in 400,000. On one position that weighted A* could not solve in 20,000 nodes, DFS needed about 10,800. The order reversed on positions 22 jumps from the goal, where weighted A* solved 95% and DFS 85%. BFS was enough only for River Crossing and Rush Hour, where it also returns the shortest plan. Weighted A* was the best general choice, though DFS plans on Boxoban came out about 2.5 times longer. Meet in the middle guarantees a shortest plan, but on short cube scrambles it used more nodes than A* with our sticker-count heuristic, and on the 40-move 24-puzzle it ran out of budget.

We did not implement AO*. It plans over actions with several outcomes, our games are deterministic, and without AND nodes it reduces to A*. It could matter for the slip model, where a move sometimes leaves the state unchanged. That outcome loops back to the same state, which is what LAO* [24] was designed for. One caution on the table: node counts are expansions for BFS, DFS and A*, but generated states for meet in the middle, so that column compares only roughly.

### Limitations

We never tried a language model, so we say nothing about how real model errors behave. The goal-biased proposer hides a BFS plan, which pushes the absolute success rates in Sections V-A and V-B above what a real proposer would reach; the paired differences are less affected. Dead-corner pruning is standard in Sokoban solvers, so Section V-E shows only that our validator works as that pruner on levels we did not write. Boxoban coverage is one file per set and one rule. Our harder-game scrambles are random walks, which are easier than uniformly random instances, and we tested the cube only up to 8 moves. TAPE's own numbers cannot be reproduced without a language model, so we make no direct comparison with it. The weight search used 8 training seeds, which makes its ranking noisy, and the small games in the search comparison have one instance. Weighted A* does not return optimal plans, so a lower node count may come with a longer plan.

## Future Scope

The test we most want is a learned proposer. We would train a policy by imitation on the Boxoban solutions we already have, then see whether checker pruning still saves nodes when the proposals contain realistic mistakes. A second Sokoban rule such as frozen boxes would show whether the Boxoban gain keeps growing as rules are added, measured as levels solved at 10,000 nodes. The slip model could be handled with LAO* and compared with replan-on-mismatch on expected replans. Each validator also needs a soundness argument like the one we gave informally for the pagoda bound.

## Conclusion

The checker paid off where the environment permitted illegal moves, or where pruning stopped a search from exploring dead branches: River Crossing, Boxoban and Peg Solitaire. It made no difference on proposers that already produced good plans. Choosing the solver by piece count saved time only on single-piece problems. Weight tuning and plan merging, both of which we expected to help, did not. The largest single gain on Peg Solitaire came from changing the search, not the checker: depth-first search with the pagoda checker solved the real start in 6,455 nodes, where weighted A* needed 139,048. The next step is to test all of this with a proposer that makes realistic mistakes.

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
