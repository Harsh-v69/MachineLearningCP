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
    for d, b in mp.PENDING:  # pending exactly while the file is absent
        assert (f"`docs/data/{d}/agents_{b}.csv`" in text) != (ROOT / "docs" / "data" / d / f"agents_{b}.csv").is_file()
    assert text.count("_pending: data not yet available") <= 1


def _layout(text):
    """Data files listed in the paper's section 9 layout table."""
    return set(re.findall(r"^\| `docs/data/([^/]+)/` \| (.*) \|$", text, re.M))


def test_committed_paper_is_a_fresh_build(committed):
    """docs/paper.md must equal a fresh build from the committed data. While the agents data is still landing the
    controller regenerates the paper after each copy into docs/data; until then the committed paper lists a different
    data set in its section 9 layout table and this check is skipped (it is not skipped once the sets agree)."""
    on_disk = (ROOT / "docs" / "paper.md").read_text(encoding="utf-8").replace("\r\n", "\n")  # autocrlf checkouts
    fresh = mp.build_paper(interpretation=mp.read_interpretation(ROOT / "docs" / "paper.md"))
    if _layout(on_disk) != _layout(fresh):
        pytest.skip("docs/paper.md predates the current docs/data set (agents data landing; regenerate with make_paper.py)")
    assert on_disk == fresh


@pytest.fixture
def toy(tmp_path):
    d = tmp_path / "data"
    s = lambda T, solver, st, nodes, sec: {"bench": "toy", "T": T, "solver": solver, "status": st, "ok": int(st == "ok"),
                                           "cost_ratio": 1.0 if st == "ok" else "", "nodes": nodes, "seconds": sec}
    write(d / "main" / "solvers_toy.csv", [
        s(3, "astar", "ok", 10, 0.01), s(3, "ilp", "ok", 20, 0.5),
        s(3, "astar", "ok", 12, 0.02), s(3, "ilp", "timeout", 99, 10.0),
        s(5, "astar", "ok", 30, 0.04), s(5, "ilp", "ok", 50, 0.08)])

    def b(T, level, solver, st, cost, sec, c, r_opt):
        return {"bench": "toy", "T": T, "level": level, "solver": solver, "status": st, "ok": int(st == "ok"),
                "r_opt": r_opt, "cost": cost if st == "ok" else "", "nodes": 5, "seconds": sec, "c_slack": c}
    skip = lambda T, c: {"bench": "toy", "T": T, "level": "-", "solver": "skipped", "status": "no_tradeoff", "ok": 0, "c_slack": c}
    write(d / "bindx" / "constrained_toy.csv", [
        skip(3, 4),
        b(3, "bind", "astar", "ok", 5, 0.003, 4, 2), b(3, "bind", "ilp", "ok", 5, 0.3, 4, 2),
        b(3, "tight", "astar", "ok", 6, 0.003, 4, 2), b(3, "tight", "ilp", "ok", 7, 0.03, 4, 2),  # cost DISagreement
        b(5, "bind", "astar", "ok", 6, 0.005, 4, 3), b(5, "bind", "ilp", "ok", 6, 0.5, 4, 3),
        b(5, "tight", "astar", "ok", 7, 0.005, 4, 3), b(5, "tight", "ilp", "timeout", 0, 0.001, 4, 3),
        skip(5, 4)])
    write(d / "bindy" / "constrained_toy.csv", [  # same 4 instances at c_slack 2; the T*=5 one has no trade-off here
        skip(3, 2), b(3, "bind", "astar", "ok", 5, 0.002, 2, 2), b(3, "bind", "ilp", "ok", 5, 0.001, 2, 2),
        skip(5, 2), skip(5, 2)])
    write(d / "main" / "constrained_toy.csv", [  # frac design (no level column)
        {"bench": "toy", "T": 3, "solver": "skipped", "status": "infeasible", "ok": 0, "R": 2},
        {"bench": "toy", "T": 3, "solver": "astar", "status": "ok", "ok": 1, "R": 3, "cost": 4.0, "agrees_with_astar": 1},
        {"bench": "toy", "T": 3, "solver": "ilp", "status": "ok", "ok": 1, "R": 3, "cost": 4.0, "agrees_with_astar": 1},
        {"bench": "toy", "T": 5, "solver": "astar", "status": "node_limit", "ok": 0, "R": 4},
        {"bench": "toy", "T": 5, "solver": "ilp", "status": "too_large", "ok": 0, "R": 4}])

    def agents(path, bench, ep, insts):
        rows = []
        for T, seed, succ in insts:
            for m, p in succ.items():
                rows.append({"bench": bench, "T": T, "method": m, "success": p, "mean_steps": 3, "solves": 1,
                             "seconds": 0.01, "episodes": ep, "inst_seed": seed})
        write(path, rows)
    # main (10 episodes) is superseded by agents_ep300 (30 episodes) on `toy`: its values must not appear anywhere
    agents(d / "main" / "agents_toy.csv", "toy", 10, [(3, 11, {"react": 0.1, "tape": 0.1, "ours_astar": 0.1}),
                                                      (5, 22, {"react": 0.1, "tape": 0.1, "ours_astar": 0.1})])
    agents(d / "agents_ep300" / "agents_toy.csv", "toy", 30, [(3, 11, {"react": 0.5, "tape": 0.8, "ours_astar": 1.0}),
                                                              (5, 22, {"react": 0.2, "tape": 0.7, "ours_astar": 0.6})])
    agents(d / "new_agents" / "agents_toy2.csv", "toy2", 10, [(3, 11, {"react": 0.1, "tape": 0.8, "ours_astar": 0.9}),
                                                              (5, 22, {"react": 0.1, "tape": 0.7, "ours_astar": 0.8})])
    (tmp_path / "figs").mkdir()
    return d, tmp_path / "figs"


def lines(text):
    return set(text.splitlines())


def test_toy_numbers_equal_hand_computed_values(toy, tmp_path):
    d, figs = toy
    text = mp.build_paper(d, figs, tmp_path)
    claim_check(text)
    L = lines(text)
    # solvers: ILP vs A* paired over the 2 instances both solved: per-row ratios 50 and 2 (median 26), ratio of mean
    # seconds 0.58 / 0.05 = 11.6; nodes ratios 2 and 5/3; 1 ILP failure
    assert "| main | toy | ilp | 2 | 2 | 1 | 26x | 2.00x to 50x | 12x | 0 | 1.83 |" in L
    assert "| toy | ilp | 3 | 2 | 1 |" in L  # failure counts: n, ok, timeout
    assert "| main | toy | ilp | 3 | 2 | 1 timeout | 1.0000 | 35 | 0.29 |" in L
    # bind c_slack 4: per-row ratios 100, 10, 100 (median 100x) vs ratio of means (0.83/3)/(0.011/3) = 75.5; one cost
    # disagreement among the 3 both-ok rows; 1 fast ILP failure; c_slack 2: the ILP is faster on its only row
    assert ("| toy | 4 | bindx | 4 | 2 | 2 no_tradeoff | 4 | 4 / 4 | 3 / 4 | 1 timeout | 3 | 2 | 100x | 10x to 100x | 75x "
            "| 0 | 1 | +1: 1, +2: 2, +3: 1 |") in L
    assert ("| toy | 2 | bindy | 4 | 1 | 3 no_tradeoff | 1 | 1 / 1 | 1 / 1 | none | 1 | 1 | 0.50x | 0.50x to 0.50x | 0.50x "
            "| 1 | 0 | +2: 1 |") in L
    assert "| `toy` | ILP 1/1, 1 inst., 0.50x | ILP 3/4, 2 inst., 100x |" in L
    bind_text = ("the ILP solved 4 of 5 (instance, level, c_slack) rows (A* 5 of 5); on the 4 rows where both solved "
                 "(2 distinct instances; the c_slack runs of a benchmark re-use the same instances) it returned the same "
                 "cost as A* on 3 and was faster on 1")
    assert f"- Over all benchmarks and c_slack values: {bind_text}" in text
    assert "- Distinct instances: 4 over all bind runs, 2 of them with a trade-off in at least one c_slack run." in text
    assert ("- Skipped: 5 no_tradeoff instance-runs; `no_tradeoff` covers 3 distinct instances (2 of them `no_tradeoff` "
            "in every c_slack run of their benchmark).") in text
    assert "Not verified" not in text
    assert "The ILP beat A* only on some rows" in text
    # frac, with the A* failure column
    assert "| main | 0.9 | toy | 3 | 1 infeasible | 1 / 2 | 1 node_limit | 1 / 2 | 1 too_large | 1 | 1 / 1 |" in L
    # agents: agents_ep300 supersedes main on toy; Wilson intervals computed by hand
    assert "`main` on `toy` (10 episodes; replaced by `agents_ep300`, 30 episodes)" in text
    assert "| `agents_ep300` | `toy` | ours_astar | 2 | 30 | 48 / 60 | 0.800 | [0.682, 0.882] |" in L
    assert "| `agents_ep300` | `toy` | react (simulated) | 2 | 30 | 21 / 60 | 0.350 | [0.242, 0.476] |" in L
    assert "| `agents_ep300` | `toy` | tape (simulated) | 2 | 30 | 45 / 60 | 0.750 | [0.628, 0.842] |" in L
    assert "| `new_agents` | `toy2` | ours_astar | 2 | 10 | 17 / 20 | 0.850 | [0.640, 0.948] |" in L
    assert not any(l.startswith("| `main` | `toy` |") for l in L)
    assert "- `toy` (`agents_ep300`): ours_astar minus react (simulated): +0.4500 [" in text
    assert "identical success on 0 of 2 instances (tape higher on 1, lower on 1)" in text
    assert "identical success on 0 of 4 instances over 2 benchmarks" in text
    # abstract: denominators of both solvers, distinct instances, benchmarks (not datasets), the tape_excl clause
    abstract = text.split("## Abstract\n")[1].split("## 1 ")[0]
    assert ("the ILP solved 2 of 3 unconstrained instances (A* 3 of 3) and was faster than A* on 0 of the 2 where both "
            "solved") in abstract
    fast = "On 1 (instance, level, c_slack) rows the ILP returned before A* but with a failure status; a fast failure is not a win."
    assert bind_text in abstract and fast in abstract
    assert ("exceeds a simulated ReAct by 0.450 to 0.750 in mean per-instance success across 2 benchmarks, and differs "
            "from a simulated TAPE by 0.050 to 0.100; the bootstrap interval of that difference contains 0 on 1 of 2 "
            "benchmarks; it excludes 0 with ours_astar higher on 1 (by at most 0.100) and with ours_astar lower on 0.") in abstract
    conclusion = text.split("## 10 Conclusion\n")[1]
    assert bind_text in conclusion and fast in conclusion
    assert "unconstrained instances (A* 3 of 3)" in conclusion
    # pending: exactly one line, naming every planned file that is absent
    assert text.count("_pending: data not yet available") == 1
    for (dd, bb) in mp.PENDING:
        assert f"/{dd}/agents_{bb}.csv` (" in text
    assert "](" not in text.split("## 8 ")[0].split("## 7 Results")[1]  # no figure files exist: no links in results


def test_same_instances_key():
    a = [{"T": 3, "r_opt": 5, "skip": None}, {"T": 5, "r_opt": None, "skip": "no_tradeoff"}]
    assert mp.same_instances([a, [dict(a[0]), {"T": 5, "r_opt": 7, "skip": None}]])
    assert not mp.same_instances([a, [{"T": 3, "r_opt": 6, "skip": None}, a[1]]])  # r_opt differs
    assert not mp.same_instances([a, a[:1]])  # different number of instances
    assert not mp.same_instances([a, [a[1], a[0]]])  # T* sequence differs


def test_missing_agent_directories_are_tolerated(tmp_path):
    d = tmp_path / "data"
    write(d / "main" / "solvers_toy.csv", [{"bench": "toy", "T": 3, "solver": "astar", "status": "ok", "ok": 1,
                                            "cost_ratio": 1.0, "nodes": 4, "seconds": 0.001}])
    text = mp.build_paper(d, tmp_path / "nofigs", tmp_path)
    claim_check(text)
    assert "_No agents data._" in text and "_No `bind` data._" in text
    assert text.count("_pending: data not yet available") == 1


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


@pytest.mark.parametrize("body", [
    f"{mp.MARK}\nhand text\n",  # end marker missing
    f"{mp.MARK}\nhand text\n{mp.END}\n{mp.MARK}\n",  # two start markers
    f"{mp.END}\nhand text\n{mp.MARK}\n",  # wrong order
    f"hand text\n{mp.END}\n",  # end without start
])
def test_broken_interpretation_markers_fail_loudly(tmp_path, body):
    p = tmp_path / "paper.md"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="INTERPRETATION-7.4"):
        mp.read_interpretation(p)
    with pytest.raises(ValueError):
        mp.main(["--data", str(tmp_path / "none"), "--figures", str(tmp_path), "--out", str(p)])
    assert p.read_text(encoding="utf-8") == body  # never overwritten
    assert mp.read_interpretation(tmp_path / "absent.md") == ""
