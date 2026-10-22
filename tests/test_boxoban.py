import random

from tapegraph.problems.boxoban import boxoban_level
from tapegraph.solvers import astar


def test_boxoban_level_shape():
    p = boxoban_level(random.Random(0))
    assert (p.H, p.W) == (10, 10) and len(p.goals) == 4


def test_boxoban_short_reverse_play_is_solvable_by_astar():
    for seed in range(4):
        rng = random.Random(seed)
        p = boxoban_level(rng)
        s = p.random_start(rng, 12)
        r = astar.solve(p, s, max_nodes=500_000)
        assert r.status == "ok" and r.cost <= 12  # reverse play of 12 steps => solution of length <= 12
