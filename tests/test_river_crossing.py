"""River crossing: a second benchmark (not Sokoban) exercising the exact
same pipeline. See src/tape/envs/river_crossing.py for why step() must
NOT enforce the safety rule itself -- that's the validator's job."""
from tape.envs.river_crossing import LEVEL_CLASSIC, RiverState
from tape.envs.river_crossing_validator import RiverSafetyValidator
from tape.executor import run_episode
from tape.experience import ExperienceStore
from tape.llm import AdversarialMockLLMClient, MockLLMClient, _bfs_plan


def test_classical_three_pairs_safe_optimal_is_eleven_moves():
    """The textbook answer for 3 missionaries/3 cannibals, boat capacity
    2, is 11 one-way trips. This is an independent ground-truth check,
    not just "the code agrees with itself"."""
    validator = RiverSafetyValidator()
    plan = _bfs_plan(LEVEL_CLASSIC, LEVEL_CLASSIC.initial_state, 20, validator=validator)
    assert len(plan) == 11

    state = LEVEL_CLASSIC.initial_state
    for action in plan:
        nxt, moved = LEVEL_CLASSIC.step(state, action)
        assert moved
        assert validator.validate(LEVEL_CLASSIC, state, action, nxt).accept
        state = nxt
    assert LEVEL_CLASSIC.is_goal(state)


def test_step_does_not_enforce_safety_by_itself():
    """The raw environment lets you take 2 missionaries across first,
    leaving 1 missionary alone with 3 cannibals on the near bank -- a
    fatal configuration step() has no opinion about."""
    state = LEVEL_CLASSIC.initial_state
    nxt, moved = LEVEL_CLASSIC.step(state, "2M")
    assert moved
    assert nxt == RiverState(missionaries_left=1, cannibals_left=3, boat_left=False)


def test_validator_rejects_outnumbered_and_accepts_safe_moves():
    validator = RiverSafetyValidator()
    state = LEVEL_CLASSIC.initial_state

    unsafe_next, _ = LEVEL_CLASSIC.step(state, "2M")
    assert not validator.validate(LEVEL_CLASSIC, state, "2M", unsafe_next).accept

    safe_next, _ = LEVEL_CLASSIC.step(state, "2C")
    assert validator.validate(LEVEL_CLASSIC, state, "2C", safe_next).accept


def test_complexity_is_always_one_a_single_boat_not_independent_pieces():
    assert LEVEL_CLASSIC.complexity(LEVEL_CLASSIC.initial_state) == 1


def test_pipeline_solves_with_a_validator_aware_mock_llm():
    validator = RiverSafetyValidator()
    result = run_episode(
        LEVEL_CLASSIC, MockLLMClient(seed=1, validator=validator), n_candidates=8,
        max_depth=20, validator=validator, experience=ExperienceStore(),
        level_id="river", path_selection="adaptive",
    )
    assert result.success
    assert result.total_actions == 11
    assert result.validator_rejections == 0
    assert result.path_selection_methods == ["astar"]  # complexity 1


def test_pipeline_fails_without_knowledge_of_the_safety_rule():
    """The real point of the validator: an LLM that hasn't been told the
    rule (here, one proposing pure random legal moves) essentially never
    stumbles onto a full safe solution on its own -- unlike Sokoban,
    where this gap only showed up under an adversarial stress test, here
    it's immediate, because almost every greedy-looking move is unsafe."""
    validator = RiverSafetyValidator()
    result = run_episode(
        LEVEL_CLASSIC, AdversarialMockLLMClient(seed=2), n_candidates=50, max_depth=15,
        validator=validator, path_selection="adaptive",
    )
    assert not result.success
    assert result.validator_rejections > 0
