"""Aggregate metrics across episodes -- the columns the Phase 6 evaluation
(baseline vs. proposed extensions) will compare."""
from __future__ import annotations

from dataclasses import dataclass

from tape.executor import EpisodeResult


@dataclass
class AggregateMetrics:
    success_rate: float
    avg_replans: float
    avg_invalid_transition_rate: float
    avg_planning_time_s: float
    avg_execution_cost: float
    n_episodes: int

    def report(self) -> str:
        return (
            f"episodes={self.n_episodes}  "
            f"success_rate={self.success_rate:.2%}  "
            f"avg_replans={self.avg_replans:.2f}  "
            f"avg_invalid_transition_rate={self.avg_invalid_transition_rate:.2%}  "
            f"avg_planning_time_s={self.avg_planning_time_s:.4f}  "
            f"avg_execution_cost={self.avg_execution_cost:.1f}"
        )


def aggregate(episodes: list[EpisodeResult]) -> AggregateMetrics:
    n = len(episodes)
    if n == 0:
        raise ValueError("no episodes to aggregate")
    return AggregateMetrics(
        success_rate=sum(e.success for e in episodes) / n,
        avg_replans=sum(e.replans for e in episodes) / n,
        avg_invalid_transition_rate=sum(e.invalid_transition_rate for e in episodes) / n,
        avg_planning_time_s=sum(e.planning_time_s for e in episodes) / n,
        avg_execution_cost=sum(e.total_actions for e in episodes) / n,
        n_episodes=n,
    )
