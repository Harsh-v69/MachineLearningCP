import csv
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tapegraph.stats import wilson_interval

spec = importlib.util.spec_from_file_location("make_figures", Path(__file__).resolve().parent.parent / "scripts" / "make_figures.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
NS = "{http://www.w3.org/2000/svg}"


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def agents_rows(bench="toy", with_episodes=True):
    rows = []
    for seed in (1, 2):
        for T in (3, 5):
            for m, p in (("react", 0.5), ("tape", 0.8), ("ours_astar", 1.0)):
                r = {"bench": bench, "T": T, "method": m, "success": p if seed == 1 else round(p * 0.4, 5), "mean_steps": 4, "solves": 0, "seconds": 0.01}
                if with_episodes:
                    r.update(episodes=10, inst_seed=seed * 100 + T)  # one instance per (seed, T)
                rows.append(r)
    return rows


def solver_rows():
    rows = []
    for T in (3, 5):
        for inst in (0, 1):
            for s in ("bfs", "astar", "ilp"):
                st = "ok"
                if T == 5 and s == "bfs":
                    st = "node_limit"
                if T == 5 and s == "ilp":
                    st = "timeout" if inst == 0 else "too_large"
                rows.append({"bench": "toy", "T": T, "solver": s, "status": st, "ok": int(st == "ok"), "cost_ratio": 1.0,
                             "nodes": 10 * T if st == "ok" else 99, "seconds": 0.01 * T if st == "ok" else 5.0})
    return rows


def bind_rows(c, fail_ilp=1):
    rows = []
    for T in (3, 5):
        for level in ("bind", "tight"):
            rows.append({"bench": "toy", "T": T, "level": level, "solver": "astar", "status": "ok", "ok": 1, "seconds": 0.001 * T, "c_slack": c})
            bad = fail_ilp and T == 5 and level == "tight"
            rows.append({"bench": "toy", "T": T, "level": level, "solver": "ilp", "status": "timeout" if bad else "ok", "ok": int(not bad),
                         "seconds": 10.0 if bad else 0.1 * T, "c_slack": c})
        rows.append({"bench": "toy", "T": T, "level": "-", "solver": "skipped", "status": "no_tradeoff", "ok": 0, "c_slack": c})
    return rows


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "data"
    write(d / "main" / "agents_toy.csv", agents_rows())
    write(d / "main" / "solvers_toy.csv", solver_rows())
    write(d / "main" / "constrained_toy.csv", [{"bench": "toy", "T": 3, "solver": "astar", "status": "ok", "ok": 1, "R": 3}])  # frac design: ignored
    b4 = bind_rows(4)
    write(d / "bindx" / "constrained_toy.csv", b4)
    write(d / "bindy" / "constrained_toy.csv", bind_rows(2, fail_ilp=0))
    write(d / "old" / "agents_other.csv", agents_rows("other", with_episodes=False))  # bench without documented episodes
    return d


def svg(path):
    return ET.parse(path).getroot()


def cls(root, c):
    return [e for e in root.iter() if e.get("class") == c]


def test_all_families_written_and_valid(data, tmp_path):
    out = tmp_path / "out"
    names = mf.make_figures(data, out)
    assert names == sorted(["agents_toy.svg", "solvers_nodes_toy.svg", "solvers_seconds_toy.svg", "ilp_rate_toy.svg",
                            "bind_scatter_toy_c2.svg", "bind_scatter_toy_c4.svg", "bind_cslack_toy.svg"])
    for n in names:
        r = svg(out / n)
        assert r.tag == NS + "svg" and r.find(NS + "title").text and not cls(r, "nodata")


def test_agents_wilson_band_matches_stats(data):
    rows = mf.load(data)["agents"][0][2]
    series, n, eps = mf.agent_series(rows)
    assert (n, eps) == (4, [10]) and [s["name"] for s in series] == ["react", "tape", "ours_astar"]
    react = series[0]
    k = 5 + 2  # T=3: two instances of 10 episodes with success 0.5 and 0.2, pooled by the report's rule
    assert react["y"][0] == k / 20 and (react["lo"][0], react["hi"][0]) == wilson_interval(k, 20)


def test_agents_figure_has_band_per_method(data, tmp_path):
    mf.make_figures(data, tmp_path)
    r = svg(tmp_path / "agents_toy.svg")
    assert len(cls(r, "band")) == 3 and len(cls(r, "ln")) == 3
    assert "n=4 instances" in r.find(NS + "title").text and "toy" in r.find(NS + "title").text


def test_solver_failures_are_shown_not_hidden(data, tmp_path):
    mf.make_figures(data, tmp_path)
    for kind in ("nodes", "seconds"):
        r = svg(tmp_path / f"solvers_{kind}_toy.svg")
        labels = [e.text for e in cls(r, "strip-label")]
        assert labels == ["x bfs node_limit", "x ilp timeout", "x ilp too_large"]
        assert len(cls(r, "fail")) == 3  # one cross per (solver, status, T) with failures
        assert [e.text for e in cls(r, "fail-label")] == ["2", "1", "1"]  # counts of failed rows at T*=5
        assert len(cls(r, "ln")) == 1 and len(cls(r, "pt")) == 4  # astar solved T=3,5; bfs and ilp solved only T=3 (single points)
    # y axis is log: tick labels are powers of ten
    assert all(t.text in {"0.01", "0.1", "1", "10", "100", "0.001", "1000"} for t in cls(svg(tmp_path / "solvers_nodes_toy.svg"), "ytick-label"))


def test_ilp_rate_figure(data, tmp_path):
    mf.make_figures(data, tmp_path)
    r = svg(tmp_path / "ilp_rate_toy.svg")
    assert len(cls(r, "pt")) == 2 and len(cls(r, "band")) == 1  # T=3 solved 2/2, T=5 solved 0/2
    assert "n=4 ILP runs" in r.find(NS + "title").text


def test_bind_scatter_pairs_and_failure_marker(data, tmp_path):
    mf.make_figures(data, tmp_path)
    r = svg(tmp_path / "bind_scatter_toy_c4.svg")
    assert len(cls(r, "pt")) == 3 and len(cls(r, "ref")) == 1  # 4 pairs, one ILP timeout
    assert [e.text for e in cls(r, "strip-label")] == ["x ILP timeout (1)"] and len(cls(r, "fail")) == 1
    assert "n=2 instances, 4 (instance, level) rows" in r.find(NS + "title").text
    assert all(float(t.text) > 0 for t in cls(r, "xtick-label"))  # log axes
    r2 = svg(tmp_path / "bind_scatter_toy_c2.svg")
    assert len(cls(r2, "pt")) == 4 and not cls(r2, "fail")


def test_cslack_bars(data, tmp_path):
    mf.make_figures(data, tmp_path)
    r = svg(tmp_path / "bind_cslack_toy.svg")
    assert [e.text for e in cls(r, "xtick-label")] == ["2", "4"]
    assert len(cls(r, "bar")) == 4 and len(cls(r, "eb")) == 4


def test_missing_data_is_skipped_with_note(tmp_path, capsys):
    assert mf.make_figures(tmp_path / "nothing", tmp_path / "o1") == []
    err = capsys.readouterr().out
    assert "[skip] no agents_*.csv" in err and "[skip] no solvers_*.csv" in err and "[skip] no bind" in err
    d = tmp_path / "d"
    write(d / "main" / "solvers_toy.csv", solver_rows())
    names = mf.make_figures(d, tmp_path / "o2")
    assert not any(n.startswith("agents") for n in names) and "solvers_nodes_toy.svg" in names
    assert "[skip] no agents_*.csv" in capsys.readouterr().out


def test_directory_suffix_only_on_collisions(data, tmp_path):
    write(data / "agents_ep300" / "agents_toy.csv", agents_rows())
    names = mf.make_figures(data, tmp_path)
    assert "agents_toy.svg" in names and "agents_toy_agents_ep300.svg" in names
    assert "[agents_ep300]" in svg(tmp_path / "agents_toy_agents_ep300.svg").find(NS + "title").text


def test_deterministic_bytes(data, tmp_path):
    a = mf.make_figures(data, tmp_path / "a")
    b = mf.make_figures(data, tmp_path / "b")
    assert a == b and a
    for n in a:
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes()


def test_cli_entry_point(data, tmp_path):
    mf.main(["--data", str(data), "--out", str(tmp_path / "cli")])
    assert (tmp_path / "cli" / "agents_toy.svg").exists()
