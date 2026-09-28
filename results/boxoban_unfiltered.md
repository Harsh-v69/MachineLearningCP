# Boxoban benchmark (1000 levels, 10x10, 4 boxes, unfiltered_valid_000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 57% [54%, 60%] | 65% [62%, 68%] | 84 | 0 |
| 5,000 | 73% [70%, 75%] | 82% [80%, 84%] | 93 | 0 |
| 10,000 | 84% [81%, 86%] | 92% [90%, 93%] | 78 | 0 |
| 20,000 | 92% [90%, 93%] | 96% [95%, 97%] | 47 | 0 |
| 30,000 | 95% [94%, 96%] | 98% [97%, 99%] | 29 | 0 |

Mean nodes expanded per level at the full budget: plain 55,554, prune 44,618 (20% fewer).

## Merging plans (prune arm)

Levels solved: 981. The merged path is shorter than the best single plan on 1 levels (mean 2.0 moves saved) and longer on 19.
