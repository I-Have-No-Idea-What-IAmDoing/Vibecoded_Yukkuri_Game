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
        from test_utils import make_configured_world
        world = make_configured_world()
        
        stats = YukkuriStats(name="Test", type_id="test")
        stats.age = 100.0
        
        needs = Needs()
        needs.hunger = 50.0
        needs.energy = 50.0
        needs.cleanliness = 100.0
        
        emotional = EmotionalState()
        emotional.happiness = 60.0
        emotional.stress = 10.0
        
        entity = world.create_entity()
        world.add_component(entity, stats)
        world.add_component(entity, needs)
        world.add_component(entity, emotional)
        
        system = EmotionSystem()
        world.add_system(system)
        
        # Set time scale to 1.0
        from yukkuri_game.game.services import TimeService
        world.services.get(TimeService).scale = 1.0
        
        dt = 1.0
        system.update(world, dt)
        
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
        from test_utils import make_configured_world
        world = make_configured_world()
        
        # Set time scale to 1.0
        from yukkuri_game.game.services import TimeService
        world.services.get(TimeService).scale = 1.0
        
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.hunger = 99.0
        needs.energy = 1.0
        
        emotional = EmotionalState()
        emotional.happiness = 50.0
        emotional.stress = 0.0
        
        entity = world.create_entity()
        world.add_component(entity, stats)
        world.add_component(entity, needs)
        world.add_component(entity, emotional)
        
        system = EmotionSystem()
        world.add_system(system)
        
        # Simulate 10 seconds
        total_time = 10.0
        step = 1.0
        for _ in range(int(total_time / step)):
            system.update(world, step)
            
        # Hunger: 99 + 20 = 119 -> Clamp 100
        # Energy: 1 - 5 = -4 -> Clamp 0
        
        self.assertEqual(needs.hunger, 100.0)
        self.assertEqual(needs.energy, 0.0)

    def test_cleanliness_clamping(self) -> None:
        from test_utils import make_configured_world
        world = make_configured_world()
        
        # Set time scale to 1.0
        from yukkuri_game.game.services import TimeService
        world.services.get(TimeService).scale = 1.0
        
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.cleanliness = 1.0
        
        entity = world.create_entity()
        world.add_component(entity, stats)
        world.add_component(entity, needs)
        
        system = EmotionSystem()
        world.add_system(system)
        
        # Simulate 10 seconds
        total_time = 10.0
        step = 1.0
        for _ in range(int(total_time / step)):
            system.update(world, step)
            
        self.assertGreaterEqual(needs.cleanliness, 0.0)
        self.assertEqual(needs.cleanliness, 0.0)

