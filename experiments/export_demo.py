"""Export a JSON trace for the frontend demo (see demo/index.html).

Builds the plan graph for two hand-verified candidates -- one BFS-optimal
solving plan, one adversarial plan that deliberately walks through an
"uncertain" wall-hug and then a hard corner-deadlock -- under three modes:

  - baseline    : Phase 1, no validator, flat cost.
  - validated   : Phase 1 + Phase 2 validator + Phase 4 scoring.
  - experience  : the same, plus Phase 3 -- one earlier "episode" already
                  recorded a mismatch on the first uncertain step of each
                  plan, so that exact transition is now less trusted here,
                  even though the validator's own verdict on it is
                  unchanged.

Every step in every trace also carries its Phase 4 score breakdown
(goal-distance change, regression, budget pressure, resulting cost) when
a validator is in play, so the demo can show the scoring formula's
components per step instead of only a single aggregate number. Also runs
the Phase 2 stress test (experiments/stress_test.py) for the aggregate
numbers panel.

Run: python experiments/export_demo.py   (writes demo/index.html)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root))

from tape.envs.sokoban import SokobanLevel, State
from tape.experience import ExperienceStore
from tape.llm import _bfs_plan
from tape.solver import select_path
from tape.graph import build_plan_graph, build_validated_plan_graph
from tape.scoring import score_transition
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

LEVEL_ID = "demo"


def state_dict(state: State) -> dict:
    return {"player": list(state.player), "boxes": [list(b) for b in state.boxes]}


def find_first_uncertain(level, start, plan, validator) -> tuple[State, str] | None:
    """The first (state, action) in this plan the validator accepts but
    doesn't fully trust -- the transition Phase 3 will "learn about" by
    having one earlier episode record a mismatch on it."""
    cur = start
    for action in plan:
        nxt, moved = level.step(cur, action)
        if not moved:
            return None
        verdict = validator.validate(level, cur, action, nxt)
        if not verdict.accept:
            return None
        if verdict.confidence < 1.0:
            return (cur, action)
        cur = nxt
        if level.is_goal(cur):
            return None
    return None


def trace_candidate(
    level: SokobanLevel,
    start: State,
    plan: list[str],
    validator=None,
    experience: ExperienceStore | None = None,
    level_id: str = LEVEL_ID,
    max_depth: int | None = None,
    flagged: tuple[State, str] | None = None,
) -> list[dict]:
    steps = []
    cur = start
    for step_index, action in enumerate(plan):
        nxt, moved = level.step(cur, action)
        if not moved:
            steps.append(
                {"action": action, "from": state_dict(cur), "to": state_dict(cur),
                 "accepted": False, "confidence": 0.0, "reason": "illegal move (wall/blocked box)",
                 "learned_from_failure": False}
            )
            break

        is_flagged = flagged is not None and cur == flagged[0] and action == flagged[1]

        if validator is not None:
            verdict = validator.validate(level, cur, action, nxt)
            accept, reason, confidence = verdict.accept, verdict.reason, verdict.confidence
            if accept and experience is not None:
                confidence = confidence * experience.confidence(level_id, cur, action)
        else:
            accept, reason, confidence = True, "ok", 1.0

        step = {
            "action": action,
            "from": state_dict(cur),
            "to": state_dict(nxt),
            "accepted": accept,
            "confidence": confidence,
            "reason": reason,
            "learned_from_failure": is_flagged,
        }
        if validator is not None and accept:
            score = score_transition(level, cur, nxt, step_index, max_depth or len(plan), confidence)
            step["score"] = {
                "goal_distance_before": score.goal_distance_before,
                "goal_distance_after": score.goal_distance_after,
                "regression": score.regression,
                "budget_used_fraction": round(score.budget_used_fraction, 2),
                "cost": score.cost,
            }
        steps.append(step)
        if validator is not None and not accept:
            break
        cur = nxt
        if level.is_goal(cur):
            break
    return steps


def run_phase5_comparison(n_episodes: int = 20) -> dict:
    """Real measured evidence for Phase 5: run full episodes with CP-SAT,
    A*, and adaptive path selection, on both a single-box level (should
    route to A*) and a two-box level (should route to CP-SAT)."""
    from tape.envs.sokoban import LEVEL_MULTI, LEVEL_SIMPLE
    from tape.executor import run_episode
    from tape.llm import MockLLMClient
    from tape.metrics import aggregate

    def run(level, method, n_candidates, max_depth, max_replans=3):
        episodes = [
            run_episode(
                level, MockLLMClient(seed=i), n_candidates=n_candidates,
                max_depth=max_depth, max_replans=max_replans, path_selection=method,
            )
            for i in range(n_episodes)
        ]
        agg = aggregate(episodes)
        methods = sorted({m for ep in episodes for m in ep.path_selection_methods})
        return agg, methods

    cp_sat_agg, _ = run(LEVEL_SIMPLE, "cp_sat", 6, 15)
    astar_agg, _ = run(LEVEL_SIMPLE, "astar", 6, 15)
    _, adaptive_simple_methods = run(LEVEL_SIMPLE, "adaptive", 6, 15)
    _, adaptive_multi_methods = run(LEVEL_MULTI, "adaptive", 20, 14)

    return {
        "n_episodes": n_episodes,
        "cp_sat": {
            "avg_planning_time_s": cp_sat_agg.avg_planning_time_s,
            "avg_execution_cost": cp_sat_agg.avg_execution_cost,
            "success_rate": cp_sat_agg.success_rate,
        },
        "astar": {
            "avg_planning_time_s": astar_agg.avg_planning_time_s,
            "avg_execution_cost": astar_agg.avg_execution_cost,
            "success_rate": astar_agg.success_rate,
        },
        "speedup": (cp_sat_agg.avg_planning_time_s / astar_agg.avg_planning_time_s) if astar_agg.avg_planning_time_s else None,
        "adaptive_simple_methods": adaptive_simple_methods,
        "adaptive_multi_methods": adaptive_multi_methods,
    }


def build_phase5_visual() -> dict:
    """An actual step-by-step solve trace for Phase 5, on two different
    levels, so the adaptive rule's two branches are both visible as real
    box movement instead of only aggregate timing numbers:
      - single-box demo level: decide_method routes to A*.
      - two-box LEVEL_MULTI: decide_method routes to CP-SAT, because two
        boxes have to be pushed without one blocking the other.
    """
    from tape.envs.sokoban import LEVEL_MULTI
    from tape.path_selector import select_path_adaptive

    def visual(level: SokobanLevel) -> dict:
        start = level.initial_state
        plan = _bfs_plan(level, start, 20)
        graph = build_plan_graph(level, start, [plan])
        solution, method = select_path_adaptive(level, graph)
        return {
            "walls": [list(w) for w in level.walls],
            "goals": [list(g) for g in level.goals],
            "width": level.width,
            "height": level.height,
            "start": state_dict(start),
            "actions": solution.actions,
            "states": [state_dict(s) for s in solution.node_path[1:]],
            "method": method,
            "cost": solution.cost,
        }

    return {
        "single": visual(SokobanLevel(DEMO_LEVEL_ROWS)),
        "two_box": visual(LEVEL_MULTI),
    }


def build_river_crossing_demo() -> dict:
    """River crossing: a completely different mechanic (no grid, just two
    head counts and a boat side). Shows the same "judged differently"
    moment as the Sokoban demo -- taking 2 missionaries across first is
    physically legal and looks like fast progress, but leaves 1
    missionary alone with 3 cannibals -- plus a full live solve of the
    real 11-move safe answer."""
    from tape.envs.river_crossing import LEVEL_CLASSIC as RC_LEVEL
    from tape.envs.river_crossing_validator import RiverSafetyValidator
    from tape.path_selector import astar_select_path

    level = RC_LEVEL
    validator = RiverSafetyValidator()
    start = level.initial_state

    def rc_state(s) -> dict:
        return {
            "missionaries_left": s.missionaries_left,
            "cannibals_left": s.cannibals_left,
            "boat_left": s.boat_left,
        }

    def rc_trace(plan: list[str], use_validator: bool) -> list[dict]:
        steps = []
        cur = start
        for action in plan:
            nxt, moved = level.step(cur, action)
            if not moved:
                steps.append({
                    "action": action, "from": rc_state(cur), "to": rc_state(cur),
                    "accepted": False, "confidence": 0.0, "reason": "not enough people on that bank",
                })
                break
            if use_validator:
                verdict = validator.validate(level, cur, action, nxt)
                accept, reason, confidence = verdict.accept, verdict.reason, verdict.confidence
            else:
                accept, reason, confidence = True, "ok", 1.0
            steps.append({
                "action": action, "from": rc_state(cur), "to": rc_state(nxt),
                "accepted": accept, "confidence": confidence, "reason": reason,
            })
            if use_validator and not accept:
                break
            cur = nxt
            if level.is_goal(cur):
                break
        return steps

    bad_plan = ["2M"]  # the tempting-but-fatal first move
    safe_plan = _bfs_plan(level, start, 20, validator=validator)
    graph = build_plan_graph(level, start, [safe_plan])
    solution = astar_select_path(level, graph)

    return {
        "n": level.n,
        "start": rc_state(start),
        "bad_trace_baseline": rc_trace(bad_plan, use_validator=False),
        "bad_trace_validated": rc_trace(bad_plan, use_validator=True),
        "solve": {
            "actions": solution.actions,
            "states": [rc_state(s) for s in solution.node_path[1:]],
            "cost": solution.cost,
        },
    }


def build_rush_hour_demo() -> dict:
    """Rush Hour: multi-cell oriented vehicles instead of single-cell
    boxes or headcounts -- the most visually distinct of the three
    benchmarks. Shows the real 6-move solve (vehicles sliding, not just
    a box) and the validator's dynamic "uncertain" tier (the hard-reject
    tier is a static level-design invariant, not something a move
    creates -- see progress.md 8.2.1 -- so it isn't staged as a live
    "move causes deadlock" moment here, that would misrepresent it)."""
    from tape.envs.rush_hour import LEVEL_CLASSIC as RH_LEVEL, RushHourLevel
    from tape.envs.rush_hour_validator import RowGridlockValidator
    from tape.path_selector import select_path_adaptive

    level = RH_LEVEL
    validator = RowGridlockValidator()
    start = level.initial_state

    def rh_state(s) -> list[list]:
        return [list(p) for p in s]

    def rh_meta(lv: RushHourLevel) -> dict:
        return {
            vid: {"orientation": lv.orientation_of(vid), "length": lv.length_of(vid)}
            for vid in lv.vehicle_ids
        }

    good_plan = _bfs_plan(level, start, 20)
    graph = build_plan_graph(level, start, [good_plan])
    solution, method = select_path_adaptive(level, graph)

    # Constructed example for the soft "uncertain" tier: D is boxed
    # between X and a vertical vehicle E that currently can't move away
    # either -- a real, dynamic, worth-distrusting signal, explicitly not
    # a hard reject, since E might still move away later.
    demo_level = RushHourLevel(["....E.", "....E.", "XXDDE.", "......"])
    demo_state = demo_level.initial_state
    verdict = validator.validate(demo_level, demo_state, "D+", demo_state)

    return {
        "width": level.width,
        "height": level.height,
        "vehicles": rh_meta(level),
        "start": rh_state(start),
        "solve": {
            "actions": solution.actions,
            "states": [rh_state(s) for s in solution.node_path[1:]],
            "method": method,
            "cost": solution.cost,
        },
        "uncertain_demo": {
            "width": demo_level.width,
            "height": demo_level.height,
            "vehicles": rh_meta(demo_level),
            "state": rh_state(demo_state),
            "validated_confidence": verdict.confidence,
            "validated_reason": verdict.reason,
        },
    }


def mode_stats(graph, solution) -> dict:
    stats = {
        "graph_nodes": graph.graph.number_of_nodes(),
        "graph_edges": graph.graph.number_of_edges(),
        "invalid_transitions": graph.invalid_transitions,
        "solver_actions": solution.actions if solution else None,
        "solver_cost": solution.cost if solution else None,
    }
    if hasattr(graph, "validator_rejections"):
        stats["validator_rejections"] = graph.validator_rejections
    return stats


def main() -> None:
    level = SokobanLevel(DEMO_LEVEL_ROWS)
    start = level.initial_state
    validator = CornerDeadlockValidator()

    good_plan = _bfs_plan(level, start, 20)
    candidates = [good_plan, BAD_PLAN]
    budget = max(len(good_plan), len(BAD_PLAN))

    # Phase 3 setup: pretend one earlier episode already ran each plan and
    # mismatched on its first uncertain step.
    experience = ExperienceStore()
    flagged_good = find_first_uncertain(level, start, good_plan, validator)
    flagged_bad = find_first_uncertain(level, start, BAD_PLAN, validator)
    if flagged_good:
        experience.record(LEVEL_ID, *flagged_good, success=False)
    if flagged_bad:
        experience.record(LEVEL_ID, *flagged_bad, success=False)

    baseline_graph = build_plan_graph(level, start, candidates)
    validated_graph = build_validated_plan_graph(level, start, candidates, validator, max_depth=budget)
    experience_graph = build_validated_plan_graph(
        level, start, candidates, validator, experience=experience, level_id=LEVEL_ID, max_depth=budget
    )

    data = {
        "level": {
            "rows": DEMO_LEVEL_ROWS,
            "walls": [list(w) for w in level.walls],
            "goals": [list(g) for g in level.goals],
            "start": state_dict(start),
        },
        "modes": {
            "baseline": {
                "good_trace": trace_candidate(level, start, good_plan),
                "bad_trace": trace_candidate(level, start, BAD_PLAN),
                **mode_stats(baseline_graph, select_path(baseline_graph)),
            },
            "validated": {
                "good_trace": trace_candidate(level, start, good_plan, validator=validator, max_depth=budget, flagged=flagged_good),
                "bad_trace": trace_candidate(level, start, BAD_PLAN, validator=validator, max_depth=budget, flagged=flagged_bad),
                **mode_stats(validated_graph, select_path(validated_graph)),
            },
            "experience": {
                "good_trace": trace_candidate(
                    level, start, good_plan, validator=validator, experience=experience,
                    level_id=LEVEL_ID, max_depth=budget, flagged=flagged_good,
                ),
                "bad_trace": trace_candidate(
                    level, start, BAD_PLAN, validator=validator, experience=experience,
                    level_id=LEVEL_ID, max_depth=budget, flagged=flagged_bad,
                ),
                **mode_stats(experience_graph, select_path(experience_graph)),
            },
        },
        "stress_test": run_stress_test(),
        "phase5": run_phase5_comparison(),
        "phase5_visual": build_phase5_visual(),
        "river_crossing": build_river_crossing_demo(),
        "rush_hour": build_rush_hour_demo(),
    }

    demo_dir = Path(__file__).resolve().parents[1] / "demo"
    template = (demo_dir / "template.html").read_text(encoding="utf-8")
    html = template.replace("__DEMO_DATA_JSON__", json.dumps(data))
    out_path = demo_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path}")
    for mode in ("baseline", "validated", "experience"):
        m = data["modes"][mode]
        print(f"{mode} solver: {m['solver_actions']} cost={m['solver_cost']}")
    p5 = data["phase5"]
    print(f"phase5: cp_sat={p5['cp_sat']['avg_planning_time_s']:.4f}s astar={p5['astar']['avg_planning_time_s']:.4f}s speedup={p5['speedup']:.1f}x")
    print(f"phase5: adaptive on simple={p5['adaptive_simple_methods']} adaptive on multi={p5['adaptive_multi_methods']}")
    pv = data["phase5_visual"]
    print(f"phase5_visual: single method={pv['single']['method']} actions={pv['single']['actions']}")
    print(f"phase5_visual: two_box method={pv['two_box']['method']} actions={pv['two_box']['actions']}")


if __name__ == "__main__":
    main()
