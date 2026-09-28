# Boxoban benchmark (200 levels, 10x10, 4 boxes, hard_000)

Proposer: weighted A* with weights 1, 2, 4, 8 and a per-search node budget.

## Solve rate by node budget (any of the four searches finds a plan)

| budget | plain | prune | levels only prune solves | levels only plain solves |
|---|---|---|---|---|
| 2,000 | 6% [3%, 10%] | 14% [10%, 19%] | 17 | 0 |
| 5,000 | 16% [12%, 22%] | 32% [26%, 39%] | 32 | 0 |
| 10,000 | 30% [24%, 36%] | 57% [51%, 64%] | 56 | 0 |
| 20,000 | 49% [42%, 56%] | 74% [67%, 79%] | 49 | 0 |
| 30,000 | 57% [51%, 64%] | 84% [78%, 88%] | 52 | 0 |

Mean nodes expanded per level at the full budget: plain 98,436, prune 72,224 (27% fewer).

## Merging plans (prune arm)

Levels solved: 167. The merged path is shorter than the best single plan on 0 levels and longer on 0.
