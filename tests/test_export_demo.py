import pytest

from experiments.export_demo import GAMES, build_game


@pytest.mark.parametrize("gid", list(GAMES))
def test_demo_data_is_sound(gid):
    d = build_game(gid)
    assert d["good"]["goal"], "the good plan must solve the game"
    if d["bad_kind"] == "static":  # checker only guards the start: it must stop an unsolvable one
        assert d["gate"]["gated"] <= 2 and d["gate"]["plain"] > 1000
        assert d["bad_checked"]["goal"], "Plan B is a valid, longer plan"
    else:
        flagged = d["bad_checked"]["steps"][d["bad_at"]]
        assert not flagged["ok"] or flagged["conf"] < 1, "the checker must flag the bad plan"
    w = d["wrong"]  # the worse-than-a-slip scenario
    assert len(d["by"]) == 2 and w["kind"] in ("lost", "deadend", "stuck", "detour")
    assert w["wrong"] != w["planned"] and len(w["before_actions"]) == w["step"]
    if w["kind"] == "lost":
        assert w["reason"], "a position the checker flags must say why"
    if w["kind"] == "deadend":
        assert not w["probe"]["solved"] and w["probe"]["nodes"] < w["probe"]["budget"]
        assert w["checked_nodes"] <= w["probe"]["nodes"]
    if w["kind"] == "detour":
        assert len(w["after_actions"]) >= w["remaining"] - 1
    assert d["choose"]["method"] in ("astar", "cp_sat")
    assert d["run"]["after_actions"], "replanning after a slip must produce a path"
    assert 0 < d["run"]["memory_conf"] < 1


def test_boxoban_demo_plan_solves_its_level():
    from experiments.export_demo import build_boxoban
    from tape.envs.boxoban import load_boxoban

    d = build_boxoban()
    assert d["moves"] == len(d["actions"]) and d["prune_nodes"] < d["budget"]
    lv = load_boxoban(limit=d["index"] + 1)[d["index"]]
    cur = lv.initial_state
    for a in d["actions"]:
        cur, moved = lv.step(cur, a)
        assert moved
    assert lv.is_goal(cur)
