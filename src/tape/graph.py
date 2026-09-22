"""Merge multiple candidate plans into a single plan graph (TAPE Phase 1).

Each candidate action sequence is simulated step by step from the current
real state. Identical resulting states across different candidates collapse
onto the same graph node (this is the "merging" TAPE describes). A candidate
step that turns out illegal (wall ahead, unpushable box) is simply not added
as an edge -- that candidate's path dead-ends in the graph. There is no
separate validator yet (that's Phase 2); this is exactly the baseline's
"trust the LLM, discover problems structurally" behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from tape.env_base import Environment, State
from tape.experience import ExperienceStore
from tape.scoring import ScoreWeights, score_transition
from tape.validator import GraphValidator


@dataclass
class PlanGraphResult:
    graph: nx.DiGraph
    start: State
    goal_nodes: list[State] = field(default_factory=list)
    attempted_transitions: int = 0
    invalid_transitions: int = 0
    validator_rejections: int = 0

    @property
    def invalid_transition_rate(self) -> float:
        if self.attempted_transitions == 0:
            return 0.0
        return (self.invalid_transitions + self.validator_rejections) / self.attempted_transitions


def build_plan_graph(
    level: Environment, start: State, candidate_plans: list[list[str]]
) -> PlanGraphResult:
    graph = nx.DiGraph()
    graph.add_node(start)
    result = PlanGraphResult(graph=graph, start=start)

    for plan in candidate_plans:
        cur = start
        for action in plan:
            result.attempted_transitions += 1
            nxt, moved = level.step(cur, action)
            if not moved:
                result.invalid_transitions += 1
                break
            if not graph.has_edge(cur, nxt):
                graph.add_edge(cur, nxt, action=action, cost=1)
            cur = nxt
            if level.is_goal(cur):
                break

    result.goal_nodes = [n for n in graph.nodes if level.is_goal(n)]
    return result


def build_validated_plan_graph(
    level: Environment,
    start: State,
    candidate_plans: list[list[str]],
    validator: GraphValidator,
    experience: ExperienceStore | None = None,
    level_id: str = "default",
    max_depth: int | None = None,
    weights: ScoreWeights = ScoreWeights(),
) -> PlanGraphResult:
    """Same as `build_plan_graph`, but every physically-legal step is also
    passed through `validator` before being accepted as an edge. A rejected
    step dead-ends that candidate (Phase 2 behaviour: catch it here instead
    of only at execution-time mismatch).

    When `experience` is given (Phase 3), its recorded success/failure
    history for this exact (state, action) further scales the confidence --
    a transition that has repeatedly mismatched execution in past episodes
    gets trusted less even if the validator has no objection to it.

    An accepted-but-uncertain step is still added, but its edge cost
    (Phase 4) is not just 1/confidence -- it's `score_transition`'s
    combined score: confidence, plus how much closer this step actually
    gets a box to a goal (a "legal" move that walks a box away from every
    goal is trusted just fine but still costs more), plus how much of
    this planning round's step budget has been used so far. The solver
    still just minimizes total cost; it now minimizes something closer to
    "least regressive, most trusted, most budget-efficient" instead of
    "fewest confident steps"."""
    graph = nx.DiGraph()
    graph.add_node(start)
    result = PlanGraphResult(graph=graph, start=start)
    budget = max_depth or (max((len(p) for p in candidate_plans), default=1) or 1)

    for plan in candidate_plans:
        cur = start
        for step_index, action in enumerate(plan):
            result.attempted_transitions += 1
            nxt, moved = level.step(cur, action)
            if not moved:
                result.invalid_transitions += 1
                break
            verdict = validator.validate(level, cur, action, nxt)
            if not verdict.accept:
                result.validator_rejections += 1
                break
            confidence = verdict.confidence
            if experience is not None:
                confidence *= experience.confidence(level_id, cur, action)
            score = score_transition(level, cur, nxt, step_index, budget, confidence, weights)
            if not graph.has_edge(cur, nxt) or graph.edges[cur, nxt]["cost"] > score.cost:
                graph.add_edge(
                    cur, nxt, action=action, cost=score.cost, confidence=confidence,
                    regression=score.regression,
                )
            cur = nxt
            if level.is_goal(cur):
                break

    result.goal_nodes = [n for n in graph.nodes if level.is_goal(n)]
    return result
