# A Validation and Adaptive-Selection Layer for Plan-Graph Planning

> **Format.** The Word version (`paper/paper.docx`) follows the ICCISD two-column IEEE template and is generated from this file by `paper/build_paper_docx.py`; figures come from `paper/make_figures.py`. Every number comes from a file in `results/`. Section numbers and subsection letters are added by the builder.

## Abstract

TAPE plans by merging several candidate plans into one graph and letting a solver pick a path through it. It does not test a move against the rules of the task before trusting it, and it uses the same solver for every problem. We add a layer with three parts: a rule checker for each game that rejects or downweights moves, a store of past failures that adjusts how far each move is trusted, and a selection rule that picks A* or a constraint solver by the number of movable pieces. No language model is involved. We test the layer on seven games: Sokoban, River Crossing, Rush Hour, Peg Solitaire, the 24-puzzle, the Rubik's cube and 3,000 public Boxoban levels. On River Crossing the checker takes safe success from 0% to 100%. Used to prune a search, it raises the share of Boxoban levels solved at every node budget in all three difficulty sets, for example from 54% to 82% on the hard set at 30,000 nodes. Choosing A* for single-piece games cut planning time on one-box Sokoban from 52 ms to 8 ms, and remembering failures reduced replans on two of four games. Depth-first search needed thirteen times fewer nodes than weighted A* on Peg Solitaire, and AO* turned out not to apply to our deterministic games. Tuning the cost weights found nothing better than our defaults, and merging plans never produced a shorter path.

Keywords: plan graph, rule validation, adaptive solver selection, A* search, constraint programming, puzzle benchmarks, safe planning.

## Introduction

A plan that looks fine on paper can fail at the first move that breaks a rule. TAPE [1] tries to avoid this by asking for several candidate plans, merging the states they share into one graph, and letting an integer-programming solver pick the cheapest feasible path. If the world then differs from the prediction, it plans again from the real state. Its authors name two limits: the graph is only as good as the plans that built it, and the solver is chosen in advance.

We looked at what those limits mean in small puzzles where the rules are exact. In River Crossing a plan can reach the far bank after leaving the missionaries outnumbered on the way, and because the environment accepts every move, a pipeline that checks only legality reports success. In Sokoban one push into a corner ends the game, but the pipeline learns this only when the search comes back empty. In Rush Hour two stuck vehicles can seal a row. In each case a short rule check would have caught the problem before any search effort was spent.

This paper adds four pieces to the pipeline and tests them on seven games. A rule checker for each game rejects forbidden moves and lowers confidence in suspicious ones. An experience store remembers which moves failed in earlier episodes. A cost function combines progress toward the goal, confidence and the remaining step budget into one number per move. A selection rule sends single-piece problems to A* and multi-piece problems to a constraint solver. We also compare plain search methods (BFS, DFS, weighted A* and meet in the middle) on the same games, to find out whether a different proposer would help more than any of the additions. The proposers are ordinary programs, not language models, so every run can be repeated from a seed and we can set how good the candidate plans are.

## Literature Review

Work on language-model agents falls into three groups. One group alternates reasoning with acting: ReAct [2] interleaves thoughts and tool calls, Reflexion [5] adds a written memory of earlier failures, and Toolformer [6] trains a model to decide when to call a tool. A second group searches over reasoning steps. Tree of Thoughts [3] and Graph of Thoughts [4] expand and score alternatives, with the graph version letting paths merge, while chain-of-thought prompting [7], Plan-and-Solve [8] and ReWOO [9] fix the plan before acting. The third is TAPE [1], which builds a merged plan graph and gives path selection to an external solver. It was evaluated on Sokoban, ALFWorld [10], MuSiQue [11] and GSM8K-Hard, which is built on GSM8K [12].

These systems judge a plan by running it or by asking a model. None tests a proposed step against a rule that the task's designer wrote down. Reflexion's memory is text, so it cannot change the cost of one particular move. TAPE is closest to our setting, but it trusts every move it is shown and fixes the solver in advance.

The search literature supplies the tools for testing this. Weighted A* [18] trades plan length for speed. Iterative deepening [19] made optimal sliding-tile solving practical, pattern databases did the same for the Rubik's cube [20], and the cube's diameter is twenty moves [21]. Sokoban [14] and Rush Hour [15] are PSPACE-complete. Dead-corner pruning is a standard Sokoban technique, so we treat it as a baseline to measure and not as a contribution. Peg Solitaire has a proof tool, the pagoda function [22], [23], which we use as a checker. AO* handles actions with several outcomes and LAO* [24] extends it to graphs with cycles; Section V-G explains why neither is needed here. We use the public Boxoban levels [16] and the CP-SAT solver in OR-Tools [17].

## Methodology

Every game implements the same six-method interface: the list of actions, a step function that returns the next state and whether the move was legal, a goal test, a heuristic distance to the goal, a count of independently movable pieces, and a text renderer. Nothing downstream depends on a particular game, so adding one means writing that interface and a checker.

### System Architecture Overview

Fig. 1 shows one planning round. The proposer returns candidate plans from the current state. We replay each plan move by move and merge equal states into one node of a directed graph. The checker then judges every move and the experience store adjusts its confidence. Each surviving move gets a cost, and the solver finds the cheapest path from the current state to a goal state. That path is executed. If an executed move does not produce the predicted state, we record the failure and start a new round from the real state. Proposing, merging and executing follow TAPE. Checking and the cost-based choice of solver are ours.

![Fig. 1. The pipeline. Check (rules and experience memory) and Choose (move score, A* or CP-SAT) are the additions to TAPE. A mismatch during Run triggers a replan from the real state.](figures/pipeline.png)

### Move Validation

For a move from state s to state s', a validator returns either a rejection or an acceptance with a confidence between 0 and 1. A rejected move never becomes an edge, so every candidate plan that uses it ends there. We wrote one validator per game.

In Sokoban we reject a push that puts a box in a corner that is not a goal, since the box can never move again, and we accept a box resting against a wall off a goal at confidence 0.5. In River Crossing we reject any state with more cannibals than missionaries on a bank that still has a missionary. The step function does not enforce this on purpose, so only the validator knows the rule. In Rush Hour we reject a row filled completely by horizontal vehicles that blocks the target, and accept a blocker that is itself stuck at confidence 0.5.

Peg Solitaire uses pagoda functions. A pagoda assigns a weight w(p) >= 0 to each hole so that w(a) + w(b) >= w(c) for every jump of a peg from a over b into c. A jump removes the pegs at a and b and adds one at c, so the total weight of the pegs can never go up. If a position's total is already below the weight of the goal, which is one peg in the centre, the goal is unreachable. We get twelve pagodas from a small linear programme and recheck every inequality after solving. For the 24-puzzle we reject any move whose result is unsolvable under the inversion-parity rule. For the Rubik's cube we reject a state that breaks one of four cubie invariants: each slot holds a real cubie exactly once, corner twists sum to 0 mod 3, edge flips sum to 0 mod 2, and corner and edge permutations have the same parity. Legal moves never break the last two rules, so on those games the checker only matters when the start itself is unsolvable.

### Experience Store

A SQLite table keeps the number of successes s and failures f for each level, state and move. Confidence is Laplace-smoothed, so that a single early failure does not set trust to zero:

EQ: confidence = (s + 1) / (s + f + 2) | (1)

A move with no history has confidence 1. The value multiplies the validator's confidence, and one recorded failure takes trust from 1.00 to 0.33.

### Move Score

CP-SAT needs integer coefficients, so each accepted move gets an integer cost, scaled by ten:

EQ: cost = 10 [ 1 + 1.5 r + 4.0 (1 - c) + 2.0 (t / T)^2 ] | (2)

Here r = max(0, h(s') - h(s)) is how far the move increases the heuristic distance to the goal, c is the confidence, and t / T is the fraction of the step budget already used. The weights 1.5, 4.0 and 2.0 are our defaults. Section V-C reports whether tuning improved them.

### Path Selection and Replanning

The selection rule reads the number of independently movable pieces. With one piece, such as a single Sokoban box or the River Crossing boat, the problem is a shortest path and we run A* with the cost above. With several pieces, such as several boxes or vehicles whose routes can conflict, we formulate the path as a one-unit flow and solve it with CP-SAT. The chosen path is executed move by move. After a mismatch we write the failure to the store and plan again from the real state, up to a fixed number of replans.

## Performance Measure and Evaluation

Each experiment changes one component and holds the rest fixed.

### Benchmarks

Sokoban has four hand-made levels with one to three boxes, the hardest with a 29-move optimum. River Crossing has three missionary-cannibal pairs and a two-seat boat, with an 11-move optimum. Rush Hour is a six-by-six board solved in six moves. Boxoban [16] adds one file from each of its three difficulty sets (unfiltered, medium and hard), 1,000 ten-by-ten levels with four boxes each. Peg Solitaire is the English board, with about 3.6 million reachable positions. The 24-puzzle has about 7.8 x 10^24 states and the 3x3x3 Rubik's cube about 4.3 x 10^19.

### Plan Proposers

Our first proposer planted one shortest plan, found by BFS, among noisy walks. On River Crossing that plan is nine moves long and passes through unsafe states, because the step function accepts them. We therefore let the planted plan use the validator, which gives the textbook 11-move answer. An adversarial proposer returns uniformly random moves. A quality proposer either mixes guided and random walks or takes an optimal plan and randomizes each step with a set probability. For Boxoban, Peg Solitaire and the 24-puzzle we use weighted A* under a node budget, and for the cube a search that grows from the start and from the solved cube until the two meet. Section V-G also uses plain BFS and DFS.

### Metrics and Statistics

We call an episode a safe success when it reaches the goal and an independent auditor, which applies the game's rules whether or not the configuration under test used a validator, rejects none of its executed moves. Plain success would score River Crossing's baseline at 100% even though it breaks the rule every time. We also report replans per episode, planning time, and, for Boxoban, the share of levels solved within a node budget. Proportions carry 95% Wilson intervals. Paired comparisons use identical hazards and seeds in both arms and report the mean difference with its standard error. The weight search was fitted on training seeds and checked on seeds it had not seen.

## Results and Discussion

Table 1 collects the headline measurements. The subsections below give the experiment behind each row, including the ones where an addition did nothing.

TABLE: SUMMARY OF RESULTS
| Measurement | Without | With |
|---|---|---|
| River Crossing, safe success | 0% | 100% |
| Planning time, one-box Sokoban (ms) | 51.8 | 7.6 |
| Boxoban hard set, solved at 30k nodes | 54% | 82% |
| Peg Solitaire start, nodes to a plan | 139,048 | 82,009 |
| Peg Solitaire start, A* against DFS (nodes) | 139,048 | 10,845 |
| Replans, one-box Sokoban (change) | 0 | -0.56 |

### Safety and Speed

We ran five configurations on six benchmarks, 30 episodes per cell, with a 15% slip probability and the goal-biased proposer: the baseline, validator only, validator plus store, adaptive selection only, and everything. The baseline reaches the River Crossing goal in every episode and never does so safely. With the validator, safe success is 100% and raw success does not change. Adaptive selection saves time where one piece moves and does nothing elsewhere (Table 2), with identical success and action counts. Hard Sokoban stayed near 53% in all five configurations.

TABLE: PLANNING TIME PER EPISODE (MS)
| Benchmark | Always CP-SAT | Adaptive |
|---|---|---|
| Sokoban, one box | 51.8 | 7.6 |
| River Crossing | 62.1 | 3.6 |
| Sokoban, two boxes | 99.9 | 96.4 |
| Rush Hour | 36.2 | 36.1 |

### Experience Store Under State-Dependent Failure

With uniform random slips the store had nothing to learn and changed nothing. We then made 25% of the state and move pairs slip with probability 0.7 and compared validator only with validator plus store, paired over 20 hazard seeds of 30 episodes (Table 3). The store cut late-episode replans by about 14% on one-box Sokoban and River Crossing, did not separate from zero on Rush Hour, and made no difference on two-box Sokoban. We have not tested why, but a plausible reason is that two-box levels offer more routes and the 30 candidates rarely include a detour around a learned hazard. The store can only reweight edges that are already in the graph.

TABLE: EXPERIENCE STORE UNDER STATE-DEPENDENT SLIP
| Benchmark | Replans (late) | Success |
|---|---|---|
| Sokoban, one box | -0.56 +/- 0.18 | +5.5 pts |
| River Crossing | -0.54 +/- 0.15 | +5.0 pts |
| Rush Hour | -0.17 +/- 0.11 | +1.2 pts |
| Sokoban, two boxes | +0.06 +/- 0.03 | -0.2 pts |

### Tuning the Score Weights

We searched 80 combinations of the three penalty weights on 8 training seeds, then reran the top three and our defaults on 16 unseen seeds. The objective was replans plus three times the failure rate, averaged over four benchmarks. The best training point scored 3.906 against 4.219 for the defaults, which ranked 23rd of 80, but on the unseen seeds it was worse by 0.122 +/- 0.111. No candidate beat the defaults by more than one standard error, so we kept them. This shows only that the search found nothing better, not that the defaults are optimal.

### Proposer Quality

We then asked how much the layer matters as the proposer gets better or worse. A proposer built only from random and guided walks barely solved the easiest non-trivial level (17% at best), so it told us little. With a proposer that corrupts an optimal plan, the full layer and the baseline differed by less than two standard errors on almost every Sokoban and Rush Hour comparison. River Crossing stayed at 0% safe success in both arms: this proposer never learns the safety rule, so its best plan is the unsafe one, and the validator correctly rejects it. What the validator did buy was 2.7 to 3.4 fewer replans per episode at quality 0.7 and above. It can remove bad plans, but it cannot supply a good one that the proposer never produced.

### Boxoban

Here a level counts as solved if any of four searches finds a plan within the node budget. Without pruning the search does not know about dead corners, and with the checker it skips them (Fig. 2, Table 4). The checker did better in all 15 combinations of set and budget, with non-overlapping 95% intervals, and never missed a level that the unpruned search solved. The gain grows with difficulty: at 10,000 nodes it is 8, 19 and 22 points on the three sets, and at 30,000 nodes 3, 17 and 28 points. At the full budget the checker also expands 20%, 25% and 23% fewer nodes per level. Merging plans did not shorten any path in practice. It produced a shorter path than the best single plan on one level out of 2,680 solved, and a longer one on 33, because the solver minimizes the cost in Eq. (2) and not the number of moves.

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

Peg Solitaire is the only game where the checker helps during play. We tested its soundness by sampling positions that the pagoda checker rejects and proving each unsolvable by exhaustive search; none was solvable. From the real start position the checker cuts the search from 139,048 to 82,009 nodes, a 41% saving. Our first benchmark used positions reached by random play, but most of them could not be solved within the budget and the search could not tell whether they were lost, so it separated nothing. We rebuilt it by playing jumps backwards from the goal, which guarantees that every position is solvable. Within 60,000 nodes the checker solves 98% of positions 22 jumps from the goal against 93% without it, and 75% against 58% at 26 jumps, using 19 to 31% fewer nodes. It never lost a position that the plain search solved (Fig. 3, Table 5).

![Fig. 3. Peg Solitaire on positions built backwards from the goal: share solved (top) and mean nodes per search (bottom, log scale).](figures/peg.png)

TABLE: PEG SOLITAIRE, SOLVED (%) AND MEAN NODES
| Jumps | No checker | Checker | Nodes (no / with) |
|---|---|---|---|
| 12 | 100 | 100 | 296 / 237 |
| 18 | 100 | 100 | 2,776 / 1,914 |
| 22 | 93 | 98 | 13,780 / 9,663 |
| 26 | 58 | 75 | 39,170 / 31,817 |

The 24-puzzle and the cube behave differently. Legal moves never break the parity rule or the cubie invariants, and we confirmed that the checks change no result on a solvable start. They matter when the input itself is unsolvable. With two tiles swapped, or one cube corner twisted, the plain search burned its whole budget (60,000 and 400,000 nodes) and the check stopped it after at most one. Weighted A* solved random-walk scrambles of the 24-puzzle at rates of 100%, 95%, 73% and 57% for 20, 40, 60 and 80 moves, and the meet-in-the-middle search solved every cube scramble of 4 to 8 moves.

### Search Methods

We ran BFS, DFS, weighted A* and meet in the middle on every game each can handle, without checkers, with a budget of 100,000 nodes. The small games had one instance and the others 20 (Table 6, Fig. 4).

TABLE: SEARCH METHODS: SOLVED (%) AND MEAN NODES
@search_table

![Fig. 4. Share of instances solved within 100,000 nodes, by search method.](figures/search_methods.png)

DFS won on one game and by a wide margin. Every Peg Solitaire solution has exactly 31 jumps, so a depth-first search that never revisits a state gives up nothing. From the real start it needed 10,845 nodes, or 6,455 with the pagoda checker, where weighted A* needed 139,048 and BFS found no plan in 400,000. On a position that weighted A* could not solve in 20,000 nodes, DFS needed about 10,800. On positions 22 jumps from the goal the order reversed slightly, with weighted A* at 95% and DFS at 85%. BFS was enough only on River Crossing and Rush Hour, where it also returns the shortest plan. Weighted A* was the best general choice, though DFS plans on Boxoban were about 2.5 times longer than its plans. Meet in the middle guarantees a shortest plan, but on short cube scrambles it used more nodes than A* with our sticker-count heuristic, and it ran out of budget on the 40-move 24-puzzle.

We did not implement AO*. It plans over graphs where an action has several possible outcomes, and each of our games is deterministic, so its graph has no AND nodes and it reduces to A*. It could matter for the slip model, where a move sometimes leaves the state unchanged. That outcome loops back to the same state, which is the case LAO* [24] was designed for. Node counts mean expansions for BFS, DFS and A*, and generated states for meet in the middle, so the last column is only roughly comparable.

### Reading the Results Together

The checker earns its place in two situations: when the environment accepts moves that its rules forbid, as in River Crossing, and when it can prune a search that would otherwise explore dead branches, as in Boxoban and Peg Solitaire. It does little when the proposer already finds good plans, and it cannot create a plan the proposer lacks. Adaptive selection is a small saving that depends only on piece count. The experience store is worth running when failures depend on the state and the candidates offer a detour. Among search methods, use depth-first search when every solution has the same length, meet in the middle when only the shortest plan will do and the state space is reversible, and weighted A* otherwise.

### Limitations

Our proposers are programs and we never tried a language model, so these results say nothing about how real model errors would behave. The goal-biased proposer plants a BFS plan, which makes absolute success rates in Sections V-A and V-B higher than a real proposer would give; the paired differences are less affected. Dead-corner pruning is standard in Sokoban solvers, so Section V-E shows only that our validator works as that pruner on external levels. Boxoban coverage is one file per set and one rule. The harder-game scrambles are random walks, which are easier than uniformly random instances, and we tested the cube only up to 8-move scrambles. We cannot compare with TAPE's reported numbers because its benchmarks need a language model. The weight search used 8 training seeds, so its ranking is noisy, the search comparison has few instances on the small games, and weighted A* returns plans that are not optimal, so a lower node count can come with a longer plan.

## Future Scope

The most useful next experiment is a learned proposer. We would train a policy by imitation on the Boxoban solutions we have and check whether checker pruning still saves nodes when the proposals contain realistic mistakes. A second Sokoban rule, such as frozen boxes, would show whether the Boxoban gain grows with more rules; the measure would be levels solved at 10,000 nodes. The slip model could be planned for in advance with LAO*, and the comparison would be expected replans against our replan-on-mismatch baseline. We would also write a soundness argument for each validator, as we did informally for the pagoda bound, and add a standard classical planner as a stronger baseline than plain A*.

## Conclusion

On these seven games the layer's value is mostly in what it prevents. It stops rule-breaking plans in River Crossing, wastes less search on dead branches in Boxoban and Peg Solitaire, and spends less solver time on single-piece problems. It did not raise the goal-reach rate of a proposer that already finds good plans, and two ideas we expected to help, weight tuning and plan merging, did nothing measurable. For Peg Solitaire the better change was to the search method: depth-first search with the pagoda checker solved the real start in 6,455 nodes against 139,048 for plain weighted A*.

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
