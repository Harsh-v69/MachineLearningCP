# Results

## Solvers (unconstrained, budget = T*+slack; ok = fraction solved within the node cap; cost means are over solved instances only)

_no data_

## Agents (success within budget under noise)

| bench | T | method | n | success | mean_steps | solves | solver_fail | seconds |
|---|---|---|---|---|---|---|---|---|
| sokoban2 | 5 | ours_astar | 2 | 0.975 | 5.33 | 1.21 | 0.05 | 0.0006 |
| sokoban2 | 5 | ours_ilp | 2 | 0.98 | 5.31 | 1.205 | 0.04 | 0.0393 |
| sokoban2 | 5 | react | 2 | 0.63 | 6.26 | 0.0 | 0.0 | 0.0003 |
| sokoban2 | 5 | tape | 2 | 0.975 | 5.33 | 1.21 | 0.0 | 0.0188 |
| sokoban2 | 7 | ours_astar | 3 | 0.9567 | 7.4867 | 1.4567 | 0.2267 | 0.0012 |
| sokoban2 | 7 | ours_ilp | 3 | 0.9567 | 7.4733 | 1.4933 | 0.27 | 0.0518 |
| sokoban2 | 7 | react | 3 | 0.4733 | 8.48 | 0.0 | 0.0 | 0.0009 |
| sokoban2 | 7 | tape | 3 | 0.96 | 7.4867 | 1.4567 | 0.0 | 0.0209 |
| sokoban2 | 10 | ours_astar | 1 | 0.96 | 10.7 | 1.48 | 0.13 | 0.0039 |
| sokoban2 | 10 | ours_ilp | 1 | 0.96 | 10.7 | 1.48 | 0.13 | 0.1168 |
| sokoban2 | 10 | react | 1 | 0.3 | 11.78 | 0.0 | 0.0 | 0.0008 |
| sokoban2 | 10 | tape | 1 | 0.96 | 10.7 | 1.48 | 0.0 | 0.0238 |
| sokoban2 | 11 | ours_astar | 4 | 0.895 | 11.7025 | 1.88 | 0.5375 | 0.0057 |
| sokoban2 | 11 | ours_ilp | 4 | 0.8975 | 11.7025 | 1.8575 | 0.5125 | 0.1903 |
| sokoban2 | 11 | react | 4 | 0.2325 | 12.8175 | 0.0 | 0.0 | 0.0015 |
| sokoban2 | 11 | tape | 4 | 0.8975 | 11.7025 | 1.87 | 0.0 | 0.0252 |
| sokoban2 | 13 | ours_astar | 1 | 0.87 | 13.7 | 1.87 | 0.53 | 0.0034 |
| sokoban2 | 13 | ours_ilp | 1 | 0.87 | 13.7 | 1.87 | 0.53 | 0.1461 |
| sokoban2 | 13 | react | 1 | 0.19 | 14.88 | 0.0 | 0.0 | 0.0013 |
| sokoban2 | 13 | tape | 1 | 0.87 | 13.7 | 1.89 | 0.0 | 0.0253 |
| sokoban2 | 15 | ours_astar | 4 | 0.8075 | 15.94 | 2.635 | 1.18 | 0.0184 |
| sokoban2 | 15 | ours_ilp | 4 | 0.81 | 15.94 | 2.61 | 1.1525 | 0.8479 |
| sokoban2 | 15 | react | 4 | 0.1275 | 16.905 | 0.0 | 0.0 | 0.0057 |
| sokoban2 | 15 | tape | 4 | 0.8 | 15.95 | 2.7675 | 0.0 | 0.0434 |
| sokoban2 | 17 | ours_astar | 2 | 0.82 | 17.905 | 2.4 | 0.96 | 0.0192 |
| sokoban2 | 17 | ours_ilp | 2 | 0.82 | 17.905 | 2.445 | 1.005 | 0.9353 |
| sokoban2 | 17 | react | 2 | 0.105 | 18.96 | 0.0 | 0.0 | 0.0056 |
| sokoban2 | 17 | tape | 2 | 0.8 | 17.925 | 2.885 | 0.0 | 0.0434 |
| sokoban2 | 18 | ours_astar | 1 | 0.76 | 19.04 | 3.33 | 1.85 | 0.0185 |
| sokoban2 | 18 | ours_ilp | 1 | 0.76 | 19.04 | 3.33 | 1.85 | 0.7443 |
| sokoban2 | 18 | react | 1 | 0.09 | 19.98 | 0.0 | 0.0 | 0.0163 |
| sokoban2 | 18 | tape | 1 | 0.75 | 19.04 | 3.74 | 0.0 | 0.0565 |
| sokoban2 | 19 | ours_astar | 2 | 0.81 | 20.04 | 2.93 | 1.385 | 0.0282 |
| sokoban2 | 19 | ours_ilp | 2 | 0.81 | 20.01 | 2.965 | 1.41 | 2.1337 |
| sokoban2 | 19 | react | 2 | 0.105 | 20.95 | 0.0 | 0.0 | 0.0103 |
| sokoban2 | 19 | tape | 2 | 0.8 | 20.04 | 3.22 | 0.0 | 0.0641 |
| sokoban2 | 21 | ours_astar | 2 | 0.705 | 22.095 | 4.435 | 2.91 | 0.029 |
| sokoban2 | 21 | ours_ilp | 2 | 0.7 | 22.095 | 4.46 | 2.94 | 1.1618 |
| sokoban2 | 21 | react | 2 | 0.06 | 22.945 | 0.0 | 0.0 | 0.0075 |
| sokoban2 | 21 | tape | 2 | 0.67 | 22.125 | 5.66 | 0.0 | 0.0519 |
| sokoban2 | 22 | ours_astar | 2 | 0.775 | 23.13 | 3.675 | 2.1 | 0.0435 |
| sokoban2 | 22 | ours_ilp | 2 | 0.79 | 23.1 | 3.35 | 1.75 | 2.9519 |
| sokoban2 | 22 | react | 2 | 0.035 | 23.98 | 0.0 | 0.0 | 0.0084 |
| sokoban2 | 22 | tape | 2 | 0.75 | 23.14 | 4.63 | 0.0 | 0.059 |
| sokoban2 | 23 | ours_astar | 1 | 0.82 | 24.12 | 3.45 | 1.9 | 0.0388 |
| sokoban2 | 23 | ours_ilp | 1 | 0.81 | 24.08 | 3.49 | 1.95 | 2.5925 |
| sokoban2 | 23 | react | 1 | 0.04 | 24.98 | 0.0 | 0.0 | 0.0067 |
| sokoban2 | 23 | tape | 1 | 0.8 | 24.14 | 4.64 | 0.0 | 0.0576 |
| sokoban3 | 9 | ours_astar | 1 | 0.9667 | 9.5333 | 1.4667 | 0.1667 | 0.0027 |
| sokoban3 | 9 | react | 1 | 0.4333 | 10.4667 | 0.0 | 0.0 | 0.0049 |
| sokoban3 | 9 | tape | 1 | 0.9667 | 9.5333 | 1.4667 | 0.0 | 0.0079 |
| sokoban3 | 10 | ours_astar | 2 | 0.95 | 10.5667 | 1.5167 | 0.2167 | 0.0031 |
| sokoban3 | 10 | react | 2 | 0.2833 | 11.7 | 0.0 | 0.0 | 0.0051 |
| sokoban3 | 10 | tape | 2 | 0.9667 | 10.5667 | 1.4 | 0.0 | 0.0154 |
| sokoban3 | 11 | ours_astar | 2 | 0.9333 | 11.5667 | 1.4667 | 0.1833 | 0.0074 |
| sokoban3 | 11 | react | 2 | 0.2667 | 12.7667 | 0.0 | 0.0 | 0.0082 |
| sokoban3 | 11 | tape | 2 | 0.9167 | 11.5667 | 1.6333 | 0.0 | 0.042 |
| sokoban3 | 13 | ours_astar | 1 | 0.8667 | 13.8667 | 2.3667 | 0.8333 | 0.0342 |
| sokoban3 | 13 | react | 1 | 0.1667 | 14.8667 | 0.0 | 0.0 | 0.0094 |
| sokoban3 | 13 | tape | 1 | 0.8 | 13.8667 | 3.1 | 0.0 | 0.1147 |
| sokoban3 | 14 | ours_astar | 1 | 0.8333 | 14.8667 | 2.2 | 0.8 | 0.0112 |
| sokoban3 | 14 | react | 1 | 0.2 | 15.8 | 0.0 | 0.0 | 0.0054 |
| sokoban3 | 14 | tape | 1 | 0.8333 | 14.8667 | 2.2333 | 0.0 | 0.0232 |
| sokoban3 | 15 | ours_astar | 3 | 0.8889 | 15.7333 | 1.8667 | 0.4778 | 0.0336 |
| sokoban3 | 15 | react | 3 | 0.2 | 16.8667 | 0.0 | 0.0 | 0.0192 |
| sokoban3 | 15 | tape | 3 | 0.8889 | 15.7556 | 1.9111 | 0.0 | 0.0327 |
| sokoban3 | 17 | ours_astar | 3 | 0.8111 | 18.1 | 2.6222 | 1.0222 | 0.0985 |
| sokoban3 | 17 | react | 3 | 0.1111 | 18.9444 | 0.0 | 0.0 | 0.0705 |
| sokoban3 | 17 | tape | 3 | 0.7778 | 18.0889 | 3.1556 | 0.0 | 0.3356 |
| sokoban3 | 18 | ours_astar | 1 | 0.8333 | 19.0 | 2.9 | 1.4 | 0.0819 |
| sokoban3 | 18 | react | 1 | 0.1 | 19.8667 | 0.0 | 0.0 | 0.0655 |
| sokoban3 | 18 | tape | 1 | 0.8333 | 19.0 | 3.1 | 0.0 | 0.145 |
| sokoban3 | 19 | ours_astar | 1 | 0.7667 | 20.2333 | 3.9 | 2.2 | 0.087 |
| sokoban3 | 19 | react | 1 | 0.1333 | 21.0 | 0.0 | 0.0 | 0.0427 |
| sokoban3 | 19 | tape | 1 | 0.7333 | 20.2667 | 5.0333 | 0.0 | 0.0813 |
| sokoban3 | 22 | ours_astar | 4 | 0.825 | 23.1583 | 3.2167 | 1.6083 | 0.3522 |
| sokoban3 | 22 | react | 4 | 0.0333 | 23.9833 | 0.0 | 0.0 | 0.2209 |
| sokoban3 | 22 | tape | 4 | 0.7583 | 23.2083 | 4.875 | 0.0 | 0.7148 |
| sokoban3 | 23 | ours_astar | 1 | 0.8333 | 23.8 | 2.6333 | 1.2333 | 0.14 |
| sokoban3 | 23 | react | 1 | 0.0 | 25.0 | 0.0 | 0.0 | 0.0871 |
| sokoban3 | 23 | tape | 1 | 0.8333 | 23.8667 | 4.4 | 0.0 | 0.3981 |
| sokoban3 | 25 | ours_astar | 1 | 0.7 | 26.1333 | 4.1667 | 2.5 | 0.172 |
| sokoban3 | 25 | react | 1 | 0.0333 | 27.0 | 0.0 | 0.0 | 0.1261 |
| sokoban3 | 25 | tape | 1 | 0.6 | 26.1333 | 5.9667 | 0.0 | 0.8535 |
| sokoban3 | 26 | ours_astar | 3 | 0.6556 | 27.2 | 4.7889 | 3.2 | 0.642 |
| sokoban3 | 26 | react | 3 | 0.0333 | 27.9778 | 0.0 | 0.0 | 0.4343 |
| sokoban3 | 26 | tape | 3 | 0.6111 | 27.2667 | 7.6 | 0.0 | 2.5931 |
| sokoban3 | 27 | ours_astar | 1 | 0.7333 | 28.0667 | 5.3 | 3.8333 | 1.2109 |
| sokoban3 | 27 | react | 1 | 0.0 | 29.0 | 0.0 | 0.0 | 1.1459 |
| sokoban3 | 27 | tape | 1 | 0.6667 | 28.3 | 9.1 | 0.0 | 4.4894 |

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
| sokoban2 | 5 | ours_astar | 2 | 195 | 200 | 0.9750 | 0.9428 | 0.9893 |
| sokoban2 | 5 | ours_ilp | 2 | 196 | 200 | 0.9800 | 0.9497 | 0.9922 |
| sokoban2 | 5 | react | 2 | 126 | 200 | 0.6300 | 0.5612 | 0.6939 |
| sokoban2 | 5 | tape | 2 | 195 | 200 | 0.9750 | 0.9428 | 0.9893 |
| sokoban2 | 7 | ours_astar | 3 | 287 | 300 | 0.9567 | 0.9273 | 0.9745 |
| sokoban2 | 7 | ours_ilp | 3 | 287 | 300 | 0.9567 | 0.9273 | 0.9745 |
| sokoban2 | 7 | react | 3 | 142 | 300 | 0.4733 | 0.4175 | 0.5298 |
| sokoban2 | 7 | tape | 3 | 288 | 300 | 0.9600 | 0.9314 | 0.9770 |
| sokoban2 | 10 | ours_astar | 1 | 96 | 100 | 0.9600 | 0.9016 | 0.9843 |
| sokoban2 | 10 | ours_ilp | 1 | 96 | 100 | 0.9600 | 0.9016 | 0.9843 |
| sokoban2 | 10 | react | 1 | 30 | 100 | 0.3000 | 0.2189 | 0.3959 |
| sokoban2 | 10 | tape | 1 | 96 | 100 | 0.9600 | 0.9016 | 0.9843 |
| sokoban2 | 11 | ours_astar | 4 | 358 | 400 | 0.8950 | 0.8611 | 0.9214 |
| sokoban2 | 11 | ours_ilp | 4 | 359 | 400 | 0.8975 | 0.8639 | 0.9235 |
| sokoban2 | 11 | react | 4 | 93 | 400 | 0.2325 | 0.1938 | 0.2763 |
| sokoban2 | 11 | tape | 4 | 359 | 400 | 0.8975 | 0.8639 | 0.9235 |
| sokoban2 | 13 | ours_astar | 1 | 87 | 100 | 0.8700 | 0.7902 | 0.9224 |
| sokoban2 | 13 | ours_ilp | 1 | 87 | 100 | 0.8700 | 0.7902 | 0.9224 |
| sokoban2 | 13 | react | 1 | 19 | 100 | 0.1900 | 0.1251 | 0.2778 |
| sokoban2 | 13 | tape | 1 | 87 | 100 | 0.8700 | 0.7902 | 0.9224 |
| sokoban2 | 15 | ours_astar | 4 | 323 | 400 | 0.8075 | 0.7660 | 0.8431 |
| sokoban2 | 15 | ours_ilp | 4 | 324 | 400 | 0.8100 | 0.7687 | 0.8454 |
| sokoban2 | 15 | react | 4 | 51 | 400 | 0.1275 | 0.0983 | 0.1638 |
| sokoban2 | 15 | tape | 4 | 320 | 400 | 0.8000 | 0.7580 | 0.8363 |
| sokoban2 | 17 | ours_astar | 2 | 164 | 200 | 0.8200 | 0.7609 | 0.8671 |
| sokoban2 | 17 | ours_ilp | 2 | 164 | 200 | 0.8200 | 0.7609 | 0.8671 |
| sokoban2 | 17 | react | 2 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 |
| sokoban2 | 17 | tape | 2 | 160 | 200 | 0.8000 | 0.7391 | 0.8495 |
| sokoban2 | 18 | ours_astar | 1 | 76 | 100 | 0.7600 | 0.6677 | 0.8331 |
| sokoban2 | 18 | ours_ilp | 1 | 76 | 100 | 0.7600 | 0.6677 | 0.8331 |
| sokoban2 | 18 | react | 1 | 9 | 100 | 0.0900 | 0.0481 | 0.1623 |
| sokoban2 | 18 | tape | 1 | 75 | 100 | 0.7500 | 0.6570 | 0.8245 |
| sokoban2 | 19 | ours_astar | 2 | 162 | 200 | 0.8100 | 0.7500 | 0.8583 |
| sokoban2 | 19 | ours_ilp | 2 | 162 | 200 | 0.8100 | 0.7500 | 0.8583 |
| sokoban2 | 19 | react | 2 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 |
| sokoban2 | 19 | tape | 2 | 160 | 200 | 0.8000 | 0.7391 | 0.8495 |
| sokoban2 | 21 | ours_astar | 2 | 141 | 200 | 0.7050 | 0.6384 | 0.7639 |
| sokoban2 | 21 | ours_ilp | 2 | 140 | 200 | 0.7000 | 0.6332 | 0.7593 |
| sokoban2 | 21 | react | 2 | 12 | 200 | 0.0600 | 0.0347 | 0.1019 |
| sokoban2 | 21 | tape | 2 | 134 | 200 | 0.6700 | 0.6022 | 0.7314 |
| sokoban2 | 22 | ours_astar | 2 | 155 | 200 | 0.7750 | 0.7123 | 0.8274 |
| sokoban2 | 22 | ours_ilp | 2 | 158 | 200 | 0.7900 | 0.7284 | 0.8407 |
| sokoban2 | 22 | react | 2 | 7 | 200 | 0.0350 | 0.0171 | 0.0705 |
| sokoban2 | 22 | tape | 2 | 150 | 200 | 0.7500 | 0.6857 | 0.8049 |
| sokoban2 | 23 | ours_astar | 1 | 82 | 100 | 0.8200 | 0.7333 | 0.8830 |
| sokoban2 | 23 | ours_ilp | 1 | 81 | 100 | 0.8100 | 0.7222 | 0.8749 |
| sokoban2 | 23 | react | 1 | 4 | 100 | 0.0400 | 0.0157 | 0.0984 |
| sokoban2 | 23 | tape | 1 | 80 | 100 | 0.8000 | 0.7112 | 0.8666 |
| sokoban3 | 9 | ours_astar | 1 | 29 | 30 | 0.9667 | 0.8333 | 0.9941 |
| sokoban3 | 9 | react | 1 | 13 | 30 | 0.4333 | 0.2738 | 0.6080 |
| sokoban3 | 9 | tape | 1 | 29 | 30 | 0.9667 | 0.8333 | 0.9941 |
| sokoban3 | 10 | ours_astar | 2 | 57 | 60 | 0.9500 | 0.8630 | 0.9829 |
| sokoban3 | 10 | react | 2 | 17 | 60 | 0.2833 | 0.1851 | 0.4077 |
| sokoban3 | 10 | tape | 2 | 58 | 60 | 0.9667 | 0.8864 | 0.9908 |
| sokoban3 | 11 | ours_astar | 2 | 56 | 60 | 0.9333 | 0.8407 | 0.9738 |
| sokoban3 | 11 | react | 2 | 16 | 60 | 0.2667 | 0.1713 | 0.3901 |
| sokoban3 | 11 | tape | 2 | 55 | 60 | 0.9167 | 0.8193 | 0.9639 |
| sokoban3 | 13 | ours_astar | 1 | 26 | 30 | 0.8667 | 0.7032 | 0.9469 |
| sokoban3 | 13 | react | 1 | 5 | 30 | 0.1667 | 0.0734 | 0.3356 |
| sokoban3 | 13 | tape | 1 | 24 | 30 | 0.8000 | 0.6269 | 0.9050 |
| sokoban3 | 14 | ours_astar | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 14 | react | 1 | 6 | 30 | 0.2000 | 0.0950 | 0.3731 |
| sokoban3 | 14 | tape | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 15 | ours_astar | 3 | 80 | 90 | 0.8889 | 0.8074 | 0.9385 |
| sokoban3 | 15 | react | 3 | 18 | 90 | 0.2000 | 0.1304 | 0.2941 |
| sokoban3 | 15 | tape | 3 | 80 | 90 | 0.8889 | 0.8074 | 0.9385 |
| sokoban3 | 17 | ours_astar | 3 | 73 | 90 | 0.8111 | 0.7182 | 0.8786 |
| sokoban3 | 17 | react | 3 | 10 | 90 | 0.1111 | 0.0615 | 0.1926 |
| sokoban3 | 17 | tape | 3 | 70 | 90 | 0.7778 | 0.6815 | 0.8513 |
| sokoban3 | 18 | ours_astar | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 18 | react | 1 | 3 | 30 | 0.1000 | 0.0346 | 0.2562 |
| sokoban3 | 18 | tape | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 19 | ours_astar | 1 | 23 | 30 | 0.7667 | 0.5907 | 0.8821 |
| sokoban3 | 19 | react | 1 | 4 | 30 | 0.1333 | 0.0531 | 0.2968 |
| sokoban3 | 19 | tape | 1 | 22 | 30 | 0.7333 | 0.5555 | 0.8582 |
| sokoban3 | 22 | ours_astar | 4 | 99 | 120 | 0.8250 | 0.7472 | 0.8826 |
| sokoban3 | 22 | react | 4 | 4 | 120 | 0.0333 | 0.0130 | 0.0826 |
| sokoban3 | 22 | tape | 4 | 91 | 120 | 0.7583 | 0.6745 | 0.8261 |
| sokoban3 | 23 | ours_astar | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 23 | react | 1 | 0 | 30 | 0.0000 | 0.0000 | 0.1135 |
| sokoban3 | 23 | tape | 1 | 25 | 30 | 0.8333 | 0.6644 | 0.9266 |
| sokoban3 | 25 | ours_astar | 1 | 21 | 30 | 0.7000 | 0.5212 | 0.8334 |
| sokoban3 | 25 | react | 1 | 1 | 30 | 0.0333 | 0.0059 | 0.1667 |
| sokoban3 | 25 | tape | 1 | 18 | 30 | 0.6000 | 0.4232 | 0.7541 |
| sokoban3 | 26 | ours_astar | 3 | 59 | 90 | 0.6556 | 0.5528 | 0.7455 |
| sokoban3 | 26 | react | 3 | 3 | 90 | 0.0333 | 0.0114 | 0.0935 |
| sokoban3 | 26 | tape | 3 | 55 | 90 | 0.6111 | 0.5078 | 0.7053 |
| sokoban3 | 27 | ours_astar | 1 | 22 | 30 | 0.7333 | 0.5555 | 0.8582 |
| sokoban3 | 27 | react | 1 | 0 | 30 | 0.0000 | 0.0000 | 0.1135 |
| sokoban3 | 27 | tape | 1 | 20 | 30 | 0.6667 | 0.4878 | 0.8077 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Agents: pooled per benchmark (successes = sum over instance rows of round(success * episodes); trials = episodes x instances; 95% Wilson interval; the interval treats the trials as independent, although the episodes of one instance share a level)

| bench | method | instances | successes | trials | success | ci_lo | ci_hi | episodes |
|---|---|---|---|---|---|---|---|---|
| sokoban2 | ours_astar | 25 | 2126 | 2500 | 0.8504 | 0.8359 | 0.8638 | 100 |
| sokoban2 | ours_ilp | 25 | 2130 | 2500 | 0.8520 | 0.8375 | 0.8654 | 100 |
| sokoban2 | react | 25 | 535 | 2500 | 0.2140 | 0.1984 | 0.2305 | 100 |
| sokoban2 | tape | 25 | 2104 | 2500 | 0.8416 | 0.8268 | 0.8554 | 100 |
| sokoban3 | ours_astar | 25 | 620 | 750 | 0.8267 | 0.7979 | 0.8521 | 30 |
| sokoban3 | react | 25 | 100 | 750 | 0.1333 | 0.1109 | 0.1595 | 30 |
| sokoban3 | tape | 25 | 597 | 750 | 0.7960 | 0.7657 | 0.8233 | 30 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).

## Paired differences in success (mean over instances of success_ours_astar - success_other; 95% percentile bootstrap, B = 2000, resampled over instances, paired by instance)

| bench | comparison | instances | mean_diff | ci_lo | ci_hi |
|---|---|---|---|---|---|
| sokoban2 | ours_astar - tape | 25 | 0.0088 | 0.0028 | 0.0156 |
| sokoban2 | ours_astar - react | 25 | 0.6364 | 0.5880 | 0.6784 |
| sokoban3 | ours_astar - tape | 25 | 0.0307 | 0.0147 | 0.0493 |
| sokoban3 | ours_astar - react | 25 | 0.6933 | 0.6547 | 0.7307 |

Excluded from the intervals: 0 skipped rows (T = -1, no success value, or unknown episodes).
