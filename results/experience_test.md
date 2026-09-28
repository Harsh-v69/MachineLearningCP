# Experience store under state-dependent slip (hazard_frac=0.25, hazard_p=0.7, candidates=30, 20 runs x 30 episodes)

Mean replans/episode, early half vs late half; success over all episodes.

| benchmark | arm | replans early | replans late | success |
|---|---|---|---|---|
| sokoban-simple | validator only | 4.21 | 4.11 | 78% |
| sokoban-simple | +experience | 3.78 | 3.55 | 83% |
| sokoban-multi | validator only | 5.17 | 4.87 | 74% |
| sokoban-multi | +experience | 5.15 | 4.93 | 74% |
| river-crossing | validator only | 4.12 | 3.74 | 80% |
| river-crossing | +experience | 3.62 | 3.20 | 85% |
| rush-hour | validator only | 2.92 | 2.64 | 90% |
| rush-hour | +experience | 2.84 | 2.47 | 91% |

Paired difference (+experience minus validator only), same hazards and seeds per run; negative = store helps.

| benchmark | late-replans diff (mean +/- SE) | success diff | runs |
|---|---|---|---|
| sokoban-simple | -0.56 +/- 0.18 | +5.5% | 20 |
| sokoban-multi | +0.06 +/- 0.03 | -0.2% | 20 |
| river-crossing | -0.54 +/- 0.15 | +5.0% | 20 |
| rush-hour | -0.17 +/- 0.11 | +1.2% | 20 |
