# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

| bench | T | solver | n | ok | cost_ratio | nodes | seconds |
|---|---|---|---|---|---|---|---|
| cube3 | 3 | astar | 5 | 1.0 | 1.0 | 3.8 | 0.0003 |
| cube3 | 3 | bfs | 5 | 1.0 | 1.0 | 165.6 | 0.0059 |
| cube3 | 3 | idastar | 5 | 1.0 | 1.0 | 3.0 | 0.0001 |
| cube3 | 3 | ilp | 5 | 1.0 | 1.0 | 127.0 | 0.051 |
| cube3 | 3 | wastar | 5 | 1.0 | 1.0 | 3.0 | 0.0002 |
| cube3 | 5 | astar | 5 | 1.0 | 1.0 | 11.2 | 0.0011 |
| cube3 | 5 | bfs | 5 | 1.0 | 1.0 | 21571.6 | 0.7093 |
| cube3 | 5 | idastar | 5 | 1.0 | 1.0 | 8.8 | 0.0003 |
| cube3 | 5 | ilp | 5 | 1.0 | 1.0 | 689.4 | 0.1568 |
| cube3 | 5 | wastar | 5 | 1.0 | 1.0 | 20.6 | 0.0013 |
| cube3 | 7 | astar | 5 | 1.0 | 1.0 | 72.0 | 0.0091 |
| cube3 | 7 | bfs | 5 | 0.0 |  | 100001.0 | 3.4838 |
| cube3 | 7 | idastar | 5 | 1.0 | 1.0 | 47.8 | 0.0021 |
| cube3 | 7 | ilp | 5 | 1.0 | 1.0 | 8131.0 | 2.0357 |
| cube3 | 7 | wastar | 5 | 1.0 | 1.0 | 441.4 | 0.0161 |
| cube3 | 9 | astar | 5 | 1.0 | 1.0 | 1990.8 | 0.1934 |
| cube3 | 9 | bfs | 5 | 0.0 |  | 100001.0 | 3.759 |
| cube3 | 9 | idastar | 5 | 1.0 | 1.0 | 1488.0 | 0.0649 |
| cube3 | 9 | ilp | 5 | 0.2 | 1.0 | 99555.4 | 3.8276 |
| cube3 | 9 | wastar | 5 | 0.8 | 1.0 | 54205.6 | 1.9685 |
| sokoban2 | 5 | astar | 2 | 1.0 | 1.0 | 27.5 | 0.0006 |
| sokoban2 | 5 | bfs | 2 | 1.0 | 1.0 | 31.5 | 0.0002 |
| sokoban2 | 5 | idastar | 2 | 1.0 | 1.0 | 52.0 | 0.0007 |
| sokoban2 | 5 | ilp | 2 | 1.0 | 1.0 | 59.5 | 0.0494 |
| sokoban2 | 5 | wastar | 2 | 1.0 | 1.0 | 20.0 | 0.0004 |
| sokoban2 | 7 | astar | 3 | 1.0 | 1.0 | 53.3333 | 0.0014 |
| sokoban2 | 7 | bfs | 3 | 1.0 | 1.0 | 84.0 | 0.0005 |
| sokoban2 | 7 | idastar | 3 | 1.0 | 1.0 | 69.0 | 0.0012 |
| sokoban2 | 7 | ilp | 3 | 1.0 | 1.0 | 123.6667 | 0.0549 |
| sokoban2 | 7 | wastar | 3 | 1.0 | 1.0 | 26.3333 | 0.0007 |
| sokoban2 | 10 | astar | 1 | 1.0 | 1.0 | 177.0 | 0.0025 |
| sokoban2 | 10 | bfs | 1 | 1.0 | 1.0 | 414.0 | 0.0017 |
| sokoban2 | 10 | idastar | 1 | 1.0 | 1.0 | 403.0 | 0.0036 |
| sokoban2 | 10 | ilp | 1 | 1.0 | 1.0 | 315.0 | 0.101 |
| sokoban2 | 10 | wastar | 1 | 1.0 | 1.0 | 117.0 | 0.0016 |
| sokoban2 | 11 | astar | 4 | 1.0 | 1.0 | 216.5 | 0.005 |
| sokoban2 | 11 | bfs | 4 | 1.0 | 1.0 | 743.75 | 0.011 |
| sokoban2 | 11 | idastar | 4 | 1.0 | 1.0 | 632.0 | 0.0078 |
| sokoban2 | 11 | ilp | 4 | 1.0 | 1.0 | 424.25 | 0.1804 |
| sokoban2 | 11 | wastar | 4 | 1.0 | 1.0 | 92.0 | 0.0021 |
| sokoban2 | 13 | astar | 1 | 1.0 | 1.0 | 158.0 | 0.0026 |
| sokoban2 | 13 | bfs | 1 | 1.0 | 1.0 | 372.0 | 0.0014 |
| sokoban2 | 13 | idastar | 1 | 1.0 | 1.0 | 749.0 | 0.0064 |
| sokoban2 | 13 | ilp | 1 | 1.0 | 1.0 | 302.0 | 0.1237 |
| sokoban2 | 13 | wastar | 1 | 1.0 | 1.0 | 87.0 | 0.0014 |
| sokoban2 | 15 | astar | 4 | 1.0 | 1.0 | 652.75 | 0.013 |
| sokoban2 | 15 | bfs | 4 | 1.0 | 1.0 | 2774.75 | 0.0127 |
| sokoban2 | 15 | idastar | 4 | 1.0 | 1.0 | 2031.0 | 0.02 |
| sokoban2 | 15 | ilp | 4 | 1.0 | 1.0 | 1319.0 | 0.7686 |
| sokoban2 | 15 | wastar | 4 | 1.0 | 1.0 | 339.5 | 0.006 |
| sokoban2 | 17 | astar | 2 | 1.0 | 1.0 | 779.5 | 0.0191 |
| sokoban2 | 17 | bfs | 2 | 1.0 | 1.0 | 3083.5 | 0.0197 |
| sokoban2 | 17 | idastar | 2 | 1.0 | 1.0 | 3043.5 | 0.0401 |
| sokoban2 | 17 | ilp | 2 | 1.0 | 1.0 | 1434.0 | 0.9295 |
| sokoban2 | 17 | wastar | 2 | 1.0 | 1.0 | 365.0 | 0.0113 |
| sokoban2 | 18 | astar | 1 | 1.0 | 1.0 | 581.0 | 0.0151 |
| sokoban2 | 18 | bfs | 1 | 1.0 | 1.0 | 8243.0 | 0.0669 |
| sokoban2 | 18 | idastar | 1 | 1.0 | 1.0 | 1779.0 | 0.0196 |
| sokoban2 | 18 | ilp | 1 | 1.0 | 1.0 | 1431.0 | 0.8973 |
| sokoban2 | 18 | wastar | 1 | 1.0 | 1.1111 | 247.0 | 0.0056 |
| sokoban2 | 19 | astar | 2 | 1.0 | 1.0 | 1089.0 | 0.0349 |
| sokoban2 | 19 | bfs | 2 | 1.0 | 1.0 | 7699.5 | 0.0642 |
| sokoban2 | 19 | idastar | 2 | 1.0 | 1.0 | 4968.5 | 0.0782 |
| sokoban2 | 19 | ilp | 2 | 1.0 | 1.0 | 2024.5 | 1.8951 |
| sokoban2 | 19 | wastar | 2 | 1.0 | 1.0 | 535.0 | 0.0167 |
| sokoban2 | 21 | astar | 2 | 1.0 | 1.0 | 1128.5 | 0.0191 |
| sokoban2 | 21 | bfs | 2 | 1.0 | 1.0 | 5420.5 | 0.0347 |
| sokoban2 | 21 | idastar | 2 | 1.0 | 1.0 | 9845.5 | 0.0894 |
| sokoban2 | 21 | ilp | 2 | 1.0 | 1.0 | 1461.5 | 0.9732 |
| sokoban2 | 21 | wastar | 2 | 1.0 | 1.0 | 630.5 | 0.0097 |
| sokoban2 | 22 | astar | 2 | 1.0 | 1.0 | 1540.0 | 0.0283 |
| sokoban2 | 22 | bfs | 2 | 1.0 | 1.0 | 9243.0 | 0.0492 |
| sokoban2 | 22 | idastar | 2 | 1.0 | 1.0 | 6881.5 | 0.064 |
| sokoban2 | 22 | ilp | 2 | 1.0 | 1.0 | 2868.0 | 2.614 |
| sokoban2 | 22 | wastar | 2 | 1.0 | 1.0 | 396.5 | 0.008 |
| sokoban2 | 23 | astar | 1 | 1.0 | 1.0 | 1602.0 | 0.0328 |
| sokoban2 | 23 | bfs | 1 | 1.0 | 1.0 | 6468.0 | 0.0302 |
| sokoban2 | 23 | idastar | 1 | 1.0 | 1.0 | 10622.0 | 0.1071 |
| sokoban2 | 23 | ilp | 1 | 1.0 | 1.0 | 1996.0 | 2.4542 |
| sokoban2 | 23 | wastar | 1 | 1.0 | 1.0 | 975.0 | 0.0196 |
| sokoban3 | 9 | astar | 1 | 1.0 | 1.0 | 120.0 | 0.0023 |
| sokoban3 | 9 | bfs | 1 | 1.0 | 1.0 | 159.0 | 0.0006 |
| sokoban3 | 9 | idastar | 1 | 1.0 | 1.0 | 234.0 | 0.0031 |
| sokoban3 | 9 | ilp | 1 | 1.0 | 1.0 | 251.0 | 0.1018 |
| sokoban3 | 9 | wastar | 1 | 1.0 | 1.0 | 74.0 | 0.0015 |
| sokoban3 | 10 | astar | 2 | 1.0 | 1.0 | 103.5 | 0.003 |
| sokoban3 | 10 | bfs | 2 | 1.0 | 1.0 | 436.0 | 0.002 |
| sokoban3 | 10 | idastar | 2 | 1.0 | 1.0 | 200.5 | 0.0034 |
| sokoban3 | 10 | ilp | 2 | 1.0 | 1.0 | 323.5 | 0.1103 |
| sokoban3 | 10 | wastar | 2 | 1.0 | 1.0 | 48.0 | 0.0014 |
| sokoban3 | 11 | astar | 2 | 1.0 | 1.0 | 290.0 | 0.0092 |
| sokoban3 | 11 | bfs | 2 | 1.0 | 1.0 | 781.5 | 0.005 |
| sokoban3 | 11 | idastar | 2 | 1.0 | 1.0 | 827.5 | 0.0151 |
| sokoban3 | 11 | ilp | 2 | 1.0 | 1.0 | 574.0 | 0.3036 |
| sokoban3 | 11 | wastar | 2 | 1.0 | 1.0 | 165.5 | 0.0054 |
| sokoban3 | 13 | astar | 1 | 1.0 | 1.0 | 1051.0 | 0.0274 |
| sokoban3 | 13 | bfs | 1 | 1.0 | 1.0 | 2342.0 | 0.0377 |
| sokoban3 | 13 | idastar | 1 | 1.0 | 1.0 | 2392.0 | 0.0338 |
| sokoban3 | 13 | ilp | 1 | 1.0 | 1.0 | 2516.0 | 1.3262 |
| sokoban3 | 13 | wastar | 1 | 1.0 | 1.0 | 356.0 | 0.007 |
| sokoban3 | 14 | astar | 1 | 1.0 | 1.0 | 308.0 | 0.0079 |
| sokoban3 | 14 | bfs | 1 | 1.0 | 1.0 | 871.0 | 0.0036 |
| sokoban3 | 14 | idastar | 1 | 1.0 | 1.0 | 850.0 | 0.01 |
| sokoban3 | 14 | ilp | 1 | 1.0 | 1.0 | 628.0 | 0.256 |
| sokoban3 | 14 | wastar | 1 | 1.0 | 1.0 | 170.0 | 0.0044 |
| sokoban3 | 15 | astar | 3 | 1.0 | 1.0 | 1053.3333 | 0.0346 |
| sokoban3 | 15 | bfs | 3 | 1.0 | 1.0 | 6454.3333 | 0.0536 |
| sokoban3 | 15 | idastar | 3 | 1.0 | 1.0 | 3443.6667 | 0.0448 |
| sokoban3 | 15 | ilp | 3 | 1.0 | 1.0 | 2374.3333 | 1.9316 |
| sokoban3 | 15 | wastar | 3 | 1.0 | 1.0 | 383.3333 | 0.01 |
| sokoban3 | 17 | astar | 3 | 1.0 | 1.0 | 2316.3333 | 0.0703 |
| sokoban3 | 17 | bfs | 3 | 1.0 | 1.0 | 20231.0 | 0.1591 |
| sokoban3 | 17 | idastar | 3 | 1.0 | 1.0 | 7230.6667 | 0.0972 |
| sokoban3 | 17 | ilp | 3 | 0.6667 | 1.0 | 5297.6667 | 4.4256 |
| sokoban3 | 17 | wastar | 3 | 1.0 | 1.0196 | 831.6667 | 0.024 |
| sokoban3 | 18 | astar | 1 | 1.0 | 1.0 | 1903.0 | 0.0597 |
| sokoban3 | 18 | bfs | 1 | 1.0 | 1.0 | 29731.0 | 0.2448 |
| sokoban3 | 18 | idastar | 1 | 1.0 | 1.0 | 5781.0 | 0.0881 |
| sokoban3 | 18 | ilp | 1 | 1.0 | 1.0 | 4737.0 | 3.7745 |
| sokoban3 | 18 | wastar | 1 | 1.0 | 1.0 | 488.0 | 0.0139 |
| sokoban3 | 19 | astar | 1 | 1.0 | 1.0 | 2203.0 | 0.0515 |
| sokoban3 | 19 | bfs | 1 | 1.0 | 1.0 | 8095.0 | 0.0368 |
| sokoban3 | 19 | idastar | 1 | 1.0 | 1.0 | 7120.0 | 0.123 |
| sokoban3 | 19 | ilp | 1 | 1.0 | 1.0 | 4068.0 | 5.1482 |
| sokoban3 | 19 | wastar | 1 | 1.0 | 1.0 | 724.0 | 0.0168 |
| sokoban3 | 22 | astar | 4 | 1.0 | 1.0 | 9293.75 | 0.2683 |
| sokoban3 | 22 | bfs | 4 | 1.0 | 1.0 | 103785.5 | 0.7276 |
| sokoban3 | 22 | idastar | 4 | 1.0 | 1.0 | 43077.25 | 0.6329 |
| sokoban3 | 22 | ilp | 4 | 0.25 | 1.0 | 16931.0 | 12.7469 |
| sokoban3 | 22 | wastar | 4 | 1.0 | 1.0 | 2901.0 | 0.0813 |
| sokoban3 | 23 | astar | 1 | 1.0 | 1.0 | 3310.0 | 0.0786 |
| sokoban3 | 23 | bfs | 1 | 1.0 | 1.0 | 48603.0 | 0.3299 |
| sokoban3 | 23 | idastar | 1 | 1.0 | 1.0 | 17835.0 | 0.2556 |
| sokoban3 | 23 | ilp | 1 | 1.0 | 1.0 | 5690.0 | 7.3905 |
| sokoban3 | 23 | wastar | 1 | 1.0 | 1.0 | 1882.0 | 0.0432 |
| sokoban3 | 25 | astar | 1 | 1.0 | 1.0 | 5144.0 | 0.1266 |
| sokoban3 | 25 | bfs | 1 | 1.0 | 1.0 | 94660.0 | 0.6754 |
| sokoban3 | 25 | idastar | 1 | 1.0 | 1.0 | 36789.0 | 0.5139 |
| sokoban3 | 25 | ilp | 1 | 0.0 |  | 8318.0 | 10.7836 |
| sokoban3 | 25 | wastar | 1 | 1.0 | 1.0 | 1464.0 | 0.0335 |
| sokoban3 | 26 | astar | 3 | 1.0 | 1.0 | 17750.0 | 0.5458 |
| sokoban3 | 26 | bfs | 3 | 1.0 | 1.0 | 152342.3333 | 1.1039 |
| sokoban3 | 26 | idastar | 3 | 1.0 | 1.0 | 119824.0 | 1.6313 |
| sokoban3 | 26 | ilp | 3 | 0.0 |  | 28317.6667 | 14.8876 |
| sokoban3 | 26 | wastar | 3 | 1.0 | 1.0 | 6726.0 | 0.1811 |
| sokoban3 | 27 | astar | 1 | 1.0 | 1.0 | 30700.0 | 0.8855 |
| sokoban3 | 27 | bfs | 1 | 1.0 | 1.0 | 368377.0 | 2.6001 |
| sokoban3 | 27 | idastar | 1 | 1.0 | 1.0 | 309075.0 | 3.9342 |
| sokoban3 | 27 | ilp | 1 | 0.0 |  | 49541.0 | 19.3718 |
| sokoban3 | 27 | wastar | 1 | 1.0 | 1.0 | 11642.0 | 0.3125 |

## Agents (success within budget under noise)

_no data_

## Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R, or (T=-1) a user-supplied level skipped by the oracle: status = the oracle status or already_solved; cost means are over solved instances only)

_no data_

## Failure breakdown: solvers (count of rows per status)

| bench | solver | n | ok | node_limit | too_large | timeout |
|---|---|---|---|---|---|---|
| cube3 | astar | 20 | 20 | 0 | 0 | 0 |
| cube3 | bfs | 20 | 10 | 10 | 0 | 0 |
| cube3 | idastar | 20 | 20 | 0 | 0 | 0 |
| cube3 | ilp | 20 | 16 | 0 | 4 | 0 |
| cube3 | wastar | 20 | 19 | 1 | 0 | 0 |
| sokoban2 | astar | 25 | 25 | 0 | 0 | 0 |
| sokoban2 | bfs | 25 | 25 | 0 | 0 | 0 |
| sokoban2 | idastar | 25 | 25 | 0 | 0 | 0 |
| sokoban2 | ilp | 25 | 25 | 0 | 0 | 0 |
| sokoban2 | wastar | 25 | 25 | 0 | 0 | 0 |
| sokoban3 | astar | 25 | 25 | 0 | 0 | 0 |
| sokoban3 | bfs | 25 | 25 | 0 | 0 | 0 |
| sokoban3 | idastar | 25 | 25 | 0 | 0 | 0 |
| sokoban3 | ilp | 25 | 16 | 0 | 0 | 9 |
| sokoban3 | wastar | 25 | 25 | 0 | 0 | 0 |

## Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

_no data_

ILP status on skipped-infeasible constrained rows (ilp_status recorded for 0 of 0; ilp_status = ok would mean the ILP found a path where A* proved none): none recorded

## Agents: success per (bench, T*, method) with 95% Wilson intervals (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1 or no success value).

## Agents: pooled per benchmark (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval; the interval treats the trials as independent, although the episodes of one instance share a level)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1 or no success value).

## Paired differences in success (mean over instances of success_ours_astar - success_other; 95% percentile bootstrap, B = 2000, resampled over instances, paired by instance)

_no data_

Excluded from the intervals: 0 skipped rows (T = -1 or no success value).
