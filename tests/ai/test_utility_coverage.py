from unittest.mock import MagicMock, patch
from yukkuri_game.game.ai.utility import UtilityAIEngine, Consideration, Action
from yukkuri_game.engine.data_models import AIAction, ActionEffect


class MockResourceManager:
    def __init__(self, actions_data):
        self.ai_actions = actions_data


def test_curve_evaluation():
    # Test different curve types directly via Consideration

    # Linear
    cons = Consideration(
        name="Test", input_key="val", curve_type="linear", params={"m": 1.0, "b": 0.0}
    )
    assert cons.evaluate_curve(0.0) == 0.0
    assert cons.evaluate_curve(50.0) == 0.5
    assert cons.evaluate_curve(100.0) == 1.0

    # Linear with params
    cons = Consideration(
        name="Test", input_key="val", curve_type="linear", params={"m": 0.5, "b": 0.2}
    )
    # v = 0.5. result = 0.5 * 0.5 + 0.2 = 0.45
    assert cons.evaluate_curve(50.0) == 0.45

    # Inverse Linear
    cons = Consideration(
        name="Test", input_key="val", curve_type="inverse_linear", params={}
    )
    assert cons.evaluate_curve(0.0) == 1.0
    assert cons.evaluate_curve(100.0) == 0.0

    # Threshold
    cons = Consideration(
        name="Test", input_key="val", curve_type="threshold", params={"threshold": 0.5}
    )
    assert cons.evaluate_curve(40.0) == 0.0  # 0.4 < 0.5
    assert cons.evaluate_curve(60.0) == 1.0  # 0.6 >= 0.5

    # Logit (S-curve)
    cons = Consideration(
        name="Test", input_key="val", curve_type="logit", params={"k": 10.0, "x0": 0.5}
    )
    # 50 -> 0.5. 1 / (1 + exp(-10 * (0.5-0.5))) = 1/ (1+1) = 0.5
    assert abs(cons.evaluate_curve(50.0) - 0.5) < 0.001
    # 0 -> 0.0. 1 / (1 + exp(-10 * -0.5)) = 1 / (1 + exp(5)) = 1 / (1 + 148) ~ 0.006
    assert cons.evaluate_curve(0.0) < 0.01
    # 100 -> 1.0. 1 / (1 + exp(-10 * 0.5)) = 1 / (1 + exp(-5)) ~ 1.0
    assert cons.evaluate_curve(100.0) > 0.99

    # Unknown curve type
    cons = Consideration(name="Test", input_key="val", curve_type="unknown", params={})
    assert cons.evaluate_curve(50.0) == 0.0


def test_action_parsing_dict():
    # Test parsing actions from dict (legacy/fallback support)
    mock_data = {
        "Eat": {
            "weight": 2.0,
            "considerations": [
                {
                    "name": "Hunger",
                    "input": "hunger",
                    "curve": "linear",
                    "params": {"m": 1.0},
                }
            ],
            "effects": {"type": "interact"},
        }
    }

    rm = MockResourceManager(mock_data)
    engine = UtilityAIEngine(rm)

    assert "Eat" in engine.actions
    action = engine.actions["Eat"]
    assert action.weight == 2.0
    assert len(action.considerations) == 1
    assert action.considerations[0].name == "Hunger"
    assert action.effects["type"] == "interact"


def test_utility_calculation_break_early():
    # Test optimization where if one consideration is 0, it returns 0 immediately
    cons1 = MagicMock(spec=Consideration)
    cons1.score.return_value = 0.0
    cons2 = MagicMock(spec=Consideration)
    cons2.score.return_value = (
        1.0  # Should not be called if optimized, but logic might call it
    )

    action = Action(name="Test", considerations=[cons1, cons2])

    score = action.calculate_utility({})
    assert score == 0.0


def test_select_action_no_actions():
    rm = MockResourceManager({})
    engine = UtilityAIEngine(rm)

    assert engine.select_action({}) == "Idle"


def test_validate_actions_warning():
    # This test requires patching BehaviorRegistry to simulate missing implementation
    # We patch the module where UtilityAIEngine imports BehaviorRegistry from
    # Since UtilityAIEngine does 'from .behavior import BehaviorRegistry' inside the method,
    # we need to patch 'yukkuri_game.game.ai.behaviors.BehaviorRegistry'

    with patch("yukkuri_game.game.ai.behaviors.BehaviorRegistry") as mock_registry:
        mock_registry.get_goals.return_value = {}  # No behaviors registered

        # Setup engine with an action "Eat"
        mock_actions = {
            "Eat": AIAction(
                weight=1.0,
                considerations=[],
                effects=ActionEffect(type="none", stat_changes={}),
            )
        }
        rm = MockResourceManager(mock_actions)
        engine = UtilityAIEngine(rm)

        # Expect warning logs
        with patch("yukkuri_game.game.ai.utility.logger") as mock_logger:
            engine.validate_actions()
            assert mock_logger.warning.called
            # Verify message content
            args, _ = mock_logger.warning.call_args
            assert "has no corresponding behavior implementation" in args[0]
