import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.ai.utility import UtilityAIEngine, Action, Consideration
from yukkuri_game.engine.data_models import AIData, AIAction, ActionEffect, ActionConsideration
from yukkuri_game.game.yukkuri_components import Personality

class MockResourceManager:
    def __init__(self, actions_data):
        self.ai_actions = actions_data

class MockTraitService:
    def __init__(self, traits_data):
        self.traits = traits_data

    def get_trait(self, trait_id):
        return self.traits.get(trait_id)

def test_utility_ai_parsing():
    # Mock data matching actions.toml structure but as objects (simulating loaded msgspec)
    mock_actions = {
        "Eat": AIAction(
            weight=2.0,
            effects=ActionEffect(type="interact_item", stat_changes={}),
            considerations=[
                ActionConsideration(name="Hunger", input="hunger", curve="linear", params={"m": 1.0, "b": 0.0})
            ]
        ),
        "Sleep": AIAction(
            weight=1.5,
            effects=ActionEffect(type="interact_item", stat_changes={}),
            considerations=[
                ActionConsideration(name="Tiredness", input="energy_inv", curve="logit", params={"k": 10.0, "x0": 0.7})
            ]
        )
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

def test_utility_calculation():
    # Setup Engine with specific actions
    mock_actions = {
        "TestHigh": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(name="C1", input="val", curve="linear", params={"m": 1.0, "b": 0.0})
            ]
        ),
        "TestLow": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(name="C2", input="val_inv", curve="inverse_linear", params={})
            ]
        )
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

def test_utility_override():
    # Mock action with linear curve
    mock_actions = {
        "TestOverride": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(name="MyConsideration", input="val", curve="linear", params={"m": 1.0, "b": 0.0})
            ]
        )
    }

    # Mock trait that overrides "MyConsideration" to be inverted (m=-1, b=1)
    mock_traits = {
        "REBEL": {
            "ai_modifiers": {
                "MyConsideration": {
                    "curve": "linear",
                    "params": {"m": -1.0, "b": 1.0}
                }
            }
        }
    }

    rm = MockResourceManager(mock_actions)
    ts = MockTraitService(mock_traits)
    engine = UtilityAIEngine(rm, trait_service=ts)

    context = {"val": 100.0}

    # Without personality: Linear (m=1) -> 1.0
    score_normal = engine.actions["TestOverride"].calculate_utility(context)
    assert score_normal == 1.0

    # With personality REBEL: Inverted (m=-1, b=1) -> 1*-1 + 1 = 0.0
    personality = Personality(traits={"REBEL"})

    # We test select_action as it does the gathering of overrides
    # But since there is only one action, it might still select it if threshold isn't set,
    # but the score should be 0.

    # Actually select_action returns "Idle" if best score is 0.
    action_name = engine.select_action(context, personality)

    # We can also check internal score if we exposed it or mocked the action logic better.
    # But here:
    # Normal: score 1.0 -> selects TestOverride
    # Rebel: score 0.0 -> selects Idle (default)

    assert engine.select_action(context, None) == "TestOverride"
    assert engine.select_action(context, personality) == "Idle"
