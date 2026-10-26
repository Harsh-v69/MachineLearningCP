# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

_no data_

## Agents (success within budget under noise)

_no data_

## Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R, or (T=-1) a user-supplied level skipped by the oracle: status = the oracle status or already_solved; cost means are over solved instances only)

| bench | level | T | solver | n | ok | forced_longer | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|---|---|
| cube2 | - | 3 | skipped | 1 | 0.0 |  |  |  |  |  |
| cube2 | - | 5 | skipped | 1 | 0.0 |  |  |  |  |  |
| cube2 | bind | 3 | astar | 3 | 1.0 | 1.0 | 1.0 | 4.0 | 6.3333 | 0.0002 |
| cube2 | bind | 3 | ilp | 3 | 0.0 |  | 0.0 |  | 98471.0 | 21.6457 |
| cube2 | bind | 5 | astar | 3 | 1.0 | 1.0 | 1.0 | 6.0 | 45.6667 | 0.0014 |
| cube2 | bind | 5 | ilp | 3 | 0.0 |  | 0.0 |  | 500000.0 | 4.1637 |
| cube2 | bind | 7 | astar | 4 | 1.0 | 1.0 | 1.0 | 8.0 | 544.0 | 0.0222 |
| cube2 | bind | 7 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.6842 |
| cube2 | bind | 9 | astar | 4 | 1.0 | 1.0 | 1.0 | 10.0 | 15193.25 | 0.8256 |
| cube2 | bind | 9 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.5034 |
| cube2 | bind | 11 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 169473.25 | 9.7551 |
| cube2 | bind | 11 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.6353 |
| cube2 | tight | 5 | astar | 2 | 1.0 | 1.0 | 1.0 | 8.0 | 664.0 | 0.0323 |
| cube2 | tight | 5 | ilp | 2 | 0.0 |  | 0.0 |  | 500000.0 | 3.923 |
| cube2 | tight | 7 | astar | 2 | 1.0 | 1.0 | 1.0 | 10.0 | 4110.0 | 0.1927 |
| cube2 | tight | 7 | ilp | 2 | 0.0 |  | 0.0 |  | 500000.0 | 3.7639 |
| cube2 | tight | 9 | astar | 3 | 1.0 | 1.0 | 1.0 | 11.0 | 13847.3333 | 0.683 |
| cube2 | tight | 9 | ilp | 3 | 0.0 |  | 0.0 |  | 500000.0 | 3.7223 |
| cube2 | tight | 11 | astar | 4 | 1.0 | 1.0 | 1.0 | 13.0 | 180470.75 | 8.7984 |
| cube2 | tight | 11 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.5838 |
| river | - | 4 | skipped | 6 | 0.0 |  |  |  |  |  |
| river | - | 6 | skipped | 8 | 0.0 |  |  |  |  |  |
| river | - | 8 | skipped | 20 | 0.0 |  |  |  |  |  |
| river | - | 10 | skipped | 16 | 0.0 |  |  |  |  |  |
| river | - | 12 | skipped | 7 | 0.0 |  |  |  |  |  |
| river | - | 14 | skipped | 20 | 0.0 |  |  |  |  |  |
| river | bind | 4 | astar | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 20.8571 | 0.0003 |
| river | bind | 4 | ilp | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 31.0 | 0.0274 |
| river | bind | 6 | astar | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 29.0 | 0.0005 |
| river | bind | 6 | ilp | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 34.0 | 0.0311 |
| river | bind | 10 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 69.0 | 0.0014 |
| river | bind | 10 | ilp | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 45.0 | 0.1299 |
| river | bind | 12 | astar | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 70.0 | 0.0013 |
| river | bind | 12 | ilp | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 45.0 | 0.0993 |
| river | tight | 4 | astar | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 20.2857 | 0.0004 |
| river | tight | 4 | ilp | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 31.0 | 0.0223 |
| river | tight | 6 | astar | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 29.0 | 0.0005 |
| river | tight | 6 | ilp | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 34.0 | 0.0322 |
| river | tight | 10 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 69.0 | 0.0015 |
| river | tight | 10 | ilp | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 45.0 | 0.1449 |
| river | tight | 12 | astar | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 70.0 | 0.0013 |
| river | tight | 12 | ilp | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 45.0 | 0.0804 |
| sokoban | - | 5 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban | - | 6 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban | - | 7 | skipped | 6 | 0.0 |  |  |  |  |  |
| sokoban | - | 9 | skipped | 9 | 0.0 |  |  |  |  |  |
| sokoban | - | 10 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban | - | 11 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban | - | 13 | skipped | 10 | 0.0 |  |  |  |  |  |
| sokoban | - | 14 | skipped | 5 | 0.0 |  |  |  |  |  |
| sokoban | - | 15 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban | - | 17 | skipped | 10 | 0.0 |  |  |  |  |  |
| sokoban | - | 18 | skipped | 5 | 0.0 |  |  |  |  |  |
| sokoban | - | 19 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban | - | 21 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban | - | 22 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban | - | 23 | skipped | 1 | 0.0 |  |  |  |  |  |
| sokoban | bind | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 184.0 | 0.0026 |
| sokoban | bind | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 360.0 | 0.3102 |
| sokoban | bind | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 185.0 | 0.0025 |
| sokoban | bind | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 368.0 | 0.2629 |
| sokoban | bind | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 358.0 | 0.0081 |
| sokoban | bind | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 602.0 | 0.423 |
| sokoban | bind | 19 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 277.0 | 0.0056 |
| sokoban | bind | 19 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 516.0 | 0.2768 |
| sokoban | bind | 21 | astar | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 348.0 | 0.0062 |
| sokoban | bind | 21 | ilp | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 602.0 | 0.4102 |
| sokoban | bind | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 233.0 | 0.0034 |
| sokoban | bind | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 427.0 | 0.3891 |
| sokoban | tight | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 167.0 | 0.0027 |
| sokoban | tight | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 360.0 | 0.2502 |
| sokoban | tight | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 175.0 | 0.0025 |
| sokoban | tight | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 368.0 | 0.331 |
| sokoban | tight | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 341.0 | 0.0054 |
| sokoban | tight | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 602.0 | 0.4208 |
| sokoban | tight | 19 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 262.0 | 0.0047 |
| sokoban | tight | 19 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 516.0 | 0.2508 |
| sokoban | tight | 21 | astar | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 336.5 | 0.0057 |
| sokoban | tight | 21 | ilp | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 602.0 | 0.3206 |
| sokoban | tight | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 212.0 | 0.0047 |
| sokoban | tight | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 427.0 | 0.4245 |
| sokoban2 | - | 5 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 6 | skipped | 1 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 7 | skipped | 12 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 9 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 10 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 11 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 13 | skipped | 7 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 14 | skipped | 4 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 15 | skipped | 8 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 17 | skipped | 9 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 18 | skipped | 6 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 19 | skipped | 2 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 21 | skipped | 9 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 22 | skipped | 6 | 0.0 |  |  |  |  |  |
| sokoban2 | - | 23 | skipped | 3 | 0.0 |  |  |  |  |  |
| sokoban2 | bind | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 428.0 | 0.0088 |
| sokoban2 | bind | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 1451.0 | 1.3107 |
| sokoban2 | bind | 17 | astar | 2 | 1.0 | 1.0 | 1.0 | 21.0 | 2759.0 | 0.0698 |
| sokoban2 | bind | 17 | ilp | 2 | 0.0 |  | 0.0 |  | 5650.0 | 10.9117 |
| sokoban2 | bind | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1509.0 | 0.0343 |
| sokoban2 | bind | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 4255.0 | 9.3494 |
| sokoban2 | bind | 21 | astar | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1096.0 | 0.0206 |
| sokoban2 | bind | 21 | ilp | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 2579.0 | 3.6684 |
| sokoban2 | bind | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 30.0 | 3524.0 | 0.0674 |
| sokoban2 | bind | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 30.0 | 3061.0 | 3.6416 |
| sokoban2 | tight | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 412.0 | 0.0112 |
| sokoban2 | tight | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 1451.0 | 1.1752 |
| sokoban2 | tight | 17 | astar | 2 | 1.0 | 1.0 | 1.0 | 21.0 | 2618.0 | 0.0854 |
| sokoban2 | tight | 17 | ilp | 2 | 0.0 |  | 0.0 |  | 5650.0 | 10.8506 |
| sokoban2 | tight | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 1483.0 | 0.0367 |
| sokoban2 | tight | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 4255.0 | 9.1419 |
| sokoban2 | tight | 21 | astar | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 1075.0 | 0.0225 |
| sokoban2 | tight | 21 | ilp | 1 | 1.0 | 1.0 | 1.0 | 23.0 | 2579.0 | 3.5371 |
| sokoban2 | tight | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 30.0 | 3407.0 | 0.0876 |
| sokoban2 | tight | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 30.0 | 3061.0 | 3.392 |

## Failure breakdown: solvers (count of rows per status)

_no data_

## Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | too_large | timeout | no_tradeoff |
|---|---|---|---|---|---|---|
| cube2 | astar | 29 | 29 | 0 | 0 | 0 |
| cube2 | ilp | 29 | 0 | 26 | 3 | 0 |
| cube2 | skipped | 2 | 0 | 0 | 0 | 2 |
| river | astar | 86 | 86 | 0 | 0 | 0 |
| river | ilp | 86 | 86 | 0 | 0 | 0 |
| river | skipped | 77 | 0 | 0 | 0 | 77 |
| sokoban | astar | 14 | 14 | 0 | 0 | 0 |
| sokoban | ilp | 14 | 14 | 0 | 0 | 0 |
| sokoban | skipped | 83 | 0 | 0 | 0 | 83 |
| sokoban2 | astar | 12 | 12 | 0 | 0 | 0 |
| sokoban2 | ilp | 12 | 8 | 0 | 4 | 0 |
| sokoban2 | skipped | 94 | 0 | 0 | 0 | 94 |

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
