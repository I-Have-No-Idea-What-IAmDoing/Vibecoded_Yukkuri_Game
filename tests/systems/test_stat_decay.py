import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    Needs,
    EmotionalState,
    Personality,
)
from yukkuri_game.game.components import LightSource, Transform
from yukkuri_game.config import StatDecaySettings


class TestEmotionSystem(unittest.TestCase):
    def test_stat_decay(self) -> None:
        # Mock World and Component
        mock_world = MagicMock()
        mock_world.has_component.return_value = False  # Not dead

        stats = YukkuriStats(name="Test", type_id="test")
        stats.age = 100.0

        needs = Needs()
        needs.hunger = 50.0
        needs.energy = 50.0
        needs.cleanliness = 100.0

        emotional = EmotionalState()
        emotional.happiness = 60.0
        emotional.stress = 10.0

        # Setup mock return
        mock_world.services.try_get.return_value = None

        def get_components_tuple(*args):
            if args == (Transform, LightSource):
                return []
            if args == (YukkuriStats, Needs):
                return [(1, (stats, needs))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_tuple

        # Handle get_component calls inside update
        def get_component(entity, comp_type):
            if comp_type == EmotionalState:
                return emotional
            if comp_type == Personality:
                return None
            return None

        mock_world.get_component.side_effect = get_component

        system = EmotionSystem(settings=StatDecaySettings())
        dt = 1.0
        # dt=1.0 fits within MAX_UPDATES_PER_FRAME (2.0s)
        system.update(mock_world, dt)

        # Expected values
        # hunger += 2.0 * dt -> 52.0
        # energy -= 0.5 * dt -> 49.5
        # age += dt -> 101.0
        # cleanliness -= 0.2 * dt -> 99.8

        # Happiness: 60 - 0.5 * dt = 59.5

        self.assertAlmostEqual(needs.hunger, 52.0)
        self.assertAlmostEqual(needs.energy, 49.5)
        self.assertAlmostEqual(emotional.happiness, 59.5)
        self.assertAlmostEqual(stats.age, 101.0)
        self.assertAlmostEqual(needs.cleanliness, 99.8)

    def test_clamping(self) -> None:
        mock_world = MagicMock()
        mock_world.has_component.return_value = False  # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.hunger = 99.0
        needs.energy = 1.0

        emotional = EmotionalState()
        emotional.happiness = 50.0  # Baseline
        emotional.stress = 0.0

        mock_world.services.try_get.return_value = None

        def get_components_tuple(*args):
            if args == (Transform, LightSource):
                return []
            if args == (YukkuriStats, Needs):
                return [(1, (stats, needs))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_tuple

        def get_component(entity, comp_type):
            if comp_type == EmotionalState:
                return emotional
            return None

        mock_world.get_component.side_effect = get_component

        system = EmotionSystem(settings=StatDecaySettings())
        # Simulate 10 seconds in 1-second chunks to avoid throttling clamp
        total_time = 10.0
        step = 1.0
        for _ in range(int(total_time / step)):
            system.update(mock_world, step)

        # Hunger: 99 + 20 = 119 -> Clamp 100
        # Energy: 1 - 5 = -4 -> Clamp 0

        self.assertEqual(needs.hunger, 100.0)
        self.assertEqual(needs.energy, 0.0)

    def test_cleanliness_clamping(self) -> None:
        mock_world = MagicMock()
        mock_world.has_component.return_value = False  # Not dead
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.cleanliness = 1.0

        mock_world.services.try_get.return_value = None

        def get_components_tuple(*args):
            if args == (Transform, LightSource):
                return []
            if args == (YukkuriStats, Needs):
                return [(1, (stats, needs))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_tuple
        mock_world.get_component.return_value = None

        system = EmotionSystem(settings=StatDecaySettings())
        # Simulate 10 seconds in 1-second chunks
        total_time = 10.0
        step = 1.0
        for _ in range(int(total_time / step)):
            system.update(mock_world, step)

        self.assertGreaterEqual(needs.cleanliness, 0.0)
        self.assertEqual(needs.cleanliness, 0.0)
