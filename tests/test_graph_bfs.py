import pytest

from tapegraph.solvers import ilp

EDGES = [("A", "ab", "B", 1, 1), ("B", "be", "E", 1, 5)]


def test_graph_path_bfs_format_and_unreachable():
    assert ilp.graph_path_bfs("A", {"E"}, EDGES) == [("A", "ab", "B"), ("B", "be", "E")]
    assert ilp.graph_path_bfs("E", {"A"}, EDGES) is None


def test_solve_graph_without_ortools_raises(monkeypatch):
    monkeypatch.setattr(ilp, "ORTOOLS_AVAILABLE", False)
    with pytest.raises(RuntimeError):
        ilp.solve_graph("A", {"E"}, EDGES)
