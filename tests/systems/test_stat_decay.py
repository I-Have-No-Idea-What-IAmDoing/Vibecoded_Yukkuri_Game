import unittest
from unittest.mock import MagicMock
from src.yukkuri_game.game.systems.stat_decay import StatDecaySystem
from src.yukkuri_game.game.yukkuri_components import YukkuriStats
from src.yukkuri_game.config import StatDecaySettings

class TestStatDecaySystem(unittest.TestCase):
    def test_stat_decay(self):
        # Mock World and Component
        mock_world = MagicMock()
        mock_world.has_component.return_value = False # Not dead

        stats = YukkuriStats(name="Test", type_id="test")
        stats.hunger = 50.0
        stats.happiness = 50.0
        stats.energy = 50.0
        stats.cleanliness = 100.0
        stats.age = 100.0

        # Setup mock return
        mock_world.get_components_tuple.return_value = [(1, (stats,))]

        system = StatDecaySystem(settings=StatDecaySettings())
        dt = 1.0
        system.update(mock_world, dt)

        # Expected values
        # hunger += 2.0 * dt -> 52.0
        # happiness -= 0.5 * dt -> 49.5
        # energy -= 0.5 * dt -> 49.5
        # age += dt -> 101.0
        # cleanliness -= 0.2 * dt -> 99.8

        self.assertAlmostEqual(stats.hunger, 52.0)
        self.assertAlmostEqual(stats.happiness, 49.5)
        self.assertAlmostEqual(stats.energy, 49.5)
        self.assertAlmostEqual(stats.age, 101.0)
        self.assertAlmostEqual(stats.cleanliness, 99.8)

    def test_clamping(self):
        mock_world = MagicMock()
        mock_world.has_component.return_value = False # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        stats.hunger = 99.0
        stats.happiness = 1.0
        stats.energy = 1.0

        mock_world.get_components_tuple.return_value = [(1, (stats,))]

        system = StatDecaySystem(settings=StatDecaySettings())
        dt = 10.0
        system.update(mock_world, dt)

        # Hunger: 99 + 20 = 119 -> Clamp 100
        # Happiness: 1 - 5 = -4 -> Clamp 0
        # Energy: 1 - 5 = -4 -> Clamp 0

        self.assertEqual(stats.hunger, 100.0)
        self.assertEqual(stats.happiness, 0.0)
        self.assertEqual(stats.energy, 0.0)

    def test_cleanliness_clamping(self):
        mock_world = MagicMock()
        mock_world.has_component.return_value = False # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        stats.cleanliness = 1.0

        mock_world.get_components_tuple.return_value = [(1, (stats,))]

        system = StatDecaySystem(settings=StatDecaySettings())
        # Cleanliness decay is 0.2 per second (default).
        # dt = 10.0 -> decay = 2.0
        # 1.0 - 2.0 = -1.0. Should be clamped to 0.0
        dt = 10.0
        system.update(mock_world, dt)

        self.assertGreaterEqual(stats.cleanliness, 0.0)
        self.assertEqual(stats.cleanliness, 0.0)
