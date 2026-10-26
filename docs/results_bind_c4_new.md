# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

_no data_

## Agents (success within budget under noise)

_no data_

## Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R, or (T=-1) a user-supplied level skipped by the oracle: status = the oracle status or already_solved; cost means are over solved instances only)

| bench | level | T | solver | n | ok | forced_longer | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|---|---|
| cube3 | - | 3 | skipped | 1 | 0.0 |  |  |  |  |  |
| cube3 | - | 9 | skipped | 2 | 0.0 |  |  |  |  |  |
| cube3 | bind | 3 | astar | 4 | 1.0 | 1.0 | 1.0 | 4.0 | 11.25 | 0.0007 |
| cube3 | bind | 3 | ilp | 4 | 1.0 | 1.0 | 1.0 | 4.0 | 5185.0 | 1.5487 |
| cube3 | bind | 5 | astar | 5 | 1.0 | 1.0 | 1.0 | 6.0 | 36.4 | 0.0023 |
| cube3 | bind | 5 | ilp | 5 | 0.6 | 1.0 | 0.6 | 6.0 | 49294.0 | 15.1216 |
| cube3 | bind | 7 | astar | 5 | 1.0 | 1.0 | 1.0 | 8.0 | 379.2 | 0.0373 |
| cube3 | bind | 7 | ilp | 5 | 0.0 |  | 0.0 |  | 100000.0 | 1.9019 |
| cube3 | bind | 9 | astar | 3 | 1.0 | 1.0 | 1.0 | 10.0 | 4295.0 | 0.39 |
| cube3 | bind | 9 | ilp | 3 | 0.0 |  | 0.0 |  | 100000.0 | 0.8244 |
| cube3 | tight | 3 | astar | 3 | 1.0 | 1.0 | 1.0 | 5.0 | 25.6667 | 0.0025 |
| cube3 | tight | 3 | ilp | 3 | 1.0 | 1.0 | 1.0 | 5.0 | 5683.6667 | 1.2909 |
| cube3 | tight | 5 | astar | 2 | 1.0 | 1.0 | 1.0 | 7.0 | 58.0 | 0.0082 |
| cube3 | tight | 5 | ilp | 2 | 1.0 | 1.0 | 1.0 | 7.0 | 42374.5 | 9.6996 |
| cube3 | tight | 7 | astar | 5 | 1.0 | 1.0 | 1.0 | 9.8 | 5434.2 | 0.3702 |
| cube3 | tight | 7 | ilp | 5 | 0.0 |  | 0.0 |  | 100000.0 | 1.9376 |
| cube3 | tight | 9 | astar | 3 | 1.0 | 1.0 | 1.0 | 11.6667 | 31094.0 | 2.3393 |
| cube3 | tight | 9 | ilp | 3 | 0.0 |  | 0.0 |  | 100000.0 | 0.8456 |
| sokoban2 | - | 5 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 6 | skipped | 1 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 7 | skipped | 12 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 9 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 10 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 11 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 13 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 14 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 15 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 17 | skipped | 10 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 18 | skipped | 6 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 19 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 21 | skipped | 9 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 22 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 23 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban2 | bind | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 428.0 | 0.0093 |
| sokoban2 | bind | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 893.0 | 0.4949 |
| sokoban2 | bind | 17 | astar | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 1854.0 | 0.0768 |
| sokoban2 | bind | 17 | ilp | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 3212.0 | 4.1651 |
| sokoban2 | bind | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1509.0 | 0.0343 |
| sokoban2 | bind | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1946.0 | 1.5929 |
| sokoban2 | bind | 21 | astar | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1096.0 | 0.0216 |
| sokoban2 | bind | 21 | ilp | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1547.0 | 1.3417 |
| sokoban2 | tight | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 412.0 | 0.0099 |
| sokoban2 | tight | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 893.0 | 0.6159 |
| sokoban2 | tight | 17 | astar | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 1835.0 | 0.0454 |
| sokoban2 | tight | 17 | ilp | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 3212.0 | 4.3072 |
| sokoban2 | tight | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1483.0 | 0.0371 |
| sokoban2 | tight | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1946.0 | 1.4746 |
| sokoban2 | tight | 21 | astar | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1075.0 | 0.0201 |
| sokoban2 | tight | 21 | ilp | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1547.0 | 1.2828 |
| sokoban3 | - | 9 | skipped | 1 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 10 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 11 | skipped | 5 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 13 | skipped | 5 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 14 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 17 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 18 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 19 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 21 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 22 | skipped | 5 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 23 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 25 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 26 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban3 | - | 27 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban3 | bind | 11 | astar | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 261.0 | 0.0061 |
| sokoban3 | bind | 11 | ilp | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 607.0 | 0.2673 |
| sokoban3 | bind | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 17.0 | 809.0 | 0.0221 |
| sokoban3 | bind | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 17.0 | 821.0 | 0.4036 |
| sokoban3 | bind | 17 | astar | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 5931.0 | 0.25 |
| sokoban3 | bind | 17 | ilp | 1 | 0.0 |  | 0.0 |  | 11675.0 | 11.3287 |
| sokoban3 | bind | 26 | astar | 1 | 1.0 | 1.0 | 1.0 | 28.0 | 38812.0 | 1.4553 |
| sokoban3 | bind | 26 | ilp | 1 | 0.0 |  | 0.0 |  | 68377.0 | 21.356 |
| sokoban3 | tight | 11 | astar | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 229.0 | 0.0052 |
| sokoban3 | tight | 11 | ilp | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 607.0 | 0.2679 |
| sokoban3 | tight | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 17.0 | 785.0 | 0.0183 |
| sokoban3 | tight | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 17.0 | 821.0 | 0.3373 |
| sokoban3 | tight | 17 | astar | 1 | 1.0 | 1.0 | 1.0 | 19.0 | 5782.0 | 0.1623 |
| sokoban3 | tight | 17 | ilp | 1 | 0.0 |  | 0.0 |  | 11675.0 | 11.0587 |
| sokoban3 | tight | 26 | astar | 1 | 1.0 | 1.0 | 1.0 | 28.0 | 36455.0 | 1.3446 |
| sokoban3 | tight | 26 | ilp | 1 | 0.0 |  | 0.0 |  | 68377.0 | 22.0147 |

## Failure breakdown: solvers (count of rows per status)

_no data_

## Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | node_limit | too_large | timeout | no_tradeoff |
|---|---|---|---|---|---|---|---|
| cube3 | astar | 30 | 30 | 0 | 0 | 0 | 0 |
| cube3 | ilp | 30 | 12 | 0 | 16 | 2 | 0 |
| cube3 | skipped | 3 | 0 | 1 | 0 | 0 | 2 |
| sokoban2 | astar | 8 | 8 | 0 | 0 | 0 | 0 |
| sokoban2 | ilp | 8 | 8 | 0 | 0 | 0 | 0 |
| sokoban2 | skipped | 96 | 0 | 0 | 0 | 0 | 96 |
| sokoban3 | astar | 8 | 8 | 0 | 0 | 0 | 0 |
| sokoban3 | ilp | 8 | 4 | 0 | 0 | 4 | 0 |
| sokoban3 | skipped | 46 | 0 | 0 | 0 | 0 | 46 |

ILP status on skipped-infeasible constrained rows (ilp_status recorded for 0 of 0; ilp_status = ok would mean the ILP found a path where A* proved none): none recorded

## Agents: success per (bench, T*, method) with 95% Wilson intervals (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Agents: pooled per benchmark (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval; the interval treats the trials as independent, although the episodes of one instance share a level)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Paired differences in success (mean over instances of success_ours_astar - success_other; 95% percentile bootstrap, B = 2000, resampled over instances, paired by instance)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).
