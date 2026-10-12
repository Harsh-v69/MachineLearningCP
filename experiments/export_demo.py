"""Build demo/index.html: a guided walkthrough of the pipeline on each game.

Everything on the page comes from a live run of the real code:
  - a good plan (validator-aware BFS) and a bad plan (found by search: a
    legal-looking move the validator flags) per game,
  - the merged plan graph of both,
  - both solvers timed on that graph,
  - an episode with a forced slip, then a replan,
  - headline numbers read from results/*.csv and results/*.md.

Run: python experiments/export_demo.py   (writes demo/index.html)
"""
from __future__ import annotations

import csv
import json
import random
import re
import statistics
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tape.bidirectional import BidirectionalProposer
from tape.envs.peg_solitaire import LEVEL_CLASSIC as PEG
from tape.envs.peg_solitaire_validator import PegPagodaValidator
from tape.envs.rubiks_cube import CUBE_3
from tape.envs.rubiks_cube_validator import CubeSolvabilityValidator
from tape.envs.sliding_puzzle import LEVEL_24
from tape.envs.sliding_puzzle_validator import SlidingParityValidator
from tape.search_proposer import WeightedAStarProposer
from tape.envs.river_crossing import LEVEL_CLASSIC as RIVER
from tape.envs.river_crossing_validator import RiverSafetyValidator
from tape.envs.rush_hour import LEVEL_CLASSIC as RUSH
from tape.envs.rush_hour_validator import RowGridlockValidator
from tape.envs.sokoban import SokobanLevel
from tape.experience import ExperienceStore
from tape.graph import build_validated_plan_graph
from tape.llm import _bfs_plan
from tape.path_selector import astar_select_path, select_path_adaptive
from tape.solver import select_path
from tape.validator import CornerDeadlockValidator

DEMO_LEVEL_ROWS = [
    "#######",
    "#     #",
    "#  $  #",
    "#     #",
    "#  @  #",
    "#    .#",
    "#######",
]
# Kept for tests/test_scoring.py: a hand-verified plan that wall-hugs twice, then corner-deadlocks.
BAD_PLAN = ["U", "U", "R", "U", "L", "L"]

SOKOBAN = SokobanLevel(DEMO_LEVEL_ROWS)


def ser_sokoban(s):
    return {"p": list(s.player), "b": sorted(list(b) for b in s.boxes)}


def ser_river(s):
    return {"m": s.missionaries_left, "c": s.cannibals_left, "boat": s.boat_left}


def ser_rush(s):
    return sorted([list(p) for p in s])


def ser_peg(s):
    return [list(p) for p in sorted(PEG.pegs(s))]


def ser_flat(s):
    return list(s)


# ---- the three harder games: plans come from searches, not from BFS -------
PUZZLE = LEVEL_24.with_start(LEVEL_24.scramble(24, random.Random(5)))
CUBE = CUBE_3.with_start(CUBE_3.scramble(6, random.Random(3)))


def _puz_search(weight):
    def plan(level, state, validator):
        p = WeightedAStarProposer(weights=(weight,), node_budget=60_000, validator=validator)
        return p.generate_candidate_plans(level, state, 1, 400)[0]
    return plan


def _peg_plan(level, state, validator):
    p = WeightedAStarProposer(weights=(2,), node_budget=400_000, validator=validator)
    return p.generate_candidate_plans(level, state, 1, 60)[0]


def _peg_bad(level, validator, start, good):
    """A random line of play that walks into a position the pagoda bound rules out."""
    for seed in range(5000):
        rng, s, plan, first = random.Random(seed), start, [], None
        while True:
            moves = [(a, n) for a in level.ACTIONS for n, ok in [level.step(s, a)] if ok]
            if not moves:
                break
            a, n = rng.choice(moves)
            if first is None and not validator.validate(level, s, a, n).accept:
                first = len(plan)
            plan.append(a)
            s = n
        if first is not None and first >= 14:
            return plan[:first], plan[first], "rejected", plan
    raise RuntimeError("no random game hit the pagoda bound")


def _static_bad(plan_fn):
    """Games whose checker only guards the start: Plan B is a longer, still valid plan."""
    def bad(level, validator, start, good):
        return [], None, "static", plan_fn(level, start, validator)
    return bad


def _cube_plan(level, state, validator):
    return BidirectionalProposer(validator=validator).generate_candidate_plans(level, state, 1, 12)[0]


def _cube_bad(level, validator, start, good):
    """The best solution that opens with a different first move than Plan A."""
    best = None
    for a in level.ACTIONS:
        if a == good[0]:
            continue
        nxt, _ = level.step(start, a)
        rest = BidirectionalProposer(validator=validator).generate_candidate_plans(level, nxt, 1, 12)
        if rest and (best is None or 1 + len(rest[0]) < len(best)):
            best = [a] + rest[0]
    return [], None, "static", best


def _gate(prop_factory, budget):
    """Nodes spent on an unsolvable start with and without the checker."""
    def gate(level, validator, start, ser, broken):
        lv = level.with_start(broken)
        used = {}
        for arm, v in (("plain", None), ("gated", validator)):
            p = prop_factory(budget, v)
            p.generate_candidate_plans(lv, broken, 1, 400)
            used[arm] = p.expansions
        return {"start": ser(broken), "plain": used["plain"], "gated": used["gated"], "budget": budget}
    return gate


def _twist_corner(validator, state):
    o = validator._corners[0]
    t = list(state)
    t[o[0]], t[o[1]], t[o[2]] = state[o[1]], state[o[2]], state[o[0]]
    return tuple(t)


_CUBE_VAL = CubeSolvabilityValidator(CUBE_3)

GAMES = {
    "peg": dict(
        level=PEG, validator=PegPagodaValidator(), ser=ser_peg, depth=40, piece="32 pegs",
        plan=_peg_plan, bad=_peg_bad,
        static=lambda lv: {"cells": [list(c) for c in lv.cells], "center": [3, 3]}),
    "puzzle": dict(
        level=PUZZLE, validator=SlidingParityValidator(), ser=ser_flat, depth=80, piece="1 blank",
        plan=_puz_search(2), bad=_static_bad(_puz_search(8)),
        gate=_gate(lambda b, v: WeightedAStarProposer(weights=(3,), node_budget=b, validator=v), 20_000),
        broken=lambda lv, v, s: lv.unsolvable_twin(s),
        static=lambda lv: {"n": lv.n}),
    "cube": dict(
        level=CUBE, validator=_CUBE_VAL, ser=ser_flat, depth=12, piece="1 cube",
        plan=_cube_plan, bad=_cube_bad,
        gate=_gate(lambda b, v: BidirectionalProposer(node_budget=b, validator=v), 100_000),
        broken=lambda lv, v, s: _twist_corner(v, s),
        static=lambda lv: {"n": lv.n, "slots": [[list(p), list(nm)] for p, nm in lv.slots]}),
    "sokoban": dict(
        level=SOKOBAN, validator=CornerDeadlockValidator(), ser=ser_sokoban, depth=20, piece="1 box",
        static=lambda lv: {"w": lv.width, "h": lv.height,
                           "walls": sorted(list(w) for w in lv.walls),
                           "goals": sorted(list(g) for g in lv.goals)}),
    "river": dict(
        level=RIVER, validator=RiverSafetyValidator(), ser=ser_river, depth=20, piece="1 boat",
        static=lambda lv: {"n": lv.n}),
    "rush": dict(
        level=RUSH, validator=RowGridlockValidator(), ser=ser_rush, depth=20, piece="5 vehicles",
        static=lambda lv: {"w": lv.width, "h": lv.height,
                           "vehicles": {v: {"o": lv.orientation_of(v), "len": lv.length_of(v)}
                                        for v in lv.vehicle_ids}}),
}


def find_bad_step(level, validator, start, min_depth=2, cap=14):
    """BFS over accepted moves; return (prefix actions, flagged action, kind) for the
    nearest legal move the validator rejects (else the nearest it only doubts)."""
    frontier, seen = deque([(start, [])]), {start}
    doubt = None
    while frontier:
        cur, path = frontier.popleft()
        for a in level.ACTIONS:
            nxt, moved = level.step(cur, a)
            if not moved:
                continue
            if len(path) >= min_depth:
                v = validator.validate(level, cur, a, nxt)
                if not v.accept:
                    return path, a, "rejected"
                if v.confidence < 1 and doubt is None:
                    doubt = (path, a, "uncertain")
            if len(path) < cap and nxt not in seen and validator.validate(level, cur, a, nxt).accept:
                seen.add(nxt)
                frontier.append((nxt, path + [a]))
    return doubt


def _replay(level, start, actions):
    cur = start
    for a in actions:
        cur, _ = level.step(cur, a)
    return cur


def trace(g, start, plan, use_validator):
    level, validator, ser = g["level"], g["validator"], g["ser"]
    steps, cur = [], start
    for a in plan:
        nxt, moved = level.step(cur, a)
        if not moved:
            break
        ok, conf, why = True, 1.0, ""
        if use_validator:
            v = validator.validate(level, cur, a, nxt)
            ok, conf, why = v.accept, v.confidence, v.reason
        steps.append({"a": a, "s": ser(nxt), "ok": ok, "conf": round(conf, 2), "why": why})
        if use_validator and not ok:
            break
        cur = nxt
        if level.is_goal(cur):
            break
    reached = bool(steps) and steps[-1]["ok"] and level.is_goal(_replay(level, start, [s["a"] for s in steps]))
    return {"steps": steps, "goal": reached}


def plan_graph(g, start, plans):
    """Nodes and edges of the merged graph; rejected edges end in a dead-end stub."""
    level, validator = g["level"], g["validator"]
    ids, nodes, edges = {start: 0}, [{"id": 0, "layer": 0, "goal": level.is_goal(start)}], []
    for pi, plan in enumerate(plans):
        cur = start
        for i, a in enumerate(plan):
            nxt, moved = level.step(cur, a)
            if not moved:
                break
            v = validator.validate(level, cur, a, nxt)
            if not v.accept:
                nid = len(nodes)
                nodes.append({"id": nid, "layer": i + 1, "stub": True})
                edges.append({"s": ids[cur], "t": nid, "a": a, "plans": [pi], "st": "rejected"})
                break
            if nxt not in ids:
                ids[nxt] = len(nodes)
                nodes.append({"id": ids[nxt], "layer": i + 1, "goal": level.is_goal(nxt)})
            same = next((x for x in edges if x["s"] == ids[cur] and x["t"] == ids[nxt]), None)
            if same:
                same["plans"].append(pi)
            else:
                edges.append({"s": ids[cur], "t": ids[nxt], "a": a, "plans": [pi],
                              "st": "ok" if v.confidence == 1 else "uncertain"})
            cur = nxt
            if level.is_goal(cur):
                break
    return {"nodes": nodes, "edges": edges}


def timed(fn, reps=7):
    ts, out = [], None
    for _ in range(reps):
        t = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t) * 1000)
    return out, statistics.median(ts)


def build_game(gid: str) -> dict:
    g = GAMES[gid]
    level, validator, ser, depth = g["level"], g["validator"], g["ser"], g["depth"]
    start = level.initial_state
    plan_fn = g.get("plan") or (lambda lv, st, val: _bfs_plan(lv, st, depth, validator=val))
    good = plan_fn(level, start, validator)
    if "bad" in g:
        prefix, bad_action, kind, bad = g["bad"](level, validator, start, good)
    else:
        prefix, bad_action, kind = find_bad_step(level, validator, start)
        after, _ = level.step(_replay(level, start, prefix), bad_action)
        tail = _bfs_plan(level, after, depth)  # what an unchecked planner would do next
        bad = prefix + [bad_action] + (tail if level.is_goal(_replay(level, after, tail)) else [])
    gate = None
    if kind == "static":
        gate = g["gate"](level, validator, start, g["ser"], g["broken"](level, validator, start))

    plans = [good, bad]
    pg = build_validated_plan_graph(level, start, plans, validator, max_depth=max(map(len, plans)))
    _, astar_ms = timed(lambda: astar_select_path(level, pg))
    _, cpsat_ms = timed(lambda: select_path(pg))
    sol, method = select_path_adaptive(level, pg)

    # Run stage: a slip after step k leaves the world at node k; replan from there.
    k = min(2, len(sol.actions) - 2)
    real = sol.node_path[k]
    re_plan = plan_fn(level, real, validator)
    re_graph = build_validated_plan_graph(level, real, [re_plan], validator, max_depth=depth)
    re_sol, re_method = select_path_adaptive(level, re_graph)

    store = ExperienceStore()  # one recorded slip on the step that slipped
    store.record(gid, real, sol.actions[k], success=False)
    memory_conf = store.confidence(gid, real, sol.actions[k])

    return {
        "id": gid,
        "static": g["static"](level),
        "start": ser(start),
        "piece": g["piece"],
        "good": trace(g, start, good, True),
        "bad_plain": trace(g, start, bad, False),
        "bad_checked": trace(g, start, bad, True),
        "bad_kind": kind,
        "bad_at": len(prefix),
        "gate": gate,
        "graph": plan_graph(g, start, plans),
        "graph_stats": {"nodes": pg.graph.number_of_nodes(), "edges": pg.graph.number_of_edges(),
                        "rejected": pg.validator_rejections},
        "choose": {
            "method": method, "cost": sol.cost, "length": len(sol.actions),
            "astar_ms": round(astar_ms, 2), "cpsat_ms": round(cpsat_ms, 2),
            "actions": sol.actions, "states": [ser(s) for s in sol.node_path[1:]],
        },
        "run": {
            "slip_at": k, "before_actions": sol.actions[:k],
            "before": [ser(s) for s in sol.node_path[1:k + 1]],
            "slipped_action": sol.actions[k], "real": ser(real),
            "after_actions": re_sol.actions, "after": [ser(s) for s in re_sol.node_path[1:]],
            "method": re_method, "memory_conf": round(memory_conf, 2),
        },
    }


def build_boxoban() -> dict:
    """One real Boxoban level (medium set) that the search solves inside the
    node budget with the corner checker but not without it."""
    from tape.envs.boxoban import load_boxoban
    from tape.search_proposer import WeightedAStarProposer

    budget, val = 10_000, CornerDeadlockValidator()
    chosen = None
    for idx, lv in enumerate(load_boxoban(limit=80)):
        pruned = WeightedAStarProposer(weights=(4,), node_budget=budget, validator=val)
        plans = pruned.generate_candidate_plans(lv, lv.initial_state, 1, 400)
        if not plans:
            continue
        if WeightedAStarProposer(weights=(4,), node_budget=budget).generate_candidate_plans(lv, lv.initial_state, 1, 400):
            continue
        chosen = (idx, lv, plans[0], pruned.expansions)
        break
    if chosen is None:
        raise RuntimeError("no Boxoban level in the first 80 separates the two searches")
    idx, lv, plan, used = chosen
    big = WeightedAStarProposer(weights=(4,), node_budget=100_000)
    found = big.generate_candidate_plans(lv, lv.initial_state, 1, 400)
    states, cur = [], lv.initial_state
    for a in plan:
        cur, _ = lv.step(cur, a)
        states.append(ser_sokoban(cur))
    return {
        "index": idx, "budget": budget, "moves": len(plan), "prune_nodes": used,
        "plain_needs": big.expansions if found else None,
        "static": {"w": lv.width, "h": lv.height, "walls": sorted(list(w) for w in lv.walls),
                   "goals": sorted(list(g) for g in lv.goals)},
        "start": ser_sokoban(lv.initial_state), "actions": plan, "states": states,
    }


def read_results() -> dict:
    with open(ROOT / "results" / "ablation.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["llm"] == "goal-biased"]
    cell = lambda b, c: next(r for r in rows if r["benchmark"] == b and r["config"] == c)
    river = "river-crossing"
    txt = (ROOT / "results" / "experience_test.md").read_text(encoding="utf-8")
    def boxoban(name, fname):
        box = (ROOT / "results" / fname).read_text(encoding="utf-8")
        return {"name": name, "levels": int(re.search(r"\((\d+) levels", box).group(1)),
                "rows": [{"budget": m[0], "plain": int(m[1]), "prune": int(m[2])}
                         for m in re.findall(r"\| ([\d,]+) \| (\d+)% \[[^\]]*\] \| (\d+)% \[", box)]}

    hard = json.loads((ROOT / "results" / "hard_games.json").read_text(encoding="utf-8"))
    return {
        "hard": hard,
        "boxoban": [boxoban("Unfiltered", "boxoban_unfiltered.md"), boxoban("Medium", "boxoban.md"),
                    boxoban("Hard", "boxoban_hard.md")],
        "river": {"baseline": float(cell(river, "baseline")["success"]),
                  "raw": float(cell(river, "baseline")["raw_success"]),
                  "validated": float(cell(river, "+validator")["success"])},
        "speed": [{"name": n, "base": float(cell(b, "baseline")["plan_ms"]),
                   "adaptive": float(cell(b, "+adaptive")["plan_ms"])}
                  for n, b in [("Sokoban 1 box", "sokoban-simple"), ("Sokoban 2 box", "sokoban-multi"),
                               ("River crossing", river), ("Rush Hour", "rush-hour")]],
        "memory": [{"name": m[0], "diff": float(m[1]), "se": float(m[2])}
                   for m in re.findall(r"\| (\S+) \| ([+-][\d.]+) \+/- ([\d.]+) \|", txt)],
    }


def build_data() -> dict:
    return {"games": {gid: build_game(gid) for gid in GAMES}, "boxoban": build_boxoban(), "results": read_results()}


def main() -> None:
    tpl = (ROOT / "demo" / "template.html").read_text(encoding="utf-8")
    html = tpl.replace("__DEMO_DATA_JSON__", json.dumps(build_data(), separators=(",", ":")))
    (ROOT / "demo" / "index.html").write_text(html, encoding="utf-8")
    print("wrote demo/index.html")


if __name__ == "__main__":
    main()
