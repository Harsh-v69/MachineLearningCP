"""Rush Hour's Phase 2 validator. See rush_hour_validator.py's module
docstring for why gridlock isn't locally decidable in general here (a
stuck vehicle can be rescued by a third vehicle moving later) and why
the hard-reject tier is scoped to the one case that IS provably
permanent (a sealed row) rather than any local "looks stuck" guess."""
from tape.envs.rush_hour import LEVEL_CLASSIC, RushHourLevel
from tape.envs.rush_hour_validator import RowGridlockValidator
from tape.executor import run_episode
from tape.llm import MockLLMClient, _bfs_plan


def test_optimal_solution_never_gets_rejected_or_downweighted():
    """The real solution routes through a state where the target has no
    moves (it starts blocked -- that's the whole puzzle). None of that
    should trip the validator, hard or soft, since B always has a legal
    move of its own at every step along this path."""
    validator = RowGridlockValidator()
    plan = _bfs_plan(LEVEL_CLASSIC, LEVEL_CLASSIC.initial_state, 20)
    state = LEVEL_CLASSIC.initial_state
    for action in plan:
        nxt, moved = LEVEL_CLASSIC.step(state, action)
        assert moved
        verdict = validator.validate(LEVEL_CLASSIC, state, action, nxt)
        assert verdict.accept and verdict.confidence == 1.0
        state = nxt


def test_pipeline_still_solves_cleanly_with_the_validator_active():
    validator = RowGridlockValidator()
    result = run_episode(
        LEVEL_CLASSIC, MockLLMClient(seed=1, validator=validator), n_candidates=10,
        max_depth=20, validator=validator, path_selection="adaptive",
    )
    assert result.success
    assert result.total_actions == 6
    assert result.validator_rejections == 0


def test_rejects_a_row_fully_sealed_by_only_horizontal_vehicles():
    # Row 1 is exactly filled, width 6, by X (len 2) and C (len 4): no
    # gap, no vertical vehicle -- a genuine, permanent dead end.
    level = RushHourLevel(["......", "XXCCCC", "......"])
    validator = RowGridlockValidator()
    verdict = validator.validate(level, level.initial_state, "noop", level.initial_state)
    assert not verdict.accept
    assert verdict.confidence == 0.0


def test_does_not_reject_a_packed_row_that_contains_a_vertical_vehicle():
    # Same row occupancy pattern, but the blocker is vertical, so it can
    # vacate its cell by moving out of the row -- not a proven dead end.
    rows = ["....E.", "....E.", "XXDDE.", "......"]
    level = RushHourLevel(rows)
    validator = RowGridlockValidator()
    verdict = validator.validate(level, level.initial_state, "noop", level.initial_state)
    assert verdict.accept  # never a hard reject when a vertical vehicle could still leave


def test_flags_uncertain_when_the_immediate_blocker_also_has_no_move():
    rows = ["....E.", "....E.", "XXDDE.", "......"]
    level = RushHourLevel(rows)
    validator = RowGridlockValidator()
    verdict = validator.validate(level, level.initial_state, "noop", level.initial_state)
    assert verdict.accept and verdict.confidence == 0.5


def test_does_not_flag_uncertain_when_the_blocker_can_still_move():
    # In LEVEL_CLASSIC's start, X is blocked by B, but B itself can move
    # (down, into empty space) -- not a suspicious double-lock.
    validator = RowGridlockValidator()
    verdict = validator.validate(
        LEVEL_CLASSIC, LEVEL_CLASSIC.initial_state, "noop", LEVEL_CLASSIC.initial_state
    )
    assert verdict.accept and verdict.confidence == 1.0
