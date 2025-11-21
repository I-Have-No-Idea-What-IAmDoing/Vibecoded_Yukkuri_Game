import unittest
from unittest.mock import MagicMock
from src.yukkuri_game.game.systems.decision import DecisionSystem
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, AIState
from src.yukkuri_game.game.ai.utility import UtilityAIEngine

class TestDecisionSystem(unittest.TestCase):
    def test_decision_interval(self):
        mock_ai_engine = MagicMock()
        mock_world = MagicMock()

        system = DecisionSystem(mock_ai_engine, decision_interval=1.0)

        # No entities for this test, just checking timer
        mock_world.get_components_tuple.return_value = []

        # dt = 0.5, timer = 0.5 < 1.0 -> No decision
        system.update(mock_world, 0.5)
        mock_ai_engine.select_action.assert_not_called()

        # dt = 0.6, timer = 1.1 >= 1.0 -> Decision
        system.update(mock_world, 0.6)

        # Need to setup entities for select_action to be called?
        # No, make_decisions is called if timer triggers, but loop inside depends on entities.
        # So if no entities, select_action still not called but timer resets.
        self.assertAlmostEqual(system.timer, 0.0)

    def test_decision_logic(self):
        mock_ai_engine = MagicMock()
        mock_world = MagicMock()

        stats = YukkuriStats(name="Test", type_id="test")
        ai = AIState()
        ai.current_action = "Idle"

        mock_world.get_components_tuple.return_value = [(1, (stats, ai))]

        # Mock AI engine response
        mock_ai_engine.select_action.return_value = "Eat"

        system = DecisionSystem(mock_ai_engine, decision_interval=1.0)

        # Trigger update
        system.update(mock_world, 1.0)

        mock_ai_engine.select_action.assert_called_once()
        self.assertEqual(ai.current_action, "Eat")
        self.assertEqual(ai.action_progress, 0.0)

    def test_decision_no_change(self):
        mock_ai_engine = MagicMock()
        mock_world = MagicMock()

        stats = YukkuriStats(name="Test", type_id="test")
        ai = AIState()
        ai.current_action = "Eat"
        ai.action_progress = 5.0

        mock_world.get_components_tuple.return_value = [(1, (stats, ai))]
        mock_ai_engine.select_action.return_value = "Eat"

        system = DecisionSystem(mock_ai_engine, decision_interval=1.0)
        system.update(mock_world, 1.0)

        self.assertEqual(ai.current_action, "Eat")
        self.assertEqual(ai.action_progress, 5.0) # Should NOT reset if action same
