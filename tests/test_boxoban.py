import random
from pathlib import Path

import pytest

from tapegraph.problems.boxoban import boxoban_level, load_boxoban_file
from tapegraph.problems.sokoban import Sokoban
from tapegraph.solvers import astar

SAMPLE = Path(__file__).parent / "data" / "boxoban_sample.txt"


def test_boxoban_level_shape():
    p = boxoban_level(random.Random(0))
    assert (p.H, p.W) == (10, 10) and len(p.goals) == 4


def test_boxoban_short_reverse_play_is_solvable_by_astar():
    for seed in range(4):
        rng = random.Random(seed)
        p = boxoban_level(rng)
        s = p.random_start(rng, 12)
        r = astar.solve(p, s, max_nodes=500_000)
        assert r.status == "ok" and r.cost <= 12  # reverse play of 12 steps => solution of length <= 12


# ---- load_boxoban_file -----------------------------------------------------------------------------------------

def test_load_sample_file_gives_three_solvable_levels():
    levels = load_boxoban_file(SAMPLE)
    assert len(levels) == 3
    boxes_per_level = []
    for p, s in levels:
        assert isinstance(p, Sokoban) and (p.H, p.W) == (10, 10)
        assert len(s[1]) == len(p.goals) and s[0] not in p.walls
        r = astar.solve(p, s, max_nodes=200_000)
        assert r.status == "ok" and 0 < r.cost <= 30
        boxes_per_level.append(len(s[1]))
    assert boxes_per_level == [1, 2, 2]
    p0, s0 = levels[0]
    assert astar.solve(p0, s0).cost == 1  # one push up
    p1, s1 = levels[1]
    assert (2, 6) in p1.goals and (2, 6) in s1[1]  # '*' = box on goal
    p2, s2 = levels[2]
    assert (6, 6) in p2.goals and s2[0] == (6, 6)  # '+' = player on goal


def _sample_levels():
    return [part.rstrip("\n").split("\n")[1:] for part in SAMPLE.read_text().split("; ")[1:]]


def _write(tmp_path, *levels, header=lambda i: f"; {i}", sep="\n\n"):
    path = tmp_path / "f.txt"
    path.write_text(sep.join(header(i) + "\n" + "\n".join(rows) for i, rows in enumerate(levels)) + "\n")
    return path


def _mutate(rows, r, c, ch):
    rows = list(rows)
    rows[r] = rows[r][:c] + ch + rows[r][c + 1:]
    return rows


def test_blank_lines_crlf_and_bare_semicolon_headers_are_accepted(tmp_path):
    a = _sample_levels()[0]
    path = tmp_path / "f.txt"
    path.write_bytes((";0\r\n" + "\r\n".join(a) + "\r\n\r\n\r\n; 1\r\n" + "\r\n".join(a) + "\r\n").encode())
    assert len(load_boxoban_file(path)) == 2


@pytest.mark.parametrize("name,make,msg", [
    ("no player", lambda L: _mutate(L, 4, 4, " "), "exactly one player"),
    ("two players", lambda L: _mutate(L, 1, 1, "@"), "exactly one player"),
    ("more boxes than goals", lambda L: _mutate(L, 1, 1, "$"), "boxes"),
    ("more goals than boxes", lambda L: _mutate(L, 1, 1, "."), "boxes"),
    ("ragged row", lambda L: _mutate(L, 5, 0, "#")[:5] + [L[5] + " "] + L[6:], "rectangular"),
    ("hole in the border", lambda L: _mutate(L, 0, 4, " "), "enclosed"),
    ("unknown character", lambda L: _mutate(L, 1, 1, "x"), "unknown character"),
    ("blank row inside", lambda L: L[:5] + [""] + L[6:], "rectangular"),
    ("empty level", lambda L: [], "empty"),
])
def test_malformed_level_is_rejected_with_its_index(tmp_path, name, make, msg):
    good = _sample_levels()
    # level index 7 (second one) is the broken one; the header index, not the position, is reported
    path = _write(tmp_path, good[0], make(good[0]), header=lambda i: f"; {[3, 7][i]}")
    with pytest.raises(ValueError, match=rf"level 7.*{msg}"):
        load_boxoban_file(path)


def test_file_level_errors(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("\n\n")
    with pytest.raises(ValueError, match="no levels"):
        load_boxoban_file(p)
    p.write_text("##########\n; 0\n" + "\n".join(_sample_levels()[0]) + "\n")
    with pytest.raises(ValueError, match="before the first"):
        load_boxoban_file(p)


def test_load_file_with_utf8_bom(tmp_path):
    f = tmp_path / "bom.txt"
    f.write_bytes(b"\xef\xbb\xbf" + SAMPLE.read_bytes())  # e.g. a file saved by Windows Notepad
    assert len(load_boxoban_file(f)) == 3
