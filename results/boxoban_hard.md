# Boxoban benchmark (1000 levels, 10x10, 4 boxes, hard_000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 6% [5%, 8%] | 13% [11%, 15%] | 70 | 0 |
| 5,000 | 16% [13%, 18%] | 29% [26%, 32%] | 134 | 0 |
| 10,000 | 27% [24%, 30%] | 49% [46%, 52%] | 224 | 0 |
| 20,000 | 44% [41%, 47%] | 70% [67%, 73%] | 263 | 0 |
| 30,000 | 54% [51%, 57%] | 82% [79%, 84%] | 281 | 0 |

Mean nodes expanded per level at the full budget: plain 100,427, prune 76,852 (23% fewer).

## Merging plans (prune arm)

Levels solved: 817. The merged path is shorter than the best single plan on 0 levels and longer on 5.
