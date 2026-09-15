"""Phase 3: record executed transitions across episodes and let past
outcomes bias future confidence -- the "self-improving graph".

A transition's outcome here is defined the same way TAPE defines planning
error: did the real environment match what the graph predicted after this
(state, action)? Every mismatch is a failure signal for that exact
transition; every match is a success signal. Repeatedly-mismatching
transitions become less trusted the next time they show up in a candidate
plan, even if the validator and raw environment both call them legal.

Uses sqlite3 (stdlib) rather than standing up Postgres -- the data is a
handful of (level, state, action) -> counts rows, well within what a flat
file handles, and this keeps the project runnable with zero extra infra.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from tape.envs.sokoban import State


@dataclass
class TransitionStats:
    successes: int
    failures: int

    @property
    def confidence(self) -> float:
        total = self.successes + self.failures
        if total == 0:
            return 1.0  # no history yet -- defer entirely to the validator/environment
        # Laplace smoothing: one early failure shouldn't zero out confidence forever.
        return (self.successes + 1) / (total + 2)


def _state_key(state: State) -> str:
    return f"{state.player}|{sorted(state.boxes)}"


class ExperienceStore:
    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS transitions (
                level_id TEXT NOT NULL,
                from_key TEXT NOT NULL,
                action TEXT NOT NULL,
                successes INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (level_id, from_key, action)
            )"""
        )
        self._conn.commit()

    def record(self, level_id: str, from_state: State, action: str, success: bool) -> None:
        from_key = _state_key(from_state)
        column = "successes" if success else "failures"
        self._conn.execute(
            f"""INSERT INTO transitions (level_id, from_key, action, {column})
                VALUES (?, ?, ?, 1)
                ON CONFLICT(level_id, from_key, action)
                DO UPDATE SET {column} = {column} + 1""",
            (level_id, from_key, action),
        )
        self._conn.commit()

    def stats(self, level_id: str, from_state: State, action: str) -> TransitionStats:
        row = self._conn.execute(
            "SELECT successes, failures FROM transitions WHERE level_id=? AND from_key=? AND action=?",
            (level_id, _state_key(from_state), action),
        ).fetchone()
        return TransitionStats(*row) if row else TransitionStats(0, 0)

    def confidence(self, level_id: str, from_state: State, action: str) -> float:
        return self.stats(level_id, from_state, action).confidence

    def close(self) -> None:
        self._conn.close()
