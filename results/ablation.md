# Phase 6 ablation (episodes/cell=30, slip=0.15)

Safe success = goal reached AND no executed move rejected by an independent domain auditor (raw = goal reached at all), shown with a 95% Wilson interval. `actions` = mean actions in solved episodes.


## LLM condition: goal-biased

| benchmark | config | safe success [95% CI] | raw | replans | invalid rate | actions | plan ms |
|---|---|---|---|---|---|---|---|
| sokoban-trivial | baseline | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 16.9 |
| sokoban-trivial | +validator | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 16.0 |
| sokoban-trivial | +val+exp | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 15.6 |
| sokoban-trivial | +adaptive | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 0.2 |
| sokoban-trivial | full | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 0.4 |
| sokoban-simple | baseline | 100% [89%, 100%] | 100% | 1.43 | 0.0% | 10.4 | 51.8 |
| sokoban-simple | +validator | 100% [89%, 100%] | 100% | 1.43 | 0.0% | 10.4 | 51.0 |
| sokoban-simple | +val+exp | 100% [89%, 100%] | 100% | 1.43 | 0.0% | 10.4 | 58.6 |
| sokoban-simple | +adaptive | 100% [89%, 100%] | 100% | 1.43 | 0.0% | 10.4 | 7.6 |
| sokoban-simple | full | 100% [89%, 100%] | 100% | 1.43 | 0.0% | 10.4 | 14.2 |
| sokoban-multi | baseline | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 99.9 |
| sokoban-multi | +validator | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 104.0 |
| sokoban-multi | +val+exp | 97% [83%, 99%] | 97% | 1.87 | 0.0% | 12.8 | 123.8 |
| sokoban-multi | +adaptive | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 96.4 |
| sokoban-multi | full | 97% [83%, 99%] | 97% | 1.87 | 0.0% | 12.8 | 105.2 |
| sokoban-hard | baseline | 53% [36%, 70%] | 53% | 4.50 | 0.0% | 32.2 | 4302.0 |
| sokoban-hard | +validator | 53% [36%, 70%] | 53% | 4.50 | 0.0% | 32.2 | 2687.0 |
| sokoban-hard | +val+exp | 53% [36%, 70%] | 53% | 4.50 | 0.0% | 32.2 | 2595.0 |
| sokoban-hard | +adaptive | 53% [36%, 70%] | 53% | 4.50 | 0.0% | 32.2 | 3837.8 |
| sokoban-hard | full | 53% [36%, 70%] | 53% | 4.50 | 0.0% | 32.2 | 3048.8 |
| river-crossing | baseline | 0% [0%, 11%] | 100% | 1.43 | 0.0% | nan | 62.1 |
| river-crossing | +validator | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 45.0 |
| river-crossing | +val+exp | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 45.1 |
| river-crossing | +adaptive | 0% [0%, 11%] | 100% | 1.43 | 0.0% | nan | 3.6 |
| river-crossing | full | 100% [89%, 100%] | 100% | 1.87 | 0.0% | 12.9 | 9.4 |
| rush-hour | baseline | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.8 | 36.2 |
| rush-hour | +validator | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.8 | 49.6 |
| rush-hour | +val+exp | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 50.7 |
| rush-hour | +adaptive | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.8 | 36.1 |
| rush-hour | full | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 49.3 |

## LLM condition: adversarial

| benchmark | config | safe success [95% CI] | raw | replans | invalid rate | actions | plan ms |
|---|---|---|---|---|---|---|---|
| sokoban-trivial | baseline | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 15.8 |
| sokoban-trivial | +validator | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 16.1 |
| sokoban-trivial | +val+exp | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 15.4 |
| sokoban-trivial | +adaptive | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 0.7 |
| sokoban-trivial | full | 100% [89%, 100%] | 100% | 0.03 | 0.0% | 1.0 | 1.5 |
| sokoban-simple | baseline | 10% [3%, 26%] | 10% | 0.03 | 0.0% | 9.3 | 15.0 |
| sokoban-simple | +validator | 10% [3%, 26%] | 10% | 0.03 | 0.5% | 9.3 | 21.9 |
| sokoban-simple | +val+exp | 10% [3%, 26%] | 10% | 0.03 | 0.5% | 9.3 | 27.3 |
| sokoban-simple | +adaptive | 10% [3%, 26%] | 10% | 0.03 | 0.0% | 9.3 | 9.6 |
| sokoban-simple | full | 10% [3%, 26%] | 10% | 0.03 | 0.5% | 9.3 | 21.6 |
| sokoban-multi | baseline | 0% [0%, 11%] | 0% | 0.00 | 0.0% | nan | 14.5 |
| sokoban-multi | +validator | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 22.9 |
| sokoban-multi | +val+exp | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 30.9 |
| sokoban-multi | +adaptive | 0% [0%, 11%] | 0% | 0.00 | 0.0% | nan | 14.3 |
| sokoban-multi | full | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 30.3 |
| sokoban-hard | baseline | 0% [0%, 11%] | 0% | 0.00 | 0.0% | nan | 28.1 |
| sokoban-hard | +validator | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 49.9 |
| sokoban-hard | +val+exp | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 66.0 |
| sokoban-hard | +adaptive | 0% [0%, 11%] | 0% | 0.00 | 0.0% | nan | 26.3 |
| sokoban-hard | full | 0% [0%, 11%] | 0% | 0.00 | 0.4% | nan | 70.5 |
| river-crossing | baseline | 0% [0%, 11%] | 100% | 1.43 | 0.0% | nan | 97.5 |
| river-crossing | +validator | 0% [0%, 11%] | 0% | 0.00 | 30.5% | nan | 9.4 |
| river-crossing | +val+exp | 0% [0%, 11%] | 0% | 0.00 | 30.5% | nan | 11.0 |
| river-crossing | +adaptive | 0% [0%, 11%] | 100% | 1.43 | 0.0% | nan | 27.2 |
| river-crossing | full | 0% [0%, 11%] | 0% | 0.00 | 30.5% | nan | 10.5 |
| rush-hour | baseline | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 124.8 |
| rush-hour | +validator | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 155.9 |
| rush-hour | +val+exp | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 187.7 |
| rush-hour | +adaptive | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 125.6 |
| rush-hour | full | 100% [89%, 100%] | 100% | 0.80 | 0.0% | 6.9 | 180.6 |
