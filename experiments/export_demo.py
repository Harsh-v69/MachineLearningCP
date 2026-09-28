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
import re
import statistics
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

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


GAMES = {
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
    good = _bfs_plan(level, start, depth, validator=validator)
    found = find_bad_step(level, validator, start)
    prefix, bad_action, kind = found
    after, _ = level.step(_replay(level, start, prefix), bad_action)
    tail = _bfs_plan(level, after, depth)  # what an unchecked planner would do next
    bad = prefix + [bad_action] + (tail if level.is_goal(_replay(level, after, tail)) else [])

    plans = [good, bad]
    pg = build_validated_plan_graph(level, start, plans, validator, max_depth=max(map(len, plans)))
    _, astar_ms = timed(lambda: astar_select_path(level, pg))
    _, cpsat_ms = timed(lambda: select_path(pg))
    sol, method = select_path_adaptive(level, pg)

    # Run stage: a slip after step k leaves the world at node k; replan from there.
    k = min(2, len(sol.actions) - 2)
    real = sol.node_path[k]
    re_plan = _bfs_plan(level, real, depth, validator=validator)
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


def read_results() -> dict:
    with open(ROOT / "results" / "ablation.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["llm"] == "goal-biased"]
    cell = lambda b, c: next(r for r in rows if r["benchmark"] == b and r["config"] == c)
    river = "river-crossing"
    txt = (ROOT / "results" / "experience_test.md").read_text(encoding="utf-8")
    box = (ROOT / "results" / "boxoban.md").read_text(encoding="utf-8")
    return {
        "boxoban": {"levels": int(re.search(r"\((\d+) levels", box).group(1)),
                    "rows": [{"budget": m[0], "plain": int(m[1]), "prune": int(m[2])}
                             for m in re.findall(r"\| ([\d,]+) \| (\d+)% \[[^\]]*\] \| (\d+)% \[", box)]},
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
    return {"games": {gid: build_game(gid) for gid in GAMES}, "results": read_results()}


def main() -> None:
    tpl = (ROOT / "demo" / "template.html").read_text(encoding="utf-8")
    html = tpl.replace("__DEMO_DATA_JSON__", json.dumps(build_data(), separators=(",", ":")))
    (ROOT / "demo" / "index.html").write_text(html, encoding="utf-8")
    print("wrote demo/index.html")


if __name__ == "__main__":
    main()
