import csv
import random
import time
from dataclasses import replace

import numpy as np
import pytest
from toy import assert_solvers_agree

from tapegraph import bench
from tapegraph.benchmarks import BENCHMARKS
from tapegraph.oracle import Oracle
from tapegraph.problems import cube2, cube3
from tapegraph.problems.cube3 import Cube3
from tapegraph.solvers import astar, idastar

CUBE = Cube3(pdb=[0])  # moves/tables only; the tests that need h() swap in a heuristic below


def _layers(p, depth):
    """Plain BFS from the goal: {state: distance} up to `depth`."""
    dist, frontier = {p.goal: 0}, [p.goal]
    for d in range(1, depth + 1):
        nxt = []
        for s in frontier:
            for _, v, _ in p.neighbors(s):
                if v not in dist:
                    dist[v] = d
                    nxt.append(v)
        frontier = nxt
    return dist


DIST4 = _layers(CUBE, 4)


def test_full_state_bfs_matches_known_half_turn_counts():
    assert np.bincount(list(DIST4.values())).tolist() == [1, 18, 243, 3240, 43239]


def _parity(p):
    return sum(p[i] > p[j] for i in range(len(p)) for j in range(i + 1, len(p))) % 2


def test_moves_are_inverses_and_cubies_stay_valid():
    rng = random.Random(0)
    s = CUBE.random_start(rng, 30)
    for a, b in (("U", "U'"), ("R", "R'"), ("F", "F'"), ("D", "D'"), ("L", "L'"), ("B", "B'"), ("R2", "R2")):
        assert CUBE.step(CUBE.step(s, a), b) == s
    for f in "UDLRFB":
        x = s
        for _ in range(4):
            x = CUBE.step(x, f)
        assert x == s and CUBE.step(CUBE.step(s, f), f) == CUBE.step(s, f + "2")
    assert CUBE.decode(CUBE.goal) == (list(range(8)), [0] * 8, list(range(12)), [0] * 12)
    for _ in range(100):
        s = CUBE.step(s, rng.choice(CUBE.names))
    cp, co, ep, eo = CUBE.decode(s)
    assert sorted(cp) == list(range(8)) and sorted(ep) == list(range(12))
    assert sum(co) % 3 == 0 and sum(eo) % 2 == 0 and _parity(cp) == _parity(ep)
    assert s != CUBE.goal and not CUBE.is_goal(s) and CUBE.is_goal(CUBE.goal)


def test_resources_match_cube2_convention():
    s = CUBE.goal
    assert CUBE.res(s, "R2", None) == 2 and CUBE.res(s, "R", None) == 1 and CUBE.res(s, "R'", None) == 1
    assert CUBE.res_bind(s, "U2", None) == 1 and CUBE.res_bind(s, "U'", None) == 0


def test_chunked_pdb_build_reproduces_the_verified_cube2_table():
    # cube2's (perm 5040 x twist 729) table is checked against the known 2x2x2 distribution in test_cube2; odd chunk and
    # block sizes exercise every boundary of the chunking
    c2 = cube2.Cube2.shared()
    assert np.array_equal(cube3.build_pdb(c2.PM, c2.TM, chunk=997, block=100_003), c2.dist)


def test_pdb_build_on_cube3_corner_subspaces_matches_plain_bfs():
    one = np.zeros((1, 18), dtype=np.int32)  # trivial second coordinate
    assert np.array_equal(cube3.build_pdb(CUBE.PM, one, chunk=1000, block=7000), cube2._bfs_1d(CUBE.PM))
    assert np.array_equal(cube3.build_pdb(one, CUBE.TM, chunk=100, block=700), cube2._bfs_1d(CUBE.TM))
    assert cube2._bfs_1d(CUBE.PM).min() == 0 and cube2._bfs_1d(CUBE.TM).min() == 0  # all 8! perms and 3^7 twists reached


def test_pdb_cache_is_reused_and_a_stale_cache_rebuilt(tmp_path, monkeypatch):
    c2 = cube2.Cube2.shared()  # small stand-in space (also max depth 11) for the 88M-entry corner table
    monkeypatch.setattr(cube3, "_CACHE", tmp_path / "pdb.npy")
    builds = []
    monkeypatch.setattr(cube3, "build_pdb", lambda PM, TM: builds.append(1) or c2.dist.copy())
    assert np.array_equal(cube3.load_or_build(c2.PM, c2.TM), c2.dist) and len(builds) == 1
    assert np.array_equal(cube3.load_or_build(c2.PM, c2.TM), c2.dist) and len(builds) == 1  # cache hit
    np.save(tmp_path / "pdb.npy", np.zeros(10, dtype=np.int8))  # stale
    assert np.array_equal(cube3.load_or_build(c2.PM, c2.TM), c2.dist) and len(builds) == 2
    assert np.load(tmp_path / "pdb.npy").shape == c2.dist.shape


def test_random_start_never_repeats_an_axis_and_stays_within_depth():
    rng = random.Random(1)
    for depth in range(5):
        for _ in range(50):
            assert DIST4[CUBE.random_start(rng, depth)] <= depth
    # with no same-axis repeats, walks of length <= 3 are optimal
    assert all(DIST4[CUBE.random_start(rng, 3)] == 3 for _ in range(50))


class _CornerBound:
    """Small admissible stand-in for the 88M-entry corner PDB: max(corner-permutation distance, twist distance)."""

    def __init__(self):
        one = np.zeros((1, 18), dtype=np.int32)
        self.p = cube3.build_pdb(CUBE.PM, one).tolist()
        self.t = cube3.build_pdb(one, CUBE.TM).tolist()

    def __getitem__(self, i):
        p, t = divmod(i, cube3.NT)
        return max(self.p[p], self.t[t])


WEAK = Cube3(pdb=_CornerBound())


def test_heuristic_reads_the_corner_index_and_is_admissible_within_depth_4():
    assert WEAK.h(WEAK.goal) == 0
    assert all(WEAK.h(s) <= d for s, d in DIST4.items())
    assert sum(WEAK.h(s) == d for s, d in DIST4.items() if d == 4) > 1000  # informative, not h == 0


def test_astar_and_idastar_match_bfs_with_the_stand_in_heuristic():
    rng = random.Random(2)
    for _ in range(5):
        s = WEAK.random_start(rng, 4)
        a, i = astar.solve(WEAK, s), idastar.solve(WEAK, s)
        assert a.status == i.status == "ok" and a.cost == i.cost == DIST4[s]
    assert_solvers_agree(WEAK, WEAK.random_start(rng, 5))


def test_cube3_bench_runs_end_to_end_with_oracle_t_star(tmp_path, monkeypatch):
    assert BENCHMARKS["cube3"].exact and BENCHMARKS["cube3"].T_targets == [3, 5, 7, 9]
    monkeypatch.setitem(BENCHMARKS, "cube3", replace(BENCHMARKS["cube3"], make=lambda rng: WEAK, T_targets=[3]))
    bench.main(["solvers", "--bench", "cube3", "--n", "1", "--out", str(tmp_path)])
    rows = list(csv.DictReader(open(tmp_path / "solvers_cube3.csv")))
    assert {r["solver"] for r in rows} >= {"bfs", "astar", "wastar", "idastar"}
    assert all(r["T"] == "3" and r["status"] == "ok" and float(r["cost_ratio"]) == 1.0 for r in rows)


# ---- the real 88,179,840-entry corner PDB (cold build ~35 s, then cached in .cache/); run with --runslow ----

# Depth distribution of the 3x3x3 corner group in the half-turn metric (published, e.g. Korf 1997): sums to 8! * 3^7.
CORNER_COUNTS = [1, 18, 243, 2874, 28000, 205416, 1168516, 5402628, 20776176, 45391616, 15139616, 64736]


@pytest.mark.slow
def test_cold_pdb_build_matches_known_corner_distribution_and_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(cube3, "_CACHE", tmp_path / "pdb.npy")
    t = time.perf_counter()
    pdb = cube3.load_or_build(CUBE.PM, CUBE.TM)
    assert time.perf_counter() - t < 300
    assert pdb.shape == (88_179_840,) and pdb.dtype == np.int8 and pdb[0] == 0 and pdb.max() == 11
    assert [int((pdb == d).sum()) for d in range(12)] == CORNER_COUNTS
    monkeypatch.setattr(cube3, "build_pdb", None)  # a second build would raise
    assert np.array_equal(cube3.load_or_build(CUBE.PM, CUBE.TM), pdb)


@pytest.fixture(scope="module")
def real():
    return Cube3.shared()


@pytest.mark.slow
def test_corner_pdb_is_admissible_against_bfs_distance(real):
    dist5 = _layers(real, 5)
    assert np.bincount(list(dist5.values())).tolist() == [1, 18, 243, 3240, 43239, 574908]  # known HTM counts
    rng = random.Random(5)
    for _ in range(200):
        s = real.random_start(rng, rng.randint(1, 5))
        assert real.h(s) <= dist5[s]
    assert all(real.h(s) <= d for s, d in dist5.items())


@pytest.mark.slow
def test_astar_idastar_optimal_and_oracle_t_star_within_scramble_depth(real):
    rng = random.Random(6)
    assert_solvers_agree(real, real.random_start(rng, 5))  # against plain BFS
    oracle = Oracle(real)
    for depth in (5, 6, 7, 7):
        s = real.random_start(rng, depth)
        a, i = astar.solve(real, s), idastar.solve(real, s)
        assert a.status == i.status == "ok" and a.cost == i.cost == oracle.dist(s) <= depth


@pytest.mark.slow
def test_cube3_bench_reports_bfs_node_limit_rows(tmp_path):
    bench.main(["solvers", "--bench", "cube3", "--n", "1", "--max_nodes", "20000", "--out", str(tmp_path)])
    rows = list(csv.DictReader(open(tmp_path / "solvers_cube3.csv")))
    assert {r["T"] for r in rows} == {"3", "5", "7", "9"}
    assert any(r["solver"] == "bfs" and r["status"] == "node_limit" for r in rows)
    assert all(r["status"] == "ok" for r in rows if r["solver"] in ("astar", "idastar"))


def test_truncated_cache_is_rebuilt_and_saves_leave_no_temp_files(tmp_path, monkeypatch):
    c2 = cube2.Cube2.shared()
    cache = tmp_path / "pdb.npy"
    monkeypatch.setattr(cube3, "_CACHE", cache)
    monkeypatch.setattr(cube3, "build_pdb", lambda PM, TM: c2.dist.copy())
    np.save(cache, c2.dist)
    cache.write_bytes(cache.read_bytes()[:200])  # an interrupted np.save leaves a truncated .npy
    assert np.array_equal(cube3.load_or_build(c2.PM, c2.TM), c2.dist)  # rebuilt, not an exception
    assert np.array_equal(np.load(cache), c2.dist) and [p.name for p in tmp_path.iterdir()] == ["pdb.npy"]
