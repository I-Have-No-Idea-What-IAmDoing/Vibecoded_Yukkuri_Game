import pytest
from src.yukkuri_game.game.ai.utility import Consideration, Action, UtilityAIEngine
import math
from unittest.mock import MagicMock

def test_consideration_linear_curve():
    cons = Consideration(
        name="Test Linear",
        input_key="hunger",
        curve_type="linear",
        params={"m": 1.0, "b": 0.0}
    )

    assert cons.score({"hunger": 0}) == 0.0
    assert cons.score({"hunger": 50}) == 0.5
    assert cons.score({"hunger": 100}) == 1.0
    assert cons.score({"hunger": 200}) == 1.0 # Clamped

def test_consideration_inverse_linear_curve():
    cons = Consideration(
        name="Test Inverse Linear",
        input_key="energy",
        curve_type="inverse_linear",
        params={}
    )

    assert cons.score({"energy": 0}) == 1.0
    assert cons.score({"energy": 50}) == 0.5
    assert cons.score({"energy": 100}) == 0.0

def test_consideration_logit_curve():
    # Logit curve: 1 / (1 + exp(-k * (v - x0)))
    # v is normalized input (0-1)
    # k=10, x0=0.5
    cons = Consideration(
        name="Test Logit",
        input_key="value",
        curve_type="logit",
        params={"k": 10.0, "x0": 0.5}
    )

    score_0 = cons.score({"value": 0})
    score_50 = cons.score({"value": 50}) # v=0.5
    score_100 = cons.score({"value": 100})

    assert score_0 < 0.1
    assert math.isclose(score_50, 0.5, abs_tol=0.01)
    assert score_100 > 0.9

def test_consideration_threshold_curve():
    cons = Consideration(
        name="Test Threshold",
        input_key="health",
        curve_type="threshold",
        params={"threshold": 0.3}
    )

    assert cons.score({"health": 20}) == 0.0 # v=0.2 < 0.3
    assert cons.score({"health": 30}) == 1.0 # v=0.3 >= 0.3
    assert cons.score({"health": 40}) == 1.0

def test_action_calculate_utility():
    c1 = Consideration("C1", "k1", "linear", {"m": 1.0, "b": 0.0})
    c2 = Consideration("C2", "k2", "linear", {"m": 1.0, "b": 0.0})

    action = Action(
        name="Test Action",
        considerations=[c1, c2],
        weight=2.0
    )

    context = {"k1": 50, "k2": 80}
    # c1 score = 0.5
    # c2 score = 0.8
    # utility = 2.0 * 0.5 * 0.8 = 0.8

    assert math.isclose(action.calculate_utility(context), 0.8)

def test_action_calculate_utility_zero_weight():
    c1 = Consideration("C1", "k1", "linear", {"m": 1.0})
    action = Action("Test", [c1], weight=0.0)
    assert action.calculate_utility({"k1": 100}) == 0.0

def test_action_no_considerations():
    action = Action("Test", [], weight=1.0)
    assert action.calculate_utility({}) == 0.0

def test_utility_ai_engine_select_action():
    # Mock ResourceManager
    mock_rm = MagicMock()
    mock_rm.ai_actions = {
        "Eat": {
            "weight": 1.0,
            "considerations": [
                {"name": "Hunger", "input": "hunger", "curve": "linear", "params": {"m": 1.0}}
            ]
        },
        "Sleep": {
            "weight": 1.0,
            "considerations": [
                {"name": "Tiredness", "input": "tiredness", "curve": "linear", "params": {"m": 1.0}}
            ]
        }
    }

    engine = UtilityAIEngine(mock_rm)

    # Case 1: Hunger > Tiredness
    context = {"hunger": 80, "tiredness": 20}
    assert engine.select_action(context) == "Eat"

    # Case 2: Tiredness > Hunger
    context = {"hunger": 10, "tiredness": 90}
    assert engine.select_action(context) == "Sleep"

    # Case 3: Both low, idle (or whichever is higher, but if very low might be 0)
    # Here Idle isn't in the dict, but select_action returns "Idle" if no action > -1.0 (init best_score)
    # But calculate_utility returns >= 0.
    # Wait, best_score starts at -1.0.
    # Even with 0 score, it might pick the last one checked if all are 0?
    # Let's check implementation:
    # score > best_score.
    # If first action is 0, 0 > -1, best_action becomes first action.
    # So if all are 0, it picks the last one? No, it iterates dict.

    context = {"hunger": 0, "tiredness": 0}
    # Eat score 0. Sleep score 0.
    # If Eat checked first: best_score=0, best_action="Eat"
    # Then Sleep checked: score=0. 0 > 0 is False.
    # So it returns "Eat".

    # Let's verify the "Idle" behavior.
    # If actions dict is empty, returns "Idle".

    mock_rm.ai_actions = {}
    engine_empty = UtilityAIEngine(mock_rm)
    assert engine_empty.select_action({}) == "Idle"

def test_select_action_defaults_to_idle_when_scores_are_zero():
    mock_rm = MagicMock()
    # Define two actions that will both evaluate to 0.0 given the context
    # "Eat" comes first in the dictionary
    mock_rm.ai_actions = {
        "Eat": {
            "weight": 1.0,
            "considerations": [
                {"name": "Hunger", "input": "hunger", "curve": "linear", "params": {"m": 1.0}}
            ]
        },
        "Sleep": {
            "weight": 1.0,
            "considerations": [
                {"name": "Tiredness", "input": "tiredness", "curve": "linear", "params": {"m": 1.0}}
            ]
        }
    }

    engine = UtilityAIEngine(mock_rm)

    # Context where both hunger and tiredness are 0
    context = {"hunger": 0, "tiredness": 0}

    # Expectation: Should return "Idle" because scores are 0
    # If best_score starts at -1.0, it returns "Eat" (bug).
    selected_action = engine.select_action(context)

    assert selected_action == "Idle", f"Expected 'Idle', but got '{selected_action}'"
