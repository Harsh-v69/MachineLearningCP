from pathlib import Path

from .sokoban import Sokoban


# Boxoban-style: 10x10 room, 4 boxes. Generated locally; real levels come from `load_boxoban_file`.
def boxoban_level(rng):
    return Sokoban.random_level(rng, H=10, W=10, boxes=4, wall_prob=0.05)


def _parse_level(rows):
    """Validate one level's rows (list of str) and return (Sokoban, start). Raises ValueError on a malformed level."""
    if not rows:
        raise ValueError("empty level")
    if len({len(r) for r in rows}) != 1:
        raise ValueError(f"rows are not rectangular (lengths {sorted({len(r) for r in rows})})")
    bad = sorted({ch for r in rows for ch in r} - set("# .$@*+"))
    if bad:
        raise ValueError(f"unknown character {bad[0]!r}")
    cells = [(r, c, ch) for r, row in enumerate(rows) for c, ch in enumerate(row)]
    players = [(r, c) for r, c, ch in cells if ch in "@+"]
    boxes = sum(ch in "$*" for _, _, ch in cells)
    goals = sum(ch in ".*+" for _, _, ch in cells)
    if len(players) != 1:
        raise ValueError(f"expected exactly one player, found {len(players)}")
    if boxes != goals:
        raise ValueError(f"{boxes} boxes but {goals} goals")
    H, W = len(rows), len(rows[0])
    seen, stack = {players[0]}, [players[0]]  # flood fill from the player: leaving the grid means not enclosed
    while stack:
        r, c = stack.pop()
        if r in (0, H - 1) or c in (0, W - 1):
            raise ValueError("not enclosed by walls (the player can reach the grid border)")
        for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if rows[n[0]][n[1]] != "#" and n not in seen:
                seen.add(n)
                stack.append(n)
    return Sokoban.from_grid("\n".join(rows))


def load_boxoban_file(path):
    """DeepMind Boxoban text format: a line starting with ';' (e.g. '; 12') opens a level, followed by its grid rows
    (# wall, space floor, . goal, $ box, @ player, * box on goal, + player on goal); blank lines after a grid are ignored.
    Returns [(Sokoban, start)]. Any malformed level raises ValueError naming its header index; nothing is skipped silently."""
    levels, label, rows = [], None, None
    lines = Path(path).read_text().splitlines()

    def close():
        while rows and not rows[-1].strip():
            rows.pop()
        try:
            levels.append(_parse_level(rows))
        except ValueError as e:
            raise ValueError(f"level {label}: {e}") from None

    for no, line in enumerate(lines, 1):
        if line.startswith(";"):
            if rows is not None:
                close()
            label, rows = line[1:].strip() or f"@line{no}", []
        elif rows is not None:
            rows.append(line)
        elif line.strip():
            raise ValueError(f"line {no}: text before the first ';' level header")
    if rows is not None:
        close()
    if not levels:
        raise ValueError("no levels found (expected lines starting with ';')")
    return levels
