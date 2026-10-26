import csv
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("make_paper", ROOT / "scripts" / "make_paper.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)
LINK = re.compile(r"\]\(([^)\s]+)\)")


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def claim_check(text):
    for bad in ("TODO", "TBD", "XXX"):
        assert bad not in text
    assert not re.search(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text), "unresolved template field"
    assert text.count(mp.MARK) == 1 and text.count(mp.END) == 1


@pytest.fixture(scope="module")
def committed():
    return mp.build_paper(), mp.build_paper()


def test_committed_data_builds_byte_identical(committed, tmp_path):
    a, b = committed
    for name, text in (("a.md", a), ("b.md", b)):
        with open(tmp_path / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    assert (tmp_path / "a.md").read_bytes() == (tmp_path / "b.md").read_bytes()


def test_committed_links_point_at_existing_files(committed):
    links = LINK.findall(committed[0])
    assert any(l.startswith("figures/") for l in links)
    for l in links:
        assert (ROOT / "docs" / l).is_file(), l


def test_committed_claim_check_and_pending_lines(committed):
    text = committed[0]
    claim_check(text)
    assert "simulated" in text and "no results on real Boxoban levels" in text
    for d in mp.PENDING:  # pending exactly while the directory is absent
        assert (f"pending: data not yet available (`docs/data/{d}/`" in text) != (ROOT / "docs" / "data" / d).is_dir()


@pytest.fixture
def toy(tmp_path):
    d = tmp_path / "data"
    s = lambda T, solver, st, nodes, sec: {"bench": "toy", "T": T, "solver": solver, "status": st, "ok": int(st == "ok"),
                                           "cost_ratio": 1.0 if st == "ok" else "", "nodes": nodes, "seconds": sec}
    write(d / "main" / "solvers_toy.csv", [
        s(3, "astar", "ok", 10, 0.01), s(3, "ilp", "ok", 20, 0.5),
        s(3, "astar", "ok", 12, 0.02), s(3, "ilp", "timeout", 99, 10.0),
        s(5, "astar", "ok", 30, 0.04), s(5, "ilp", "ok", 50, 0.08)])

    def b(T, level, solver, st, cost, sec, c):
        return {"bench": "toy", "T": T, "level": level, "solver": solver, "status": st, "ok": int(st == "ok"),
                "cost": cost if st == "ok" else "", "nodes": 5, "seconds": sec, "c_slack": c}
    skip = lambda T, c: {"bench": "toy", "T": T, "level": "-", "solver": "skipped", "status": "no_tradeoff", "ok": 0, "c_slack": c}
    write(d / "bindx" / "constrained_toy.csv", [
        skip(3, 4),
        b(3, "bind", "astar", "ok", 5, 0.003, 4), b(3, "bind", "ilp", "ok", 5, 0.3, 4),
        b(3, "tight", "astar", "ok", 6, 0.003, 4), b(3, "tight", "ilp", "ok", 6, 0.03, 4),
        b(5, "bind", "astar", "ok", 6, 0.005, 4), b(5, "bind", "ilp", "ok", 6, 0.5, 4),
        b(5, "tight", "astar", "ok", 7, 0.005, 4), b(5, "tight", "ilp", "timeout", 0, 10.0, 4),
        skip(5, 4)])
    write(d / "bindy" / "constrained_toy.csv", [
        skip(3, 2), b(3, "bind", "astar", "ok", 5, 0.002, 2), b(3, "bind", "ilp", "ok", 5, 0.001, 2)])
    write(d / "main" / "constrained_toy.csv", [  # frac design (no level column)
        {"bench": "toy", "T": 3, "solver": "skipped", "status": "infeasible", "ok": 0, "R": 2},
        {"bench": "toy", "T": 3, "solver": "astar", "status": "ok", "ok": 1, "R": 3, "cost": 4.0, "agrees_with_astar": 1},
        {"bench": "toy", "T": 3, "solver": "ilp", "status": "ok", "ok": 1, "R": 3, "cost": 4.0, "agrees_with_astar": 1}])
    ag = []
    for T, seed, succ in ((3, 11, {"react": 0.5, "tape": 0.8, "ours_astar": 1.0}), (5, 22, {"react": 0.2, "tape": 0.8, "ours_astar": 0.6})):
        for m, p in succ.items():
            ag.append({"bench": "toy", "T": T, "method": m, "success": p, "mean_steps": 3, "solves": 1, "seconds": 0.01,
                       "episodes": 10, "inst_seed": seed})
    write(d / "main" / "agents_toy.csv", ag)
    (tmp_path / "figs").mkdir()
    return d, tmp_path / "figs"


def lines(text):
    return set(text.splitlines())


def test_toy_numbers_equal_hand_computed_values(toy, tmp_path):
    d, figs = toy
    text = mp.build_paper(d, figs, tmp_path)
    claim_check(text)
    L = lines(text)
    # solvers: ILP vs A* paired over the 2 instances both solved (ratios 50 and 2; nodes 2 and 5/3), 1 ILP failure
    assert "| main | toy | ilp | 2 | 2 | 1 | 26x | 2.00x to 50x | 0 | 1.83 |" in L
    assert "| toy | ilp | 3 | 2 | 1 |" in L  # failure counts: n, ok, timeout
    assert "| main | toy | ilp | 3 | 2 | 1 timeout | 1.0000 | 35 | 0.29 |" in L
    assert "The ILP was faster than A* on 0 of 2 instances where both solved" in text
    # bind, c_slack 4 and 2 (the c_slack 2 row has the ILP faster on its only row)
    assert ("| toy | 4 | bindx | 4 | 2 | 2 no_tradeoff | 4 | 4 / 4 | 3 / 4 | 1 timeout | 3 | 3 | 100x | 10x to 100x | 0 | 0 "
            "| +1: 1, +2: 2, +3: 1 |") in L
    assert "| toy | 2 | bindy | 2 | 1 | 1 no_tradeoff | 1 | 1 / 1 | 1 / 1 | none | 1 | 1 | 0.50x | 0.50x to 0.50x | 1 | 0 | +2: 1 |" in L
    assert "| `toy` | ILP 1/1, 1 inst., 0.50x | ILP 3/4, 2 inst., 100x |" in L
    assert "4 rows where both solved; the ILP's cost equals A*'s on 4 of them; the ILP was faster on 1 of them" in text
    assert "The ILP beat A* only on some rows" in text
    # frac
    assert "| main | 0.9 | toy | 2 | 1 infeasible | 1 / 1 | 1 / 1 | none | 1 | 1 / 1 |" in L
    # agents: ours_astar pooled 16 / 20, Wilson [0.584, 0.919] computed by hand; paired differences by instance
    assert "| `main` | `toy` | ours_astar | 2 | 10 | 16 / 20 | 0.800 | [0.584, 0.919] |" in L
    assert "| `main` | `toy` | react (simulated) | 2 | 10 | 7 / 20 | 0.350 | [0.181, 0.567] |" in L
    assert "- `toy` (`main`): ours_astar minus react (simulated): +0.4500 [" in text
    assert "over 2 instances" in text
    assert "identical success on 0 of 2 instances (tape higher on 1, lower on 1)" in text
    for p in mp.PENDING:
        assert f"pending: data not yet available (`" in text and f"/{p}/`" in text
    assert "](" not in text.split("## 8 ")[0].split("## 7 Results")[1]  # no figure files exist: no links in results


def test_missing_agent_directories_are_tolerated(tmp_path):
    d = tmp_path / "data"
    write(d / "main" / "solvers_toy.csv", [{"bench": "toy", "T": 3, "solver": "astar", "status": "ok", "ok": 1,
                                            "cost_ratio": 1.0, "nodes": 4, "seconds": 0.001}])
    text = mp.build_paper(d, tmp_path / "nofigs", tmp_path)
    claim_check(text)
    assert "_No agents data._" in text and "_No `bind` data._" in text
    assert text.count("pending: data not yet available") == 2 * len(mp.PENDING)


def test_interpretation_block_survives_regeneration(toy, tmp_path):
    d, figs = toy
    out = tmp_path / "out" / "paper.md"
    argv = ["--data", str(d), "--figures", str(figs), "--out", str(out)]
    mp.main(argv)
    first = out.read_bytes()
    mp.main(argv)
    assert out.read_bytes() == first
    text = out.read_text(encoding="utf-8").replace(f"{mp.MARK}\n{mp.END}", f"{mp.MARK}\nThe agents agree.\n{mp.END}")
    out.write_text(text, encoding="utf-8")
    mp.main(argv)
    assert f"{mp.MARK}\nThe agents agree.\n{mp.END}" in out.read_text(encoding="utf-8")
