import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.stat_decay import StatDecaySystem
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.config import StatDecaySettings

class TestStatDecaySystemHealthClamp(unittest.TestCase):
    def test_health_clamping(self):
        mock_world = MagicMock()
        mock_world.has_component.return_value = False # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        stats.max_health = 100.0
        stats.health = 150.0 # Over limit

        mock_world.get_components_tuple.return_value = [(1, (stats,))]

        system = StatDecaySystem(settings=StatDecaySettings())
        dt = 0.0 # No decay
        system.update(mock_world, dt)

        # Health should be clamped to max_health
        self.assertEqual(stats.health, 100.0)

    def test_health_clamping_low(self):
        mock_world = MagicMock()
        mock_world.has_component.return_value = False # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        stats.max_health = 100.0
        stats.health = -50.0 # Under limit

        mock_world.get_components_tuple.return_value = [(1, (stats,))]

        system = StatDecaySystem(settings=StatDecaySettings())
        dt = 0.0 # No decay
        system.update(mock_world, dt)

        # Health should be clamped to 0
        self.assertEqual(stats.health, 0.0)
