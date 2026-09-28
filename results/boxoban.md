# Boxoban benchmark (1000 levels, 10x10, 4 boxes, medium_valid_000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 14% [12%, 16%] | 23% [20%, 26%] | 91 | 0 |
| 5,000 | 29% [26%, 32%] | 45% [42%, 48%] | 160 | 0 |
| 10,000 | 46% [43%, 49%] | 65% [62%, 68%] | 193 | 0 |
| 20,000 | 61% [58%, 64%] | 82% [79%, 84%] | 212 | 0 |
| 30,000 | 71% [68%, 74%] | 88% [86%, 90%] | 170 | 0 |

Mean nodes expanded per level at the full budget: plain 90,019, prune 67,190 (25% fewer).

## Merging plans (prune arm)

Levels solved: 882. The merged path is shorter than the best single plan on 0 levels and longer on 9.
