from tapegraph.problem import Problem


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
