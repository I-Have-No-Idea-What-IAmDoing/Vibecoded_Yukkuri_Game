import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.components import YukkuriStats, Needs
from yukkuri_game.engine.components import LightSource, Transform
from yukkuri_game.config import StatDecaySettings


class TestEmotionSystemHealthClamp(unittest.TestCase):
    def test_health_clamping(self) -> None:
        from test_utils import make_configured_world
        world = make_configured_world()
        
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.max_health = 100.0
        needs.health = 150.0  # Over limit
        
        entity = world.create_entity()
        world.add_component(entity, stats)
        world.add_component(entity, needs)
        
        system = EmotionSystem()
        world.add_system(system)
        
        dt = 0.2  # Sufficient dt to trigger throttled update
        system.update(world, dt)
        
        # Health should be clamped to max_health
        self.assertEqual(needs.health, 100.0)

    def test_health_clamping_low(self) -> None:
        from test_utils import make_configured_world
        world = make_configured_world()
        
        stats = YukkuriStats(name="Test", type_id="test")
        needs = Needs()
        needs.max_health = 100.0
        needs.health = -50.0  # Under limit
        
        entity = world.create_entity()
        world.add_component(entity, stats)
        world.add_component(entity, needs)
        
        system = EmotionSystem()
        world.add_system(system)
        
        dt = 0.2  # Sufficient dt to trigger throttled update
        system.update(world, dt)
        
        # Health should be clamped to 0
        self.assertEqual(needs.health, 0.0)
