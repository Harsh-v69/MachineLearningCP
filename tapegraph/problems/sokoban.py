from __future__ import annotations

from collections import deque

from ..problem import Problem

DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}


class Sokoban(Problem):
    """Sokoban level (walls + goals). State = (player, sorted box tuple). Map must be enclosed by walls.

    Legend for from_grid: # wall, . goal, $ box, @ player, * box on goal, + player on goal.
    """

    def __init__(self, H, W, walls, goals):
        self.H, self.W = H, W
        self.walls = frozenset(walls)
        self.goals = frozenset(goals)
        self.free = [(r, c) for r in range(H) for c in range(W) if (r, c) not in self.walls]
        self.dead = self._dead_cells()

    @classmethod
    def from_grid(cls, grid):
        walls, goals, boxes, player = set(), set(), [], None
        rows = grid.strip("\n").split("\n")
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "#":
                    walls.add((r, c))
                if ch in ".*+":
                    goals.add((r, c))
                if ch in "$*":
                    boxes.append((r, c))
                if ch in "@+":
                    player = (r, c)
        p = cls(len(rows), max(map(len, rows)), walls, goals)
        return p, (player, tuple(sorted(boxes)))

    @classmethod
    def random_level(cls, rng, H=7, W=9, boxes=1, wall_prob=0.08):
        border = {(r, c) for r in range(H) for c in range(W) if r in (0, H - 1) or c in (0, W - 1)}
        inner = [(r, c) for r in range(1, H - 1) for c in range(1, W - 1)]
        while True:
            walls = border | {x for x in inner if rng.random() < wall_prob}
            free = [x for x in inner if x not in walls]
            if len(free) >= boxes + 1:
                rng.shuffle(free)
                return cls(H, W, walls, free[:boxes])

    def _dead_cells(self):
        """Cells from which a box can never reach any goal (walls only, other boxes ignored)."""
        alive = set(self.goals)
        q = deque(alive)
        while q:
            g = q.popleft()
            for dr, dc in DIRS.values():
                x = (g[0] - dr, g[1] - dc)  # box pushed from x to g in direction d
                pl = (x[0] - dr, x[1] - dc)  # player stands here to push
                if x in alive or x in self.walls or pl in self.walls:
                    continue
                alive.add(x)
                q.append(x)
        return frozenset(c for c in self.free if c not in alive)

    def neighbors(self, s):
        (pr, pc), boxes = s
        for a, (dr, dc) in DIRS.items():
            n = (pr + dr, pc + dc)
            if n in self.walls:
                continue
            if n in boxes:
                b = (n[0] + dr, n[1] + dc)
                if b in self.walls or b in boxes:
                    continue
                nb = tuple(sorted([x for x in boxes if x != n] + [b]))
                yield a, (n, nb), 1.0
            else:
                yield a, (n, boxes), 1.0

    def is_goal(self, s):
        return set(s[1]) == self.goals

    def h(self, s):
        return float(sum(min(abs(b[0] - g[0]) + abs(b[1] - g[1]) for g in self.goals) for b in s[1]))

    def prune(self, s):
        return any(b in self.dead for b in s[1])

    def res(self, s, a, s2):
        return 3.0 if s2[1] != s[1] else 1.0  # pushing costs more fuel than walking

    def res_bind(self, s, a, s2):
        """Binding experiment: count pushes only (walking is free), so a longer walk-heavy route can save resource."""
        return 1.0 if s2[1] != s[1] else 0.0

    def _reverse_neighbors(self, s):
        (pr, pc), boxes = s
        for dr, dc in DIRS.values():
            n = (pr + dr, pc + dc)
            if n in self.walls or n in boxes:
                continue
            yield (n, boxes)
            back = (pr - dr, pc - dc)  # a box behind the player can be pulled into the player's cell
            if back in boxes:
                yield (n, tuple(sorted([x for x in boxes if x != back] + [(pr, pc)])))

    def random_start(self, rng, depth):
        spots = [x for x in self.free if x not in self.goals]
        s = (rng.choice(spots), tuple(sorted(self.goals)))
        for _ in range(depth):
            nbrs = list(self._reverse_neighbors(s))
            if not nbrs:
                break
            s = rng.choice(nbrs)
        return s
