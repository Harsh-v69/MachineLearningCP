import random

import pytest

from tape.bidirectional import BidirectionalProposer
from tape.envs.rubiks_cube import CUBE_2, CUBE_3
from tape.envs.rubiks_cube_validator import CubeSolvabilityValidator
from tape.executor import run_episode


def test_move_group_laws():
    c = CUBE_3
    assert len(c.ACTIONS) == 18 and len(CUBE_2.ACTIONS) == 9
    for a in c.ACTIONS:
        s = c.solved
        for _ in range(2 if a.endswith("2") else 4):
            s, _ = c.step(s, a)
        assert s == c.solved
        assert c.step(c.step(c.solved, a)[0], c.inverse(a))[0] == c.solved
    s = c.solved
    for _ in range(6):
        for a in ("R", "U", "R'", "U'"):
            s, _ = c.step(s, a)
    assert s == c.solved  # (R U R' U') has order 6


def test_clockwise_u_sends_the_right_face_to_the_front():
    c = CUBE_3
    u, _ = c.step(c.solved, "U")
    front_top = [i for i, (p, n) in enumerate(c.slots) if n == (0, 0, 1) and p[1] == 2]
    assert [u[i] for i in front_top] == [4, 4, 4]  # colour 4 = R


@pytest.mark.parametrize("cube", [CUBE_3, CUBE_2])
def test_validator_never_rejects_reachable_states(cube):
    v, rng = CubeSolvabilityValidator(cube), random.Random(5)
    assert v.solvable(cube.solved)
    assert all(v.solvable(cube.scramble(rng.randint(1, 40), rng)) for _ in range(200))


def _twist(cube, v, s):
    o = v._corners[0]
    t = list(s)
    t[o[0]], t[o[1]], t[o[2]] = s[o[1]], s[o[2]], s[o[0]]
    return tuple(t)


def test_validator_catches_each_kind_of_broken_cube():
    c = CUBE_3
    v = CubeSolvabilityValidator(c)
    s = c.scramble(20, random.Random(1))
    assert not v.solvable(_twist(c, v, s))  # twisted corner
    slots, _ = v._edges[0]
    t = list(s)
    t[slots[0]], t[slots[1]] = s[slots[1]], s[slots[0]]
    assert not v.solvable(tuple(t))  # flipped edge
    a, b = v._edges[0][0], v._edges[1][0]
    t = list(s)
    t[a[0]], t[a[1]], t[b[0]], t[b[1]] = s[b[0]], s[b[1]], s[a[0]], s[a[1]]
    assert not v.solvable(tuple(t))  # two edges swapped (parity)
    v2 = CubeSolvabilityValidator(CUBE_2)
    assert not v2.solvable(_twist(CUBE_2, v2, CUBE_2.scramble(15, random.Random(2))))


def test_bidirectional_search_finds_a_shortest_plan_and_pipeline_succeeds():
    c = CUBE_3
    s = c.scramble(6, random.Random(3))
    lv = c.with_start(s)
    (plan, *_) = BidirectionalProposer().generate_candidate_plans(lv, s, 1, 12)
    assert len(plan) <= 6
    cur = s
    for a in plan:
        cur, _ = c.step(cur, a)
    assert c.is_goal(cur)
    v = CubeSolvabilityValidator(c)
    r = run_episode(lv, BidirectionalProposer(validator=v), n_candidates=1, max_depth=12, validator=v)
    assert r.success


def test_gate_stops_a_twisted_cube_without_searching():
    c = CUBE_3
    v = CubeSolvabilityValidator(c)
    s = _twist(c, v, c.scramble(6, random.Random(1)))
    lv = c.with_start(s)
    plain = BidirectionalProposer(node_budget=20_000)
    gated = BidirectionalProposer(node_budget=20_000, validator=v)
    assert plain.generate_candidate_plans(lv, s, 1, 12) == [] and plain.expansions > 20_000
    assert gated.generate_candidate_plans(lv, s, 1, 12) == [] and gated.expansions == 0
