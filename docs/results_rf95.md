# Supplementary: constrained at res_frac 0.95, 0.97 and 1.0 (Sokoban and Boxoban, --n 5)

Generated with `python -m tapegraph.bench constrained --bench {sokoban,boxoban} --n 5 --res_frac X --out results_rfNN` and `report --out results_rfNN`. Same instances as the main run (seed 1). `skipped` rows are instances whose resource budget is infeasible. 1.0 is non-binding by construction (budget = the optimum's own resource).

## res_frac 0.95

### Constrained (length + resource budget; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)

| bench | T | solver | n | ok | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|
| boxoban | 7 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 8 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 9 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 11 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 12 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 13 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 15 | skipped | 2 | 0.0 |  |  |  |  |
| boxoban | 16 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 19 | skipped | 2 | 0.0 |  |  |  |  |
| boxoban | 21 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 5 | skipped | 1 | 0.0 |  |  |  |  |
| sokoban | 6 | skipped | 1 | 0.0 |  |  |  |  |
| sokoban | 7 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 9 | skipped | 5 | 0.0 |  |  |  |  |
| sokoban | 14 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 15 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 17 | astar | 1 | 1.0 | 1.0 | 19.0 | 243.0 | 0.0047 |
| sokoban | 17 | ilp | 1 | 1.0 | 1.0 | 19.0 | 245.0 | 0.1458 |
| sokoban | 17 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 18 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 21 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 23 | skipped | 2 | 0.0 |  |  |  |  |

### Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | infeasible |
|---|---|---|---|---|
| boxoban | skipped | 20 | 0 | 20 |
| sokoban | astar | 1 | 1 | 0 |
| sokoban | ilp | 1 | 1 | 0 |
| sokoban | skipped | 24 | 0 | 24 |

## res_frac 0.97

### Constrained (length + resource budget; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)

| bench | T | solver | n | ok | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|
| boxoban | 7 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 8 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 9 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 11 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 12 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 13 | skipped | 1 | 0.0 |  |  |  |  |
| boxoban | 15 | skipped | 2 | 0.0 |  |  |  |  |
| boxoban | 16 | skipped | 3 | 0.0 |  |  |  |  |
| boxoban | 19 | skipped | 2 | 0.0 |  |  |  |  |
| boxoban | 21 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 5 | skipped | 1 | 0.0 |  |  |  |  |
| sokoban | 6 | skipped | 1 | 0.0 |  |  |  |  |
| sokoban | 7 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 9 | skipped | 5 | 0.0 |  |  |  |  |
| sokoban | 14 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 15 | skipped | 3 | 0.0 |  |  |  |  |
| sokoban | 17 | astar | 1 | 1.0 | 1.0 | 19.0 | 245.0 | 0.0068 |
| sokoban | 17 | ilp | 1 | 1.0 | 1.0 | 19.0 | 245.0 | 0.1695 |
| sokoban | 17 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 18 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 21 | astar | 1 | 1.0 | 1.0 | 23.0 | 351.0 | 0.0064 |
| sokoban | 21 | ilp | 1 | 1.0 | 1.0 | 23.0 | 348.0 | 0.2092 |
| sokoban | 21 | skipped | 2 | 0.0 |  |  |  |  |
| sokoban | 23 | skipped | 2 | 0.0 |  |  |  |  |

### Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | infeasible |
|---|---|---|---|---|
| boxoban | skipped | 20 | 0 | 20 |
| sokoban | astar | 2 | 2 | 0 |
| sokoban | ilp | 2 | 2 | 0 |
| sokoban | skipped | 23 | 0 | 23 |

## res_frac 1.0

### Constrained (length + resource budget; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R; cost means are over solved instances only)

| bench | T | solver | n | ok | agrees_with_astar | cost | nodes | seconds |
|---|---|---|---|---|---|---|---|---|
| boxoban | 7 | astar | 3 | 1.0 | 1.0 | 7.0 | 59.3333 | 0.0027 |
| boxoban | 7 | ilp | 3 | 1.0 | 1.0 | 7.0 | 172.6667 | 0.0888 |
| boxoban | 8 | astar | 1 | 1.0 | 1.0 | 8.0 | 50.0 | 0.0021 |
| boxoban | 8 | ilp | 1 | 1.0 | 1.0 | 8.0 | 115.0 | 0.0505 |
| boxoban | 9 | astar | 1 | 1.0 | 1.0 | 9.0 | 137.0 | 0.0064 |
| boxoban | 9 | ilp | 1 | 1.0 | 1.0 | 9.0 | 410.0 | 0.2975 |
| boxoban | 11 | astar | 1 | 1.0 | 1.0 | 11.0 | 230.0 | 0.0073 |
| boxoban | 11 | ilp | 1 | 1.0 | 1.0 | 11.0 | 514.0 | 0.3481 |
| boxoban | 12 | astar | 3 | 1.0 | 1.0 | 12.0 | 987.3333 | 0.047 |
| boxoban | 12 | ilp | 3 | 1.0 | 1.0 | 12.0 | 2892.0 | 3.05 |
| boxoban | 13 | astar | 1 | 1.0 | 1.0 | 13.0 | 213.0 | 0.011 |
| boxoban | 13 | ilp | 1 | 1.0 | 1.0 | 13.0 | 455.0 | 0.274 |
| boxoban | 15 | astar | 2 | 1.0 | 1.0 | 15.0 | 1011.0 | 0.0298 |
| boxoban | 15 | ilp | 2 | 1.0 | 1.0 | 15.0 | 2207.0 | 2.711 |
| boxoban | 16 | astar | 3 | 1.0 | 1.0 | 16.0 | 3505.0 | 0.1809 |
| boxoban | 16 | ilp | 3 | 0.0 | 0.0 |  | 9854.3333 | 11.779 |
| boxoban | 19 | astar | 2 | 1.0 | 1.0 | 19.0 | 6626.5 | 0.3243 |
| boxoban | 19 | ilp | 2 | 0.5 | 0.5 | 19.0 | 15530.0 | 10.0527 |
| boxoban | 21 | astar | 3 | 1.0 | 1.0 | 21.0 | 6483.6667 | 0.2782 |
| boxoban | 21 | ilp | 3 | 0.3333 | 0.3333 | 21.0 | 14660.6667 | 11.3149 |
| sokoban | 5 | astar | 1 | 1.0 | 1.0 | 5.0 | 15.0 | 0.0003 |
| sokoban | 5 | ilp | 1 | 1.0 | 1.0 | 5.0 | 39.0 | 0.0287 |
| sokoban | 6 | astar | 1 | 1.0 | 1.0 | 6.0 | 30.0 | 0.0006 |
| sokoban | 6 | ilp | 1 | 1.0 | 1.0 | 6.0 | 34.0 | 0.0296 |
| sokoban | 7 | astar | 3 | 1.0 | 1.0 | 7.0 | 23.0 | 0.0004 |
| sokoban | 7 | ilp | 3 | 1.0 | 1.0 | 7.0 | 54.0 | 0.0284 |
| sokoban | 9 | astar | 5 | 1.0 | 1.0 | 9.0 | 51.2 | 0.001 |
| sokoban | 9 | ilp | 5 | 1.0 | 1.0 | 9.0 | 101.0 | 0.0477 |
| sokoban | 14 | astar | 2 | 1.0 | 1.0 | 14.0 | 79.0 | 0.001 |
| sokoban | 14 | ilp | 2 | 1.0 | 1.0 | 14.0 | 127.0 | 0.0574 |
| sokoban | 15 | astar | 3 | 1.0 | 1.0 | 15.0 | 84.0 | 0.0013 |
| sokoban | 15 | ilp | 3 | 1.0 | 1.0 | 15.0 | 203.0 | 0.0924 |
| sokoban | 17 | astar | 3 | 1.0 | 1.0 | 17.0 | 97.3333 | 0.0017 |
| sokoban | 17 | ilp | 3 | 1.0 | 1.0 | 17.0 | 215.6667 | 0.1398 |
| sokoban | 18 | astar | 2 | 1.0 | 1.0 | 18.0 | 121.0 | 0.0016 |
| sokoban | 18 | ilp | 2 | 1.0 | 1.0 | 18.0 | 211.5 | 0.1428 |
| sokoban | 21 | astar | 3 | 1.0 | 1.0 | 21.0 | 211.3333 | 0.0038 |
| sokoban | 21 | ilp | 3 | 1.0 | 1.0 | 21.0 | 312.3333 | 0.2344 |
| sokoban | 23 | astar | 2 | 1.0 | 1.0 | 23.0 | 231.0 | 0.0047 |
| sokoban | 23 | ilp | 2 | 1.0 | 1.0 | 23.0 | 292.0 | 0.2006 |

### Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

| bench | solver | n | ok | timeout |
|---|---|---|---|---|
| boxoban | astar | 20 | 20 | 0 |
| boxoban | ilp | 20 | 14 | 6 |
| sokoban | astar | 25 | 25 | 0 |
| sokoban | ilp | 25 | 25 | 0 |
