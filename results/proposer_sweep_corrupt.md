# Proposer-quality sweep, mode=corrupt (10 hazard seeds x 20 episodes, 30 candidates)

Safe success per arm; last two columns are the paired full-minus-baseline difference (mean +/- SE).

| benchmark | quality | baseline safe | full safe | safe diff | replans diff |
|---|---|---|---|---|---|
| sokoban-trivial | 0.5 | 99% | 99% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-trivial | 0.7 | 99% | 99% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-trivial | 0.8 | 99% | 99% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-trivial | 0.9 | 99% | 99% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-trivial | 0.95 | 99% | 99% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-simple | 0.5 | 18% | 18% | -0.0% +/- 1.1% | +0.01 +/- 0.03 |
| sokoban-simple | 0.7 | 75% | 75% | +0.0% +/- 1.5% | -0.02 +/- 0.16 |
| sokoban-simple | 0.8 | 78% | 77% | -0.5% +/- 1.2% | -0.18 +/- 0.14 |
| sokoban-simple | 0.9 | 76% | 76% | -0.5% +/- 0.9% | -0.07 +/- 0.08 |
| sokoban-simple | 0.95 | 78% | 76% | -1.5% +/- 1.1% | +0.08 +/- 0.09 |
| sokoban-multi | 0.5 | 4% | 6% | +1.0% +/- 1.0% | -0.06 +/- 0.05 |
| sokoban-multi | 0.7 | 55% | 60% | +5.0% +/- 2.0% | -0.10 +/- 0.22 |
| sokoban-multi | 0.8 | 70% | 70% | -0.0% +/- 2.5% | +0.02 +/- 0.13 |
| sokoban-multi | 0.9 | 68% | 68% | -0.0% +/- 1.1% | +0.01 +/- 0.07 |
| sokoban-multi | 0.95 | 70% | 69% | -0.5% +/- 1.2% | -0.02 +/- 0.03 |
| sokoban-hard | 0.5 | 0% | 0% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-hard | 0.7 | 0% | 0% | +0.0% +/- 0.0% | +0.00 +/- 0.00 |
| sokoban-hard | 0.8 | 2% | 2% | +0.0% +/- 0.7% | +0.04 +/- 0.04 |
| sokoban-hard | 0.9 | 13% | 14% | +0.5% +/- 1.9% | -0.02 +/- 0.09 |
| sokoban-hard | 0.95 | 14% | 14% | -0.5% +/- 0.5% | +0.02 +/- 0.01 |
| river-crossing | 0.5 | 0% | 0% | +0.0% +/- 0.0% | -0.77 +/- 0.11 |
| river-crossing | 0.7 | 0% | 0% | +0.0% +/- 0.0% | -2.73 +/- 0.30 |
| river-crossing | 0.8 | 0% | 0% | +0.0% +/- 0.0% | -3.20 +/- 0.29 |
| river-crossing | 0.9 | 0% | 0% | +0.0% +/- 0.0% | -3.40 +/- 0.35 |
| river-crossing | 0.95 | 0% | 0% | +0.0% +/- 0.0% | -3.17 +/- 0.39 |
| rush-hour | 0.5 | 55% | 61% | +6.5% +/- 3.8% | -0.51 +/- 0.24 |
| rush-hour | 0.7 | 90% | 90% | -0.5% +/- 5.3% | -0.10 +/- 0.85 |
| rush-hour | 0.8 | 86% | 90% | +3.5% +/- 6.4% | -0.11 +/- 0.97 |
| rush-hour | 0.9 | 86% | 88% | +1.5% +/- 4.8% | +0.43 +/- 0.91 |
| rush-hour | 0.95 | 89% | 94% | +5.0% +/- 4.1% | -0.23 +/- 0.60 |
