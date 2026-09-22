"""River crossing (the missionaries-and-cannibals family of classic AI
planning puzzles): N missionary/cannibal pairs must cross a river using a
boat that holds at most `capacity` people. On EITHER bank, cannibals may
never outnumber missionaries while any missionaries are present there --
otherwise the missionaries get eaten.

This is a deliberately different mechanic from Sokoban: there is no
pushing, no walls, and the "board" is just two counts and a boat side.
It is also a clean second example of Phase 2's validator pattern: moving
people across the river is always physically legal (you can always ferry
however many the boat holds, if that many are present) -- the fatal
"outnumbered" configuration is a domain rule the raw step function does
not and should not enforce itself, exactly like Sokoban's corner
deadlock. `step()` allows it; `RiverSafetyValidator` is what catches it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiverState:
    missionaries_left: int
    cannibals_left: int
    boat_left: bool  # True: boat (and the "current" bank for a crossing) is on the left


# action code -> (missionaries moved, cannibals moved)
_MOVES: dict[str, tuple[int, int]] = {
    "1M": (1, 0),
    "1C": (0, 1),
    "2M": (2, 0),
    "2C": (0, 2),
    "1M1C": (1, 1),
}


class RiverCrossingLevel:
    def __init__(self, n_pairs: int = 3, capacity: int = 2):
        if capacity != 2:
            raise ValueError("only the classic 2-seat boat is implemented")
        self.n = n_pairs
        self.capacity = capacity
        self.ACTIONS = tuple(_MOVES)
        self.initial_state = RiverState(
            missionaries_left=n_pairs, cannibals_left=n_pairs, boat_left=True
        )

    def step(self, state: RiverState, action: str) -> tuple[RiverState, bool]:
        """Physical legality only: enough people on the boat's current
        bank to make this trip. Does NOT check the safety rule -- that is
        RiverSafetyValidator's job (Phase 2), on purpose."""
        if action not in _MOVES:
            return state, False
        dm, dc = _MOVES[action]
        if state.boat_left:
            avail_m, avail_c = state.missionaries_left, state.cannibals_left
        else:
            avail_m = self.n - state.missionaries_left
            avail_c = self.n - state.cannibals_left
        if dm > avail_m or dc > avail_c:
            return state, False

        sign = -1 if state.boat_left else 1
        new_state = RiverState(
            missionaries_left=state.missionaries_left + sign * dm,
            cannibals_left=state.cannibals_left + sign * dc,
            boat_left=not state.boat_left,
        )
        return new_state, True

    def is_goal(self, state: RiverState) -> bool:
        return state.missionaries_left == 0 and state.cannibals_left == 0

    def heuristic(self, state: RiverState) -> int:
        """People still stranded on the left bank. Not a tight bound (a
        full boatload moves 2 at a time, a solo trip only 1), but the same
        kind of simple, imperfect distance estimate Sokoban's heuristic
        is -- good enough to bias search and to price regression."""
        return state.missionaries_left + state.cannibals_left

    def complexity(self, state: RiverState) -> int:
        """Only one resource ever moves independently -- the boat. The
        people don't route themselves; every crossing is a single
        sequential decision, unlike Sokoban's independently-pushable
        boxes. So this is always a pure shortest-path problem."""
        return 1

    def render(self, state: RiverState) -> str:
        right_m = self.n - state.missionaries_left
        right_c = self.n - state.cannibals_left
        boat = "boat: LEFT " if state.boat_left else "boat: RIGHT"
        return (
            f"left:  {state.missionaries_left}M {state.cannibals_left}C   "
            f"{boat}   "
            f"right: {right_m}M {right_c}C"
        )


LEVEL_CLASSIC = RiverCrossingLevel(n_pairs=3, capacity=2)
