"""
Tests for Utility AI Engine.
"""

from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.engine.data_models import (
    AIAction,
    ActionEffect,
    ActionConsideration,
)


class MockResourceManager:
    """Mock resource manager for testing."""

    def __init__(self, actions_data):
        self.ai_actions = actions_data


def test_utility_ai_parsing() -> None:
    """
    Tests parsing of AI action data into Action objects.
    """
    # Mock data matching actions.toml structure but as objects (simulating loaded msgspec)
    mock_actions = {
        "Eat": AIAction(
            weight=2.0,
            effects=ActionEffect(type="interact_item", stat_changes={}),
            considerations=[
                ActionConsideration(
                    name="Hunger",
                    input="hunger",
                    curve="linear",
                    params={"m": 1.0, "b": 0.0},
                )
            ],
        ),
        "Sleep": AIAction(
            weight=1.5,
            effects=ActionEffect(type="interact_item", stat_changes={}),
            considerations=[
                ActionConsideration(
                    name="Tiredness",
                    input="energy_inv",
                    curve="logit",
                    params={"k": 10.0, "x0": 0.7},
                )
            ],
        ),
    }

    rm = MockResourceManager(mock_actions)
    engine = UtilityAIEngine(rm)

    assert "Eat" in engine.actions
    assert "Sleep" in engine.actions

    eat_action = engine.actions["Eat"]
    assert eat_action.weight == 2.0
    assert len(eat_action.considerations) == 1
    assert eat_action.considerations[0].name == "Hunger"
    assert eat_action.considerations[0].curve_type == "linear"


def test_utility_calculation() -> None:
    """
    Tests calculation of utility scores and action selection.
    """
    # Setup Engine with specific actions
    mock_actions = {
        "TestHigh": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(
                    name="C1", input="val", curve="linear", params={"m": 1.0, "b": 0.0}
                )
            ],
        ),
        "TestLow": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(
                    name="C2", input="val_inv", curve="inverse_linear", params={}
                )
            ],
        ),
    }
    rm = MockResourceManager(mock_actions)
    engine = UtilityAIEngine(rm)

    # Context 1: val = 100 (High should score 1.0, Low should score 0.0)
    context1 = {"val": 100.0, "val_inv": 100.0}
    # Wait, inverse linear in utility.py: return 1.0 - v. v is normalized x/100.
    # If val_inv is 100, v=1.0, score=0.0. Correct.

    score_high = engine.actions["TestHigh"].calculate_utility(context1)
    score_low = engine.actions["TestLow"].calculate_utility(context1)

    assert score_high == 1.0
    assert score_low == 0.0
    assert engine.select_action(context1) == "TestHigh"

    # Context 2: val = 0 (High score 0.0, Low score 1.0)
    context2 = {"val": 0.0, "val_inv": 0.0}
    score_high = engine.actions["TestHigh"].calculate_utility(context2)
    score_low = engine.actions["TestLow"].calculate_utility(context2)

    assert score_high == 0.0
    assert score_low == 1.0
    assert engine.select_action(context2) == "TestLow"
