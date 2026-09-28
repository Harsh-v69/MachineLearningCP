# Boxoban benchmark (200 levels, 10x10, 4 boxes, unfiltered_valid_000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 51% [44%, 58%] | 58% [52%, 65%] | 15 | 0 |
| 5,000 | 70% [63%, 75%] | 82% [77%, 87%] | 26 | 0 |
| 10,000 | 84% [78%, 88%] | 90% [85%, 93%] | 13 | 0 |
| 20,000 | 90% [86%, 94%] | 96% [92%, 98%] | 11 | 0 |
| 30,000 | 95% [91%, 97%] | 98% [96%, 99%] | 7 | 0 |

Mean nodes expanded per level at the full budget: plain 57,637, prune 46,772 (19% fewer).

## Merging plans (prune arm)

Levels solved: 197. The merged path is shorter than the best single plan on 0 levels and longer on 6.
