# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

_no data_

## Agents (success within budget under noise)

_no data_

## Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)

| bench | level | T | solver | n | ok | forced_longer | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|---|---|
| boxoban | - | 7 | skipped | 4 | 0.0 |  |  |  |  |  |
| boxoban | - | 8 | skipped | 2 | 0.0 |  |  |  |  |  |
| boxoban | - | 9 | skipped | 4 | 0.0 |  |  |  |  |  |
| boxoban | - | 11 | skipped | 2 | 0.0 |  |  |  |  |  |
| boxoban | - | 12 | skipped | 6 | 0.0 |  |  |  |  |  |
| boxoban | - | 13 | skipped | 1 | 0.0 |  |  |  |  |  |
| boxoban | - | 15 | skipped | 4 | 0.0 |  |  |  |  |  |
| boxoban | - | 16 | skipped | 4 | 0.0 |  |  |  |  |  |
| boxoban | - | 17 | skipped | 2 | 0.0 |  |  |  |  |  |
| boxoban | - | 19 | skipped | 3 | 0.0 |  |  |  |  |  |
| boxoban | - | 20 | skipped | 2 | 0.0 |  |  |  |  |  |
| boxoban | - | 21 | skipped | 5 | 0.0 |  |  |  |  |  |
| boxoban | bind | 12 | astar | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 1274.0 | 0.0914 |
| boxoban | bind | 12 | ilp | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 8330.0 | 7.3262 |
| boxoban | tight | 12 | astar | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 1248.0 | 0.0547 |
| boxoban | tight | 12 | ilp | 1 | 1.0 | 1.0 | 1.0 | 13.0 | 8330.0 | 7.3454 |
| cube2 | - | 3 | skipped | 1 | 0.0 |  |  |  |  |  |
| cube2 | - | 5 | skipped | 1 | 0.0 |  |  |  |  |  |
| cube2 | bind | 3 | astar | 3 | 1.0 | 1.0 | 1.0 | 4.0 | 6.3333 | 0.0002 |
| cube2 | bind | 3 | ilp | 3 | 1.0 | 1.0 | 1.0 | 4.0 | 302.3333 | 0.066 |
| cube2 | bind | 5 | astar | 3 | 1.0 | 1.0 | 1.0 | 6.0 | 45.6667 | 0.0017 |
| cube2 | bind | 5 | ilp | 3 | 1.0 | 1.0 | 1.0 | 6.0 | 4319.3333 | 1.9566 |
| cube2 | bind | 7 | astar | 4 | 1.0 | 1.0 | 1.0 | 8.0 | 544.0 | 0.0285 |
| cube2 | bind | 7 | ilp | 4 | 0.0 |  | 0.0 |  | 90702.0 | 19.514 |
| cube2 | bind | 9 | astar | 4 | 1.0 | 1.0 | 1.0 | 10.0 | 15193.25 | 0.7755 |
| cube2 | bind | 9 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.4271 |
| cube2 | bind | 11 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 169473.25 | 8.788 |
| cube2 | bind | 11 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 3.0762 |
| cube2 | tight | 5 | astar | 2 | 1.0 | 1.0 | 1.0 | 8.0 | 664.0 | 0.0144 |
| cube2 | tight | 5 | ilp | 2 | 1.0 | 1.0 | 1.0 | 8.0 | 4396.0 | 0.8737 |
| cube2 | tight | 7 | astar | 2 | 1.0 | 1.0 | 1.0 | 10.0 | 4110.0 | 0.1858 |
| cube2 | tight | 7 | ilp | 2 | 0.0 |  | 0.0 |  | 93595.0 | 21.4939 |
| cube2 | tight | 9 | astar | 3 | 1.0 | 1.0 | 1.0 | 11.0 | 13847.3333 | 0.5759 |
| cube2 | tight | 9 | ilp | 3 | 0.0 |  | 0.0 |  | 500000.0 | 3.6688 |
| cube2 | tight | 11 | astar | 4 | 1.0 | 1.0 | 1.0 | 13.0 | 180470.75 | 8.241 |
| cube2 | tight | 11 | ilp | 4 | 0.0 |  | 0.0 |  | 500000.0 | 2.9301 |
| river | - | 4 | skipped | 6 | 0.0 |  |  |  |  |  |
| river | - | 6 | skipped | 8 | 0.0 |  |  |  |  |  |
| river | - | 8 | skipped | 20 | 0.0 |  |  |  |  |  |
| river | - | 10 | skipped | 16 | 0.0 |  |  |  |  |  |
| river | - | 12 | skipped | 7 | 0.0 |  |  |  |  |  |
| river | - | 14 | skipped | 20 | 0.0 |  |  |  |  |  |
| river | bind | 4 | astar | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 20.8571 | 0.0003 |
| river | bind | 4 | ilp | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 23.1429 | 0.0254 |
| river | bind | 6 | astar | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 29.0 | 0.0005 |
| river | bind | 6 | ilp | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 24.0 | 0.0292 |
| river | bind | 10 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 69.0 | 0.0018 |
| river | bind | 10 | ilp | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 45.0 | 0.0739 |
| river | bind | 12 | astar | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 70.0 | 0.0011 |
| river | bind | 12 | ilp | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 45.0 | 0.0539 |
| river | tight | 4 | astar | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 20.2857 | 0.0004 |
| river | tight | 4 | ilp | 14 | 1.0 | 1.0 | 1.0 | 6.0 | 23.1429 | 0.0214 |
| river | tight | 6 | astar | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 29.0 | 0.0005 |
| river | tight | 6 | ilp | 12 | 1.0 | 1.0 | 1.0 | 8.0 | 24.0 | 0.0303 |
| river | tight | 10 | astar | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 69.0 | 0.0014 |
| river | tight | 10 | ilp | 4 | 1.0 | 1.0 | 1.0 | 12.0 | 45.0 | 0.0897 |
| river | tight | 12 | astar | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 70.0 | 0.0012 |
| river | tight | 12 | ilp | 13 | 1.0 | 1.0 | 1.0 | 14.0 | 45.0 | 0.1165 |
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
| sokoban | bind | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 184.0 | 0.0034 |
| sokoban | bind | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 278.0 | 0.2135 |
| sokoban | bind | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 185.0 | 0.0042 |
| sokoban | bind | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 274.0 | 0.118 |
| sokoban | bind | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 358.0 | 0.0055 |
| sokoban | bind | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 532.0 | 0.4183 |
| sokoban | bind | 19 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 277.0 | 0.0042 |
| sokoban | bind | 19 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 405.0 | 0.1711 |
| sokoban | bind | 21 | astar | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 348.0 | 0.0053 |
| sokoban | bind | 21 | ilp | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 506.0 | 0.2293 |
| sokoban | bind | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 233.0 | 0.0037 |
| sokoban | bind | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 279.0 | 0.119 |
| sokoban | tight | 13 | astar | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 167.0 | 0.0038 |
| sokoban | tight | 13 | ilp | 1 | 1.0 | 1.0 | 1.0 | 15.0 | 278.0 | 0.1855 |
| sokoban | tight | 14 | astar | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 175.0 | 0.003 |
| sokoban | tight | 14 | ilp | 1 | 1.0 | 1.0 | 1.0 | 16.0 | 274.0 | 0.1179 |
| sokoban | tight | 18 | astar | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 341.0 | 0.006 |
| sokoban | tight | 18 | ilp | 1 | 1.0 | 1.0 | 1.0 | 20.0 | 532.0 | 0.4024 |
| sokoban | tight | 19 | astar | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 262.0 | 0.0037 |
| sokoban | tight | 19 | ilp | 1 | 1.0 | 1.0 | 1.0 | 21.0 | 405.0 | 0.1683 |
| sokoban | tight | 21 | astar | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 336.5 | 0.0052 |
| sokoban | tight | 21 | ilp | 2 | 1.0 | 1.0 | 1.0 | 23.0 | 506.0 | 0.2637 |
| sokoban | tight | 22 | astar | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 212.0 | 0.003 |
| sokoban | tight | 22 | ilp | 1 | 1.0 | 1.0 | 1.0 | 24.0 | 279.0 | 0.1119 |

## Failure breakdown: solvers (count of rows per status)

_no data_

## Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | too_large | timeout | no_tradeoff |
|---|---|---|---|---|---|---|
| boxoban | astar | 2 | 2 | 0 | 0 | 0 |
| boxoban | ilp | 2 | 2 | 0 | 0 | 0 |
| boxoban | skipped | 39 | 0 | 0 | 0 | 39 |
| cube2 | astar | 29 | 29 | 0 | 0 | 0 |
| cube2 | ilp | 29 | 8 | 15 | 6 | 0 |
| cube2 | skipped | 2 | 0 | 0 | 0 | 2 |
| river | astar | 86 | 86 | 0 | 0 | 0 |
| river | ilp | 86 | 86 | 0 | 0 | 0 |
| river | skipped | 77 | 0 | 0 | 0 | 77 |
| sokoban | astar | 14 | 14 | 0 | 0 | 0 |
| sokoban | ilp | 14 | 14 | 0 | 0 | 0 |
| sokoban | skipped | 83 | 0 | 0 | 0 | 83 |

ILP status on skipped-infeasible constrained rows (ilp_status recorded for 0 of 0; ilp_status = ok would mean the ILP found a path where A* proved none): none recorded
