
import unittest
from unittest.mock import MagicMock, patch
from src.yukkuri_game.game.components import FloatingText, Transform
from src.yukkuri_game.game.systems.floating_text_system import FloatingTextSystem
from src.yukkuri_game.engine.ecs import World

class TestFloatingTextSystem(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.system = FloatingTextSystem()
        self.world.add_system(self.system)

    def test_update(self):
        # Create entity
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=100, y=100))
        self.world.add_component(entity, FloatingText(text="Test", color=(255, 255, 255), lifetime=1.0, velocity_y=-10.0))

        # Update
        dt = 0.1
        self.system.update(self.world, dt)

        # Check position
        transform = self.world.get_component(entity, Transform)
        self.assertEqual(transform.y, 99.0) # 100 + (-10 * 0.1)

        # Check lifetime
        text = self.world.get_component(entity, FloatingText)
        self.assertAlmostEqual(text.lifetime, 0.9)

        # Expire
        dt = 1.0
        self.system.update(self.world, dt)

        # Should be destroyed
        self.assertFalse(self.world.entity_exists(entity))

if __name__ == '__main__':
    unittest.main()
