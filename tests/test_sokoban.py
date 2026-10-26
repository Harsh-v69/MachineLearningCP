import random

from toy import assert_solvers_agree
from tapegraph.problems.sokoban import Sokoban
from tapegraph.solvers import astar, bfs, idastar

GRID = """
#######
#     #
# .$@ #
#     #
#######
"""


def test_single_push():
    p, s = Sokoban.from_grid(GRID)
    r = bfs.solve(p, s)
    assert r.path == ["L"] and r.cost == 1
    assert r.res == 3  # a push costs 3 resource units
    assert astar.solve(p, s).path == ["L"]


def test_dead_cells_are_static_deadlocks():
    p, _ = Sokoban.from_grid(GRID)
    assert (1, 1) in p.dead and (3, 3) in p.dead and (2, 1) in p.dead
    assert (2, 2) not in p.dead and (2, 3) not in p.dead


def test_pushing_into_a_dead_cell_is_pruned():
    p, s = Sokoban.from_grid(GRID)
    s_dead = ((2, 4), ((1, 3),))  # row 1 is all dead in this room
    assert p.prune(s_dead) and not p.prune(s)


def _levels(boxes, seeds, depth):
    for seed in seeds:
        rng = random.Random(seed)
        p = Sokoban.random_level(rng, 7, 9, boxes, 0.08)
        yield p, p.random_start(rng, depth)


def test_astar_and_idastar_match_bfs_on_random_levels():
    cases = [(p, s, 40) for p, s in _levels(1, range(40), 40)]
    cases += [(p, s, 60) for p, s in _levels(2, range(100, 115), 60)]
    nontrivial, hard = 0, 0
    for p, s, depth in cases:
        b = bfs.solve(p, s)  # BFS ignores h and prune
        assert b.status == "ok" and b.cost <= depth  # reverse play guarantees solvability
        if b.cost == 0:
            continue  # already solved: says nothing about h or prune
        assert_solvers_agree(p, s, b)
        nontrivial += 1
        hard += b.cost >= 5
    assert nontrivial >= 15 and hard >= 5, (nontrivial, hard)


def test_random_start_is_a_legal_state():
    p, s = next(_levels(2, [7], 20))
    (pr, pc), boxes = s
    assert len(boxes) == 2 and (pr, pc) not in p.walls and not set(boxes) & p.walls
