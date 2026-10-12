# Search methods compared (budget 100,000 nodes per search, no checkers)

Each cell: share solved, then mean nodes and mean plan length over the solved ones.

| game | instances | BFS | DFS | weighted A* | meet in the middle |
|---|---|---|---|---|---|
| River Crossing | 1 | 100%, 28 nodes, 9.0 moves | 100%, 19 nodes, 15.0 moves | 100%, 26 nodes, 9.0 moves | n/a |
| Rush Hour | 1 | 100%, 20 nodes, 6.0 moves | 100%, 18 nodes, 18.0 moves | 100%, 12 nodes, 6.0 moves | n/a |
| Sokoban | 1 | 100%, 1,363 nodes, 11.0 moves | 0% | 100%, 107 nodes, 11.0 moves | n/a |
| Peg Solitaire | 1 | 0% | 100%, 10,845 nodes, 31.0 moves | 0% | n/a |
| Boxoban (20 levels) | 20 | 45%, 41,347 nodes, 33.8 moves | 55%, 37,835 nodes, 93.4 moves | 55%, 24,368 nodes, 36.5 moves | n/a |
| Peg Solitaire, 22 jumps out | 20 | 0% | 85%, 23,769 nodes, 22.0 moves | 95%, 20,853 nodes, 22.0 moves | n/a |
| 24-puzzle, 20 move scramble | 20 | 0% | 0% | 100%, 413 nodes, 23.6 moves | 100%, 18,453 nodes, 19.5 moves |
| 24-puzzle, 40 move scramble | 20 | 0% | 0% | 100%, 7,934 nodes, 48.1 moves | 0% |
| Rubik's cube, 5 move scramble | 20 | 30%, 30,755 nodes, 3.8 moves | 5%, 27,728 nodes, 12.0 moves | 100%, 66 nodes, 4.7 moves | 100%, 3,078 nodes, 4.7 moves |
| Rubik's cube, 6 move scramble | 20 | 15%, 11,676 nodes, 4.0 moves | 0% | 100%, 392 nodes, 5.5 moves | 100%, 5,544 nodes, 5.5 moves |
