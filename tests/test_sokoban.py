from tape.envs.sokoban import LEVEL_TRIVIAL, SokobanLevel


def test_trivial_level_push_reaches_goal():
    level = LEVEL_TRIVIAL
    state = level.initial_state
    assert not level.is_goal(state)
    state, moved = level.step(state, "R")  # push box right onto goal
    assert moved
    assert level.is_goal(state)


def test_move_into_wall_is_a_no_op():
    level = LEVEL_TRIVIAL
    state = level.initial_state
    new_state, moved = level.step(state, "L")  # wall to the left
    assert not moved
    assert new_state == state


def test_cannot_push_box_into_wall():
    level = SokobanLevel(["#####", "#.@$#", "#####"])  # box already against the wall
    state = level.initial_state
    new_state, moved = level.step(state, "R")
    assert not moved
    assert new_state == state


def test_render_round_trips_symbols():
    level = LEVEL_TRIVIAL
    rendered = level.render(level.initial_state)
    assert "@" in rendered and "$" in rendered and "." in rendered
