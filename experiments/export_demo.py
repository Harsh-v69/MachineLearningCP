"""Export a JSON trace for the frontend demo (see demo/index.html).

Builds the plan graph for two hand-verified candidates -- one BFS-optimal
solving plan, one adversarial plan that deliberately walks through an
"uncertain" wall-hug and then a hard corner-deadlock -- under both the
Phase 1 baseline and the Phase 2 validated graph builder, recording every
step's state, verdict, and confidence. Also runs the Phase-2 stress test
(experiments/stress_test.py) for the aggregate numbers panel.

Run: python experiments/export_demo.py   (writes demo/data.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root))

from tape.envs.sokoban import SokobanLevel, State
from tape.llm import _bfs_plan
from tape.solver import select_path
from tape.graph import build_plan_graph, build_validated_plan_graph
from tape.validator import CornerDeadlockValidator
from experiments.stress_test import run_stress_test

DEMO_LEVEL_ROWS = [
    "#######",
    "#     #",
    "#  $  #",
    "#     #",
    "#  @  #",
    "#    .#",
    "#######",
]

# Hand-verified (see conversation): walks through an "uncertain" wall-hug
# twice, then a hard corner-deadlock at the final push.
BAD_PLAN = ["U", "U", "R", "U", "L", "L"]


def state_dict(state: State) -> dict:
    return {"player": list(state.player), "boxes": [list(b) for b in state.boxes]}


def trace_candidate(level: SokobanLevel, start: State, plan: list[str], validator=None) -> list[dict]:
    steps = []
    cur = start
    for action in plan:
        nxt, moved = level.step(cur, action)
        if not moved:
            steps.append(
                {"action": action, "from": state_dict(cur), "to": state_dict(cur),
                 "accepted": False, "confidence": 0.0, "reason": "illegal move (wall/blocked box)"}
            )
            break
        if validator is not None:
            verdict = validator.validate(level, cur, action, nxt)
        else:
            verdict = None
        step = {
            "action": action,
            "from": state_dict(cur),
            "to": state_dict(nxt),
            "accepted": True if verdict is None else verdict.accept,
            "confidence": 1.0 if verdict is None else verdict.confidence,
            "reason": "ok" if verdict is None else verdict.reason,
        }
        steps.append(step)
        if verdict is not None and not verdict.accept:
            break
        cur = nxt
        if level.is_goal(cur):
            break
    return steps


def main() -> None:
    level = SokobanLevel(DEMO_LEVEL_ROWS)
    start = level.initial_state
    validator = CornerDeadlockValidator()

    good_plan = _bfs_plan(level, start, 20)
    candidates = [good_plan, BAD_PLAN]

    baseline_graph = build_plan_graph(level, start, candidates)
    validated_graph = build_validated_plan_graph(level, start, candidates, validator)

    baseline_solution = select_path(baseline_graph)
    validated_solution = select_path(validated_graph)

    data = {
        "level": {
            "rows": DEMO_LEVEL_ROWS,
            "walls": [list(w) for w in level.walls],
            "goals": [list(g) for g in level.goals],
            "start": state_dict(start),
        },
        "modes": {
            "baseline": {
                "good_trace": trace_candidate(level, start, good_plan, validator=None),
                "bad_trace": trace_candidate(level, start, BAD_PLAN, validator=None),
                "graph_nodes": baseline_graph.graph.number_of_nodes(),
                "graph_edges": baseline_graph.graph.number_of_edges(),
                "invalid_transitions": baseline_graph.invalid_transitions,
                "solver_actions": baseline_solution.actions if baseline_solution else None,
                "solver_cost": baseline_solution.cost if baseline_solution else None,
            },
            "validated": {
                "good_trace": trace_candidate(level, start, good_plan, validator=validator),
                "bad_trace": trace_candidate(level, start, BAD_PLAN, validator=validator),
                "graph_nodes": validated_graph.graph.number_of_nodes(),
                "graph_edges": validated_graph.graph.number_of_edges(),
                "invalid_transitions": validated_graph.invalid_transitions,
                "validator_rejections": validated_graph.validator_rejections,
                "solver_actions": validated_solution.actions if validated_solution else None,
                "solver_cost": validated_solution.cost if validated_solution else None,
            },
        },
        "stress_test": run_stress_test(),
    }

    demo_dir = Path(__file__).resolve().parents[1] / "demo"
    template = (demo_dir / "template.html").read_text(encoding="utf-8")
    html = template.replace("__DEMO_DATA_JSON__", json.dumps(data))
    out_path = demo_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"baseline solver: {data['modes']['baseline']['solver_actions']} cost={data['modes']['baseline']['solver_cost']}")
    print(f"validated solver: {data['modes']['validated']['solver_actions']} cost={data['modes']['validated']['solver_cost']}")


if __name__ == "__main__":
    main()
