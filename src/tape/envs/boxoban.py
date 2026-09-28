"""Boxoban: DeepMind's public Sokoban level set (github.com/google-deepmind/boxoban-levels).

Files hold 1000 levels each, 10x10, 4 boxes, one per block:

    ; 17
    ##########
    #  ...

The character grammar is the same as ours, so a block parses straight into
a `SokobanLevel`. This is a standard external benchmark, unlike the levels
we wrote by hand.
"""
from __future__ import annotations

from pathlib import Path

from tape.envs.sokoban import SokobanLevel

DEFAULT_FILE = Path(__file__).resolve().parents[3] / "data" / "boxoban" / "medium_valid_000.txt"


def parse_boxoban(text: str) -> list[SokobanLevel]:
    levels, rows = [], []
    for line in text.splitlines() + [";"]:
        if line.startswith(";"):
            if rows:
                levels.append(SokobanLevel(rows))
            rows = []
        elif line.strip():
            rows.append(line)
    return levels


def load_boxoban(path: str | Path = DEFAULT_FILE, limit: int | None = None) -> list[SokobanLevel]:
    levels = parse_boxoban(Path(path).read_text(encoding="utf-8"))
    return levels[:limit] if limit else levels
