# Harder games (60 instances per row, no LLM)

## Peg Solitaire (weighted A*, weight 2, budget 60,000 nodes per search)

Start position, nodes until the first plan (weight 2 / weight 4):

| | no checker | pagoda checker |
|---|---|---|
| nodes | 139,048 / 139,324 | 82,009 / 82,257 |

Positions built by playing k jumps backwards from the goal (every one is solvable in k moves):

| moves to goal | solved, no checker | solved, checker | mean nodes, no checker | mean nodes, checker | solved only with checker | only without |
|---|---|---|---|---|---|---|
| 12 | 100% | 100% | 296 | 237 | 0 | 0 |
| 18 | 100% | 100% | 2,776 | 1,914 | 0 | 0 |
| 22 | 93% | 98% | 13,780 | 9,663 | 3 | 0 |
| 26 | 58% | 75% | 39,170 | 31,817 | 10 | 0 |

## 24-puzzle (weighted A*, weight 3, budget 60,000 nodes)

| scramble moves | solved | mean solution moves | gate changes any result | nodes wasted on unsolvable start, no gate | with gate |
|---|---|---|---|---|---|
| 20 | 100% | 22 | no | 60,000 | 1 |
| 40 | 95% | 47 | no | 60,000 | 1 |
| 60 | 73% | 63 | no | 60,000 | 1 |
| 80 | 57% | 76 | no | 60,000 | 1 |

## Rubik's cube 3x3x3 (meet in the middle, budget 400,000 nodes)

| scramble moves | solved | mean nodes | mean solution moves | gate changes any result | nodes wasted on twisted cube, no gate | with gate |
|---|---|---|---|---|---|---|
| 4 | 100% | 457 | 3.7 | no | 400,010 | 0 |
| 5 | 100% | 3,182 | 4.7 | no | 400,010 | 0 |
| 6 | 100% | 5,806 | 5.6 | no | 400,010 | 0 |
| 7 | 100% | 37,955 | 6.5 | no | 400,010 | 0 |
| 8 | 100% | 71,428 | 7.4 | no | 400,010 | 0 |
