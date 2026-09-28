# ScoreWeights tuning (objective = replans + 3*(1-success), lower is better)

Grid 80 points on train seeds 0..7; held-out seeds 100..115.

## Top 5 on train

| regression | confidence | budget | train objective |
|---|---|---|---|
| 0.0 | 16.0 | 2.0 | 3.906 |
| 3.0 | 4.0 | 0.0 | 3.961 |
| 0.0 | 16.0 | 4.0 | 3.967 |
| 0.0 | 2.0 | 1.0 | 3.975 |
| 0.75 | 16.0 | 1.0 | 4.036 |

Default (1.5, 4.0, 2.0): train objective 4.219 (rank 23/80); worst grid point 5.117.

## Held-out: candidate vs default (paired over seeds; negative diff = candidate better)

| regression | confidence | budget | held-out objective | diff vs default (mean +/- SE) |
|---|---|---|---|---|
| 0.0 | 16.0 | 2.0 | 4.298 | +0.122 +/- 0.111 |
| 3.0 | 4.0 | 0.0 | 4.098 | -0.078 +/- 0.123 |
| 0.0 | 16.0 | 4.0 | 4.287 | +0.112 +/- 0.167 |
| default (1.5, 4.0, 2.0) | | | 4.176 | 0 |
