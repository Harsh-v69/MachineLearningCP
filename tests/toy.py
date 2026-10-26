from tapegraph.problem import Problem
from tapegraph.solvers import astar, bfs, idastar


class GraphProblem(Problem):
    """Explicit graph. adj[s] = [(action, next, resource)]; every edge costs 1."""

    def __init__(self, adj, goal, h=None):
        self.adj, self.goal, self._h = adj, goal, h or {}

    def neighbors(self, s):
        for a, v, _ in self.adj[s]:
            yield a, v, 1.0

    def is_goal(self, s):
        return s == self.goal

    def h(self, s):
        return float(self._h.get(s, 0))

    def res(self, s, a, s2):
        return float(next(r for a2, v, r in self.adj[s] if a2 == a))


# Two routes A->E: short but resource-hungry (len 2, res 6) vs long and cheap (len 3, res 3).
GRAPH = GraphProblem(
    {
        "A": [("ab", "B", 1), ("ac", "C", 1)],
        "B": [("be", "E", 5)],
        "C": [("cd", "D", 1)],
        "D": [("de", "E", 1)],
        "E": [],
        "X": [],  # dead end: goal unreachable
    },
    goal="E",
    h={"A": 2, "B": 1, "C": 1, "D": 1, "E": 0},
)


# Diamond with a shared middle node M. Unit edge costs, h = 0 (so A* pops in g order).
#   A-p1->P1-m->M  g=2, res 1+5=6        A-p2->P2-m->M  g=2, res 1+1=2  (same g, lower res: dominates the first)
#   A-c1->C1-c2->C2-m->M  g=3, res 0     (larger g, smaller res: neither dominates the (2,2) label, so M keeps both)
#   M-g->G (res 3).  Best constrained paths: res_budget>=5 -> via P2 (cost 3, res 5); 3..4 -> via C (cost 4, res 3); <3 -> none.
DIAMOND = GraphProblem(
    {
        "A": [("p1", "P1", 1), ("p2", "P2", 1), ("c1", "C1", 0)],
        "P1": [("m", "M", 5)],
        "P2": [("m", "M", 1)],
        "C1": [("c2", "C2", 0)],
        "C2": [("m", "M", 0)],
        "M": [("g", "G", 3)],
        "G": [],
    },
    goal="G",
)


def assert_solvers_agree(p, s, b=None):
    """BFS ignores h and prune, so it is the reference: A* and IDA* must return its cost. Returns the BFS result."""
    b = b or bfs.solve(p, s)
    a, i = astar.solve(p, s), idastar.solve(p, s)
    assert b.status == a.status == i.status == "ok"
    assert a.cost == b.cost == i.cost, "inadmissible h or unsound prune"
    return b
