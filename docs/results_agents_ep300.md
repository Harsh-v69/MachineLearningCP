# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

_no data_

## Agents (success within budget under noise)

| bench | T | method | n | success | mean_steps | solves | solver_fail | seconds |
|---|---|---|---|---|---|---|---|---|
| river | 4 | ours_astar | 5 | 0.9933 | 4.224 | 1.1493 | 0.0067 | 0.0003 |
| river | 4 | ours_ilp | 5 | 0.9927 | 4.204 | 1.1507 | 0.0093 | 0.0265 |
| river | 4 | react | 5 | 0.76 | 4.948 | 0.0 | 0.0 | 0.0001 |
| river | 4 | tape | 5 | 0.9927 | 4.22 | 1.1513 | 0.0 | 0.015 |
| river | 6 | ours_astar | 5 | 0.9813 | 6.3373 | 1.2553 | 0.036 | 0.0004 |
| river | 6 | ours_ilp | 5 | 0.988 | 6.2627 | 1.2533 | 0.0313 | 0.032 |
| river | 6 | react | 5 | 0.6413 | 7.2213 | 0.0 | 0.0 | 0.0002 |
| river | 6 | tape | 5 | 0.9787 | 6.3467 | 1.258 | 0.0 | 0.0178 |
| river | 8 | ours_astar | 5 | 0.956 | 8.5107 | 1.4193 | 0.11 | 0.0006 |
| river | 8 | ours_ilp | 5 | 0.964 | 8.5107 | 1.4107 | 0.0927 | 0.0392 |
| river | 8 | react | 5 | 0.4693 | 9.516 | 0.0 | 0.0 | 0.0002 |
| river | 8 | tape | 5 | 0.956 | 8.5027 | 1.42 | 0.0 | 0.0209 |
| river | 10 | ours_astar | 5 | 0.9367 | 10.5947 | 1.5667 | 0.2247 | 0.0009 |
| river | 10 | ours_ilp | 5 | 0.9473 | 10.544 | 1.5587 | 0.208 | 0.049 |
| river | 10 | react | 5 | 0.3447 | 11.7 | 0.0 | 0.0 | 0.0003 |
| river | 10 | tape | 5 | 0.9367 | 10.5907 | 1.5807 | 0.0 | 0.0224 |
| river | 12 | ours_astar | 5 | 0.9147 | 12.7093 | 1.7487 | 0.3233 | 0.0009 |
| river | 12 | ours_ilp | 5 | 0.9273 | 12.6453 | 1.7293 | 0.2927 | 0.0503 |
| river | 12 | react | 5 | 0.286 | 13.752 | 0.0 | 0.0 | 0.0003 |
| river | 12 | tape | 5 | 0.9133 | 12.708 | 1.7653 | 0.0 | 0.0259 |
| river | 14 | ours_astar | 5 | 0.946 | 14.5907 | 1.658 | 0.2407 | 0.0009 |
| river | 14 | ours_ilp | 5 | 0.9427 | 14.5733 | 1.6953 | 0.2813 | 0.0522 |
| river | 14 | react | 5 | 0.266 | 15.772 | 0.0 | 0.0 | 0.0003 |
| river | 14 | tape | 5 | 0.9353 | 14.6413 | 1.732 | 0.0 | 0.0267 |
| sokoban | 5 | ours_astar | 1 | 0.9633 | 5.3467 | 1.2567 | 0.1033 | 0.0003 |
| sokoban | 5 | ours_ilp | 1 | 0.9633 | 5.3467 | 1.2567 | 0.1033 | 0.0181 |
| sokoban | 5 | react | 1 | 0.6433 | 6.2 | 0.0 | 0.0 | 0.0001 |
| sokoban | 5 | tape | 1 | 0.9633 | 5.3467 | 1.2567 | 0.0 | 0.0131 |
| sokoban | 6 | ours_astar | 1 | 0.96 | 6.4067 | 1.2767 | 0.07 | 0.0006 |
| sokoban | 6 | ours_ilp | 1 | 0.96 | 6.4067 | 1.2767 | 0.07 | 0.0297 |
| sokoban | 6 | react | 1 | 0.5633 | 7.4133 | 0.0 | 0.0 | 0.0001 |
| sokoban | 6 | tape | 1 | 0.96 | 6.4 | 1.2767 | 0.0 | 0.0136 |
| sokoban | 7 | ours_astar | 3 | 0.9544 | 7.4689 | 1.3622 | 0.1367 | 0.0005 |
| sokoban | 7 | ours_ilp | 3 | 0.9544 | 7.4689 | 1.3622 | 0.1367 | 0.0293 |
| sokoban | 7 | react | 3 | 0.4844 | 8.5044 | 0.0 | 0.0 | 0.0001 |
| sokoban | 7 | tape | 3 | 0.9556 | 7.4644 | 1.3622 | 0.0 | 0.0162 |
| sokoban | 9 | ours_astar | 5 | 0.938 | 9.5773 | 1.52 | 0.2147 | 0.001 |
| sokoban | 9 | ours_ilp | 5 | 0.9387 | 9.5773 | 1.518 | 0.212 | 0.0502 |
| sokoban | 9 | react | 5 | 0.3687 | 10.6893 | 0.0 | 0.0 | 0.0002 |
| sokoban | 9 | tape | 5 | 0.94 | 9.584 | 1.5167 | 0.0 | 0.0194 |
| sokoban | 14 | ours_astar | 2 | 0.8383 | 14.8867 | 2.32 | 0.8733 | 0.0015 |
| sokoban | 14 | ours_ilp | 2 | 0.8383 | 14.8933 | 2.3033 | 0.8517 | 0.0606 |
| sokoban | 14 | react | 2 | 0.17 | 15.8933 | 0.0 | 0.0 | 0.0002 |
| sokoban | 14 | tape | 2 | 0.8367 | 14.89 | 2.4017 | 0.0 | 0.0236 |
| sokoban | 15 | ours_astar | 3 | 0.8289 | 15.9156 | 2.3822 | 0.8956 | 0.0019 |
| sokoban | 15 | ours_ilp | 3 | 0.8344 | 15.92 | 2.32 | 0.8222 | 0.0868 |
| sokoban | 15 | react | 3 | 0.1556 | 16.8933 | 0.0 | 0.0 | 0.0003 |
| sokoban | 15 | tape | 3 | 0.8289 | 15.92 | 2.4978 | 0.0 | 0.0264 |
| sokoban | 17 | ours_astar | 3 | 0.8378 | 17.9378 | 2.4378 | 0.9356 | 0.002 |
| sokoban | 17 | ours_ilp | 3 | 0.8467 | 17.9244 | 2.3944 | 0.8844 | 0.0916 |
| sokoban | 17 | react | 3 | 0.1156 | 18.9333 | 0.0 | 0.0 | 0.0003 |
| sokoban | 17 | tape | 3 | 0.83 | 17.94 | 2.6867 | 0.0 | 0.0267 |
| sokoban | 18 | ours_astar | 2 | 0.8333 | 18.9733 | 2.4733 | 0.9183 | 0.0026 |
| sokoban | 18 | ours_ilp | 2 | 0.825 | 18.9467 | 2.57 | 1.0283 | 0.1286 |
| sokoban | 18 | react | 2 | 0.115 | 19.94 | 0.0 | 0.0 | 0.0003 |
| sokoban | 18 | tape | 2 | 0.8233 | 18.9667 | 2.85 | 0.0 | 0.0276 |
| sokoban | 21 | ours_astar | 3 | 0.7711 | 22.1222 | 3.4322 | 1.8533 | 0.0044 |
| sokoban | 21 | ours_ilp | 3 | 0.7689 | 22.1089 | 3.4411 | 1.8644 | 0.1643 |
| sokoban | 21 | react | 3 | 0.06 | 22.9489 | 0.0 | 0.0 | 0.0006 |
| sokoban | 21 | tape | 3 | 0.73 | 22.1444 | 4.6256 | 0.0 | 0.0329 |
| sokoban | 23 | ours_astar | 2 | 0.7817 | 24.1433 | 3.695 | 2.085 | 0.005 |
| sokoban | 23 | ours_ilp | 2 | 0.7717 | 24.1467 | 3.8483 | 2.25 | 0.154 |
| sokoban | 23 | react | 2 | 0.0417 | 24.98 | 0.0 | 0.0 | 0.0005 |
| sokoban | 23 | tape | 2 | 0.7317 | 24.19 | 5.2967 | 0.0 | 0.0354 |

## Constrained (design=bind: B = T*+c_slack, level bind: R = r_opt-1, tight: R = r_min, so the optimum must be longer than T*; design=frac: R = floor(res_frac * optimum resource), level frac; forced_longer = share of solved rows with cost > T*; agrees_with_astar = rate of both solved with identical cost; solver=skipped rows are instances with no derivable or feasible R, or (T=-1) a user-supplied level skipped by the oracle: status = the oracle status or already_solved; cost means are over solved instances only)

_no data_

## Failure breakdown: solvers (count of rows per status)

_no data_

## Failure breakdown: constrained (count of rows per status; skipped = no derivable/feasible R)

_no data_

ILP status on skipped-infeasible constrained rows (ilp_status recorded for 0 of 0; ilp_status = ok would mean the ILP found a path where A* proved none): none recorded

## Agents: success per (bench, T*, method) with 95% Wilson intervals (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval)

| bench | T | method | instances | successes | trials | success | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|
| river | 4 | ours_astar | 5 | 1490 | 1500 | 0.9933 | 0.9878 | 0.9964 |
| river | 4 | ours_ilp | 5 | 1489 | 1500 | 0.9927 | 0.9869 | 0.9959 |
| river | 4 | react | 5 | 1140 | 1500 | 0.7600 | 0.7377 | 0.7809 |
| river | 4 | tape | 5 | 1489 | 1500 | 0.9927 | 0.9869 | 0.9959 |
| river | 6 | ours_astar | 5 | 1472 | 1500 | 0.9813 | 0.9732 | 0.9871 |
| river | 6 | ours_ilp | 5 | 1482 | 1500 | 0.9880 | 0.9811 | 0.9924 |
| river | 6 | react | 5 | 962 | 1500 | 0.6413 | 0.6167 | 0.6652 |
| river | 6 | tape | 5 | 1468 | 1500 | 0.9787 | 0.9700 | 0.9848 |
| river | 8 | ours_astar | 5 | 1434 | 1500 | 0.9560 | 0.9444 | 0.9653 |
| river | 8 | ours_ilp | 5 | 1446 | 1500 | 0.9640 | 0.9533 | 0.9723 |
| river | 8 | react | 5 | 704 | 1500 | 0.4693 | 0.4442 | 0.4946 |
| river | 8 | tape | 5 | 1434 | 1500 | 0.9560 | 0.9444 | 0.9653 |
| river | 10 | ours_astar | 5 | 1405 | 1500 | 0.9367 | 0.9232 | 0.9479 |
| river | 10 | ours_ilp | 5 | 1421 | 1500 | 0.9473 | 0.9348 | 0.9575 |
| river | 10 | react | 5 | 517 | 1500 | 0.3447 | 0.3210 | 0.3691 |
| river | 10 | tape | 5 | 1405 | 1500 | 0.9367 | 0.9232 | 0.9479 |
| river | 12 | ours_astar | 5 | 1372 | 1500 | 0.9147 | 0.8994 | 0.9278 |
| river | 12 | ours_ilp | 5 | 1391 | 1500 | 0.9273 | 0.9131 | 0.9394 |
| river | 12 | react | 5 | 429 | 1500 | 0.2860 | 0.2637 | 0.3094 |
| river | 12 | tape | 5 | 1370 | 1500 | 0.9133 | 0.8980 | 0.9265 |
| river | 14 | ours_astar | 5 | 1419 | 1500 | 0.9460 | 0.9334 | 0.9563 |
| river | 14 | ours_ilp | 5 | 1414 | 1500 | 0.9427 | 0.9297 | 0.9533 |
| river | 14 | react | 5 | 399 | 1500 | 0.2660 | 0.2443 | 0.2889 |
| river | 14 | tape | 5 | 1403 | 1500 | 0.9353 | 0.9217 | 0.9467 |
| sokoban | 5 | ours_astar | 1 | 289 | 300 | 0.9633 | 0.9355 | 0.9794 |
| sokoban | 5 | ours_ilp | 1 | 289 | 300 | 0.9633 | 0.9355 | 0.9794 |
| sokoban | 5 | react | 1 | 193 | 300 | 0.6433 | 0.5876 | 0.6954 |
| sokoban | 5 | tape | 1 | 289 | 300 | 0.9633 | 0.9355 | 0.9794 |
| sokoban | 6 | ours_astar | 1 | 288 | 300 | 0.9600 | 0.9314 | 0.9770 |
| sokoban | 6 | ours_ilp | 1 | 288 | 300 | 0.9600 | 0.9314 | 0.9770 |
| sokoban | 6 | react | 1 | 169 | 300 | 0.5633 | 0.5068 | 0.6183 |
| sokoban | 6 | tape | 1 | 288 | 300 | 0.9600 | 0.9314 | 0.9770 |
| sokoban | 7 | ours_astar | 3 | 859 | 900 | 0.9544 | 0.9388 | 0.9662 |
| sokoban | 7 | ours_ilp | 3 | 859 | 900 | 0.9544 | 0.9388 | 0.9662 |
| sokoban | 7 | react | 3 | 436 | 900 | 0.4844 | 0.4519 | 0.5171 |
| sokoban | 7 | tape | 3 | 860 | 900 | 0.9556 | 0.9400 | 0.9672 |
| sokoban | 9 | ours_astar | 5 | 1407 | 1500 | 0.9380 | 0.9246 | 0.9491 |
| sokoban | 9 | ours_ilp | 5 | 1408 | 1500 | 0.9387 | 0.9254 | 0.9497 |
| sokoban | 9 | react | 5 | 553 | 1500 | 0.3687 | 0.3446 | 0.3934 |
| sokoban | 9 | tape | 5 | 1410 | 1500 | 0.9400 | 0.9268 | 0.9509 |
| sokoban | 14 | ours_astar | 2 | 503 | 600 | 0.8383 | 0.8067 | 0.8656 |
| sokoban | 14 | ours_ilp | 2 | 503 | 600 | 0.8383 | 0.8067 | 0.8656 |
| sokoban | 14 | react | 2 | 102 | 600 | 0.1700 | 0.1421 | 0.2021 |
| sokoban | 14 | tape | 2 | 502 | 600 | 0.8367 | 0.8050 | 0.8641 |
| sokoban | 15 | ours_astar | 3 | 746 | 900 | 0.8289 | 0.8029 | 0.8521 |
| sokoban | 15 | ours_ilp | 3 | 751 | 900 | 0.8344 | 0.8087 | 0.8573 |
| sokoban | 15 | react | 3 | 140 | 900 | 0.1556 | 0.1333 | 0.1807 |
| sokoban | 15 | tape | 3 | 746 | 900 | 0.8289 | 0.8029 | 0.8521 |
| sokoban | 17 | ours_astar | 3 | 754 | 900 | 0.8378 | 0.8123 | 0.8604 |
| sokoban | 17 | ours_ilp | 3 | 762 | 900 | 0.8467 | 0.8217 | 0.8687 |
| sokoban | 17 | react | 3 | 104 | 900 | 0.1156 | 0.0963 | 0.1381 |
| sokoban | 17 | tape | 3 | 747 | 900 | 0.8300 | 0.8041 | 0.8531 |
| sokoban | 18 | ours_astar | 2 | 500 | 600 | 0.8333 | 0.8014 | 0.8610 |
| sokoban | 18 | ours_ilp | 2 | 495 | 600 | 0.8250 | 0.7926 | 0.8533 |
| sokoban | 18 | react | 2 | 69 | 600 | 0.1150 | 0.0919 | 0.1430 |
| sokoban | 18 | tape | 2 | 494 | 600 | 0.8233 | 0.7908 | 0.8518 |
| sokoban | 21 | ours_astar | 3 | 694 | 900 | 0.7711 | 0.7425 | 0.7974 |
| sokoban | 21 | ours_ilp | 3 | 692 | 900 | 0.7689 | 0.7402 | 0.7953 |
| sokoban | 21 | react | 3 | 54 | 900 | 0.0600 | 0.0463 | 0.0775 |
| sokoban | 21 | tape | 3 | 657 | 900 | 0.7300 | 0.7001 | 0.7580 |
| sokoban | 23 | ours_astar | 2 | 469 | 600 | 0.7817 | 0.7469 | 0.8129 |
| sokoban | 23 | ours_ilp | 2 | 463 | 600 | 0.7717 | 0.7364 | 0.8035 |
| sokoban | 23 | react | 2 | 25 | 600 | 0.0417 | 0.0284 | 0.0608 |
| sokoban | 23 | tape | 2 | 439 | 600 | 0.7317 | 0.6948 | 0.7656 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Agents: pooled per benchmark (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval; the interval treats the trials as independent, although the episodes of one instance share a level)

| bench | method | instances | successes | trials | success | ci_lo | ci_hi | episodes |
|---|---|---|---|---|---|---|---|---|
| river | ours_astar | 30 | 8592 | 9000 | 0.9547 | 0.9502 | 0.9588 | 300 |
| river | ours_ilp | 30 | 8643 | 9000 | 0.9603 | 0.9561 | 0.9642 | 300 |
| river | react | 30 | 4151 | 9000 | 0.4612 | 0.4509 | 0.4715 | 300 |
| river | tape | 30 | 8569 | 9000 | 0.9521 | 0.9475 | 0.9563 | 300 |
| sokoban | ours_astar | 25 | 6509 | 7500 | 0.8679 | 0.8600 | 0.8753 | 300 |
| sokoban | ours_ilp | 25 | 6510 | 7500 | 0.8680 | 0.8602 | 0.8755 | 300 |
| sokoban | react | 25 | 1845 | 7500 | 0.2460 | 0.2364 | 0.2559 | 300 |
| sokoban | tape | 25 | 6432 | 7500 | 0.8576 | 0.8495 | 0.8653 | 300 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Paired differences in success (mean over instances of success_ours_astar - success_other; 95% percentile bootstrap, B = 2000, resampled over instances, paired by instance)

| bench | comparison | instances | mean_diff | ci_lo | ci_hi |
|---|---|---|---|---|---|
| river | ours_astar - tape | 30 | 0.0026 | 0.0009 | 0.0044 |
| river | ours_astar - react | 30 | 0.4934 | 0.4329 | 0.5493 |
| sokoban | ours_astar - tape | 25 | 0.0103 | 0.0032 | 0.0181 |
| sokoban | ours_astar - react | 25 | 0.6219 | 0.5749 | 0.6647 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).
