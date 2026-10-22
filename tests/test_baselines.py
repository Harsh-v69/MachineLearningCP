import random

from tapegraph.baselines import tape_sim
from tapegraph.baselines.react_sim import ReActSim
from tapegraph.baselines.replan import Replan
from tapegraph.baselines.tape_sim import TapeSim
from tapegraph.execute import evaluate, run_episode
from tapegraph.oracle import Oracle
from tapegraph.problems.river import River
from tapegraph.solvers import astar, ilp


def _river_case(depth=10, seed=0):
    p = River(8, 4)
    return p, Oracle(p), p.random_start(random.Random(seed), depth)


def test_noise_free_react_is_optimal():
    p, o, s = _river_case()
    ok, steps = run_episode(p, ReActSim(p, o, delta=0.0), s, B=12, eta=0.0, rng=random.Random(0))
    assert ok and steps == 10


def test_react_with_always_wrong_planning_fails_at_zero_slack():
    p, o, s = _river_case()
    r = evaluate(p, s, ReActSim(p, o, delta=1.0), B=10, eta=0.0, episodes=20, seed=0)
    assert r["success"] < 0.5


def test_replan_is_optimal_without_noise_and_solves_once():
    p, o, s = _river_case()
    pol = Replan(p, astar.solve)
    r = evaluate(p, s, pol, B=10, eta=0.0, episodes=5, seed=0)
    assert r["success"] == 1.0 and r["mean_steps"] == 10 and r["solves"] == 1.0


def test_replan_recovers_from_a_deviation():
    p, o, s = _river_case()
    pol = Replan(p, astar.solve)
    pol.reset(0)
    a = pol.act(s, 12)
    other = next(a2 for a2, _, _ in p.neighbors(s) if a2 != a)
    s_dev = p.step(s, other)  # the world did something else
    a2 = pol.act(s_dev, 11)
    assert pol.solves == 2
    assert o.dist(p.step(s_dev, a2)) <= 11  # the new plan starts from the observed state


def test_tape_sim_without_planning_error_succeeds():
    p, o, s = _river_case()
    pol = TapeSim(p, o, delta=0.0, N=2, use_ilp=False)
    r = evaluate(p, s, pol, B=12, eta=0.0, episodes=5, seed=0)
    assert r["success"] == 1.0


def test_tape_sim_survives_ilp_timeout(monkeypatch):
    def boom(*a, **k):
        raise ilp.IlpTimeout("forced")

    monkeypatch.setattr(tape_sim.ilp, "solve_graph", boom)
    p, o, s = _river_case()
    pol = TapeSim(p, o, delta=0.0, N=2, use_ilp=True)
    pol.use_ilp = True  # even if ortools were missing, force the patched path
    pol.reset(0)
    assert pol.act(s, 12) in [a for a, _, _ in p.neighbors(s)]


def test_replan_beats_react_under_noise():
    p, o, s = _river_case(depth=12)
    B, eta, delta = 12 + 2, 0.04, 0.16
    react = evaluate(p, s, ReActSim(p, o, delta), B, eta, episodes=100, seed=1)
    ours = evaluate(p, s, Replan(p, astar.solve), B, eta, episodes=100, seed=1)
    assert ours["success"] > react["success"]
