import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs
from yukkuri_game.game.components import LightSource, Transform
from yukkuri_game.config import StatDecaySettings


class TestEmotionSystemHealthClamp(unittest.TestCase):
    def test_health_clamping(self) -> None:
        mock_world = MagicMock()
        mock_world.has_component.return_value = False  # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.max_health = 100.0
        needs.health = 150.0  # Over limit

        mock_world.services.try_get.return_value = None

        def get_components_tuple(*args):
            if args == (Transform, LightSource):
                return []
            if args == (YukkuriStats, Needs):
                return [(1, (stats, needs))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_tuple

        # Mock EmotionalState to return None or a valid object
        # If None, the system skips emotional update
        mock_world.get_component.return_value = None

        system = EmotionSystem(settings=StatDecaySettings())
        dt = 0.2  # Sufficient dt to trigger throttled update
        system.update(mock_world, dt)

        # Health should be clamped to max_health
        self.assertEqual(needs.health, 100.0)

    def test_health_clamping_low(self) -> None:
        mock_world = MagicMock()
        mock_world.has_component.return_value = False  # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.max_health = 100.0
        needs.health = -50.0  # Under limit

        mock_world.services.try_get.return_value = None

        def get_components_tuple(*args):
            if args == (Transform, LightSource):
                return []
            if args == (YukkuriStats, Needs):
                return [(1, (stats, needs))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_tuple

        # Mock EmotionalState to return None
        mock_world.get_component.return_value = None

        system = EmotionSystem(settings=StatDecaySettings())
        dt = 0.2  # Sufficient dt to trigger throttled update
        system.update(mock_world, dt)

        # Health should be clamped to 0
        self.assertEqual(needs.health, 0.0)
