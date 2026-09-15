"""Minimal deterministic Sokoban environment.

Level grammar (one string per row):
    #  wall
    @  player on floor
    +  player on goal
    $  box on floor
    *  box on goal
    .  goal
    (space) floor

State is immutable and hashable: (player: (row, col), boxes: frozenset[(row, col)]).
Walls and goals are fixed per level and are not part of the state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

ACTIONS = ("U", "D", "L", "R")
_DELTA = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


@dataclass(frozen=True)
class State:
    player: tuple[int, int]
    boxes: frozenset[tuple[int, int]]


class SokobanLevel:
    def __init__(self, rows: Iterable[str]):
        rows = list(rows)
        self.height = len(rows)
        self.width = max(len(r) for r in rows)
        walls, goals, boxes = set(), set(), set()
        player = None
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                pos = (r, c)
                if ch == "#":
                    walls.add(pos)
                elif ch == "@":
                    player = pos
                elif ch == "+":
                    player = pos
                    goals.add(pos)
                elif ch == "$":
                    boxes.add(pos)
                elif ch == "*":
                    boxes.add(pos)
                    goals.add(pos)
                elif ch == ".":
                    goals.add(pos)
        if player is None:
            raise ValueError("level has no player start position")
        if len(boxes) != len(goals):
            raise ValueError("level has a mismatched number of boxes and goals")
        self.walls = frozenset(walls)
        self.goals = frozenset(goals)
        self.initial_state = State(player=player, boxes=frozenset(boxes))

    def in_bounds(self, pos: tuple[int, int]) -> bool:
        r, c = pos
        return 0 <= r < self.height and 0 <= c < self.width

    def is_goal(self, state: State) -> bool:
        return state.boxes == self.goals

    def is_valid_action(self, state: State, action: str) -> bool:
        return self.step(state, action)[1]

    def step(self, state: State, action: str) -> tuple[State, bool]:
        """Apply `action`. Returns (new_state, moved). If the move is illegal
        (wall ahead, or a box that can't be pushed), returns (state, False)
        unchanged -- this is how an invalid transition surfaces without a
        separate validator (added in Phase 2)."""
        if action not in _DELTA:
            return state, False
        dr, dc = _DELTA[action]
        pr, pc = state.player
        target = (pr + dr, pc + dc)
        if not self.in_bounds(target) or target in self.walls:
            return state, False
        if target in state.boxes:
            beyond = (target[0] + dr, target[1] + dc)
            if not self.in_bounds(beyond) or beyond in self.walls or beyond in state.boxes:
                return state, False
            new_boxes = (state.boxes - {target}) | {beyond}
            return State(player=target, boxes=frozenset(new_boxes)), True
        return State(player=target, boxes=state.boxes), True

    def render(self, state: State) -> str:
        lines = []
        for r in range(self.height):
            row_chars = []
            for c in range(self.width):
                pos = (r, c)
                if pos in self.walls:
                    row_chars.append("#")
                elif pos == state.player and pos in self.goals:
                    row_chars.append("+")
                elif pos == state.player:
                    row_chars.append("@")
                elif pos in state.boxes and pos in self.goals:
                    row_chars.append("*")
                elif pos in state.boxes:
                    row_chars.append("$")
                elif pos in self.goals:
                    row_chars.append(".")
                else:
                    row_chars.append(" ")
            lines.append("".join(row_chars))
        return "\n".join(lines)


LEVEL_TRIVIAL = SokobanLevel(
    [
        "#####",
        "#@$.#",
        "#####",
    ]
)

LEVEL_SIMPLE = SokobanLevel(
    [
        "#######",
        "#     #",
        "# $ # #",
        "# @ . #",
        "#     #",
        "#######",
    ]
)
