import unittest
from unittest.mock import MagicMock
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import FloatingText, Transform
from src.yukkuri_game.game.systems.floating_text_system import FloatingTextSystem
from src.yukkuri_game.game.entity_factory import EntityFactory
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.systems.physics import PhysicsSystem

class TestFloatingText(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.system = FloatingTextSystem()

        # Mock services for factory
        self.rm = MagicMock(spec=ResourceManager)
        self.world.services.register(self.rm, ResourceManager)
        self.world.services.register(MagicMock(spec=PhysicsSystem), PhysicsSystem)

        self.factory = EntityFactory(self.world)
        self.world.services.register(self.factory)

    def test_creation(self):
        entity = self.factory.create_floating_text("Test", 100, 100)
        ft = self.world.get_component(entity, FloatingText)
        tr = self.world.get_component(entity, Transform)

        self.assertIsNotNone(ft)
        self.assertIsNotNone(tr)
        self.assertEqual(ft.text, "Test")
        self.assertEqual(tr.x, 100)
        self.assertEqual(tr.y, 100)

    def test_movement_and_lifetime(self):
        entity = self.factory.create_floating_text("Move", 0, 0, dy=-10, lifetime=0.5)

        # Update 0.1s
        self.system.update(self.world, 0.1)
        tr = self.world.get_component(entity, Transform)
        ft = self.world.get_component(entity, FloatingText)

        self.assertAlmostEqual(tr.y, -1.0) # 0 + (-10 * 0.1)
        self.assertAlmostEqual(ft.age, 0.1)

        # Update past lifetime
        self.system.update(self.world, 0.5) # Total 0.6s > 0.5s

        # Entity should be destroyed (not in world anymore)
        # However, world.destroy_entity might be deferred or immediate depending on implementation.
        # In this simple ECS, it's usually immediate or marked.
        # Let's check if component still exists.

        # Usually get_component returns None if entity destroyed or component missing
        # But if entity is destroyed, `get_component` might raise error or return None.
        # Let's check `world.entities` if we can access it, or try getting component.

        # If entity is destroyed, it shouldn't be in the list returned by get_entities_with
        entities = self.world.get_entities_with(FloatingText)
        self.assertFalse(entity in entities)

if __name__ == '__main__':
    unittest.main()
