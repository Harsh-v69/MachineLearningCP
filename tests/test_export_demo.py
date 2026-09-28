import pytest

from experiments.export_demo import GAMES, build_game


@pytest.mark.parametrize("gid", list(GAMES))
def test_demo_data_is_sound(gid):
    d = build_game(gid)
    assert d["good"]["goal"], "the good plan must solve the game"
    flagged = d["bad_checked"]["steps"][d["bad_at"]]
    assert not flagged["ok"] or flagged["conf"] < 1, "the checker must flag the bad plan"
    assert d["choose"]["method"] in ("astar", "cp_sat")
    assert d["run"]["after_actions"], "replanning after a slip must produce a path"
    assert 0 < d["run"]["memory_conf"] < 1
