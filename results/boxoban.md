# Boxoban benchmark (200 levels, 10x10, 4 boxes, medium/valid/000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 14% [9%, 19%] | 22% [17%, 28%] | 17 | 0 |
| 5,000 | 26% [21%, 33%] | 41% [34%, 48%] | 29 | 0 |
| 10,000 | 43% [36%, 50%] | 64% [57%, 70%] | 42 | 0 |
| 20,000 | 57% [50%, 64%] | 82% [76%, 87%] | 50 | 0 |
| 30,000 | 70% [63%, 76%] | 88% [83%, 92%] | 36 | 0 |

Mean nodes expanded per level at the full budget: plain 91,606, prune 69,002 (25% fewer).

## Merging plans (prune arm)

Levels solved: 176. The merged path is shorter than the best single plan on 0 levels and longer on 2.
