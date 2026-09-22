"""Rush Hour: the sliding-block traffic-jam puzzle (ThinkFun, 1996 --
one of the best-known commercial logic puzzles, and a standard planning
benchmark). A target vehicle must reach the board's right edge; other
vehicles occupy 2+ cells each, move only along their own fixed axis
(horizontal vehicles left/right, vertical ones up/down), and block each
other -- a genuinely different mechanic from Sokoban: pieces have length
and orientation, and "coordinating boxes" becomes "working out which
vehicle has to move out of the way before which other one."

Level grammar (one string per row):
    .        empty
    X        the target vehicle (must be horizontal; goal = reaches the
             right edge of its row)
    A-Z      any other vehicle -- all cells sharing a letter must form a
             single contiguous horizontal or vertical run (that run's
             orientation and length are fixed for the whole puzzle; only
             its position, stored in the state, changes)
"""
from __future__ import annotations

from typing import Iterable

Placement = tuple[str, int, int]  # (vehicle_id, anchor_row, anchor_col)
State = frozenset[Placement]


class RushHourLevel:
    def __init__(self, rows: Iterable[str]):
        rows = list(rows)
        self.height = len(rows)
        self.width = max(len(r) for r in rows)

        cells: dict[str, list[tuple[int, int]]] = {}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    cells.setdefault(ch, []).append((r, c))

        if "X" not in cells:
            raise ValueError("level has no target vehicle 'X'")

        self._orientation: dict[str, str] = {}  # 'H' or 'V'
        self._length: dict[str, int] = {}
        placements = []
        for vid, positions in cells.items():
            rowset = {p[0] for p in positions}
            colset = {p[1] for p in positions}
            if len(rowset) == 1:
                orientation, anchor, length = "H", (min(rowset), min(colset)), len(positions)
                if sorted(colset) != list(range(min(colset), min(colset) + length)):
                    raise ValueError(f"vehicle {vid!r} is not a contiguous run")
            elif len(colset) == 1:
                orientation, anchor, length = "V", (min(rowset), min(colset)), len(positions)
                if sorted(rowset) != list(range(min(rowset), min(rowset) + length)):
                    raise ValueError(f"vehicle {vid!r} is not a contiguous run")
            else:
                raise ValueError(f"vehicle {vid!r} is not a single straight run")
            if length < 2:
                raise ValueError(f"vehicle {vid!r} must occupy at least 2 cells")
            self._orientation[vid] = orientation
            self._length[vid] = length
            placements.append((vid, anchor[0], anchor[1]))

        if self._orientation["X"] != "H":
            raise ValueError("the target vehicle 'X' must be horizontal")

        self.vehicle_ids = tuple(sorted(cells))
        self.ACTIONS = tuple(f"{vid}{sign}" for vid in self.vehicle_ids for sign in "+-")
        self.initial_state: State = frozenset(placements)

    def _occupied(self, state: State) -> dict[tuple[int, int], str]:
        cells: dict[tuple[int, int], str] = {}
        for vid, row, col in state:
            for cell in self._cells_of(vid, row, col):
                cells[cell] = vid
        return cells

    def _cells_of(self, vid: str, row: int, col: int) -> list[tuple[int, int]]:
        length = self._length[vid]
        if self._orientation[vid] == "H":
            return [(row, col + i) for i in range(length)]
        return [(row + i, col) for i in range(length)]

    def _anchor(self, state: State, vid: str) -> tuple[int, int]:
        for v, row, col in state:
            if v == vid:
                return row, col
        raise KeyError(vid)

    def step(self, state: State, action: str) -> tuple[State, bool]:
        if len(action) < 2 or action[-1] not in "+-":
            return state, False
        vid, sign = action[:-1], action[-1]
        if vid not in self._orientation:
            return state, False

        row, col = self._anchor(state, vid)
        delta = 1 if sign == "+" else -1
        new_row, new_col = (row, col + delta) if self._orientation[vid] == "H" else (row + delta, col)

        new_cells = self._cells_of(vid, new_row, new_col)
        if any(not (0 <= r < self.height and 0 <= c < self.width) for r, c in new_cells):
            return state, False

        occupied = self._occupied(state)
        for cell in new_cells:
            occupant = occupied.get(cell)
            if occupant is not None and occupant != vid:
                return state, False

        new_state = frozenset((v, r, c) if v != vid else (vid, new_row, new_col) for v, r, c in state)
        return new_state, True

    def is_goal(self, state: State) -> bool:
        _, _, col = next(p for p in state if p[0] == "X")
        return col + self._length["X"] - 1 == self.width - 1

    def heuristic(self, state: State) -> int:
        """Distance from the target vehicle's front to the exit edge. 0
        at the goal. Doesn't account for blocking vehicles in the way --
        same spirit as Sokoban's Manhattan heuristic: a simple, imperfect
        estimate, not a solver in itself."""
        _, _, col = next(p for p in state if p[0] == "X")
        return (self.width - 1) - (col + self._length["X"] - 1)

    def complexity(self, state: State) -> int:
        """Number of vehicles on the board. Almost always > 1: getting
        the target out usually means moving one or more blockers out of
        its way first, in the right order -- independently-movable
        pieces whose routes can conflict, the same shape of problem as
        Sokoban's multiple boxes, so this routes to CP-SAT."""
        return len(state)

    def render(self, state: State) -> str:
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        for vid, row, col in state:
            for r, c in self._cells_of(vid, row, col):
                grid[r][c] = vid
        return "\n".join("".join(row) for row in grid)


# A small, hand-verified solvable board: B (vertical, rows 1-3, col 2)
# blocks X's row (row 2) until it slides down out of the way; A (row 3,
# cols 3-4) is an uninvolved decoy vehicle, same as real Rush Hour boards
# usually have pieces that never need to move.
LEVEL_CLASSIC = RushHourLevel(
    [
        "......",
        "..B...",
        "XXB...",
        "..BAA.",
        "......",
        "......",
    ]
)
