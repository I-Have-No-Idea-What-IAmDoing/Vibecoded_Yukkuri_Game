import unittest
from unittest.mock import MagicMock, patch
import pymunk
from src.yukkuri_game.game.entity_factory import EntityFactory
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Transform, Sprite, Selectable, PhysicsBody
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.systems.physics import PhysicsSystem

class TestEntityFactory(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.rm = MagicMock(spec=ResourceManager)
        # Initialize the mock dicts on the mock object
        self.rm.yukkuri_types = {}
        self.rm.item_types = {}

        self.world.services.register(self.rm, ResourceManager)

        # Mock physics system (optional)
        self.physics_system = MagicMock(spec=PhysicsSystem)
        self.physics_system.space = MagicMock(spec=pymunk.Space)
        self.world.services.register(self.physics_system, PhysicsSystem)

        self.factory = EntityFactory(self.world)

        # Setup mock data
        self.rm.yukkuri_types.update({
            "reimu": {
                "image": "reimu.png",
                "width": 64,
                "height": 64,
                "max_health": 100,
                "frame_count": 4,
                "frame_duration": 0.2,
                "loop": True
            },
            "marisa": { # Minimal data to test defaults
            }
        })

        self.rm.item_types.update({
            "cookie": {
                "image": "cookie.png",
                "width": 32,
                "height": 32,
                "name": "Cookie",
                "cost": 10,
                "nutrition": 50,
                "fun": 10
            },
            "toy": { # Minimal data
                "name": "Toy",
                "cost": 50,
                "fun": 100
            }
        })

    def test_create_yukkuri(self):
        entity = self.factory.create_yukkuri("reimu", 100, 200)

        # Verify components
        self.assertTrue(self.world.has_component(entity, Transform))
        self.assertTrue(self.world.has_component(entity, Sprite))
        self.assertTrue(self.world.has_component(entity, Selectable))
        self.assertTrue(self.world.has_component(entity, YukkuriStats))
        self.assertTrue(self.world.has_component(entity, AIState))
        self.assertTrue(self.world.has_component(entity, PhysicsBody))

        # Verify component data
        transform = self.world.get_component(entity, Transform)
        self.assertEqual(transform.x, 100)
        self.assertEqual(transform.y, 200)

        sprite = self.world.get_component(entity, Sprite)
        self.assertEqual(sprite.image_name, "reimu.png")
        self.assertEqual(sprite.width, 64)
        self.assertEqual(sprite.frame_count, 4)
        self.assertTrue(sprite.is_animating)

        stats = self.world.get_component(entity, YukkuriStats)
        self.assertEqual(stats.type_id, "reimu")
        self.assertEqual(stats.max_health, 50.0) # Baby (age 0) has 50% health

        # Verify physics
        self.physics_system.space.add.assert_called()

    def test_create_yukkuri_defaults(self):
        # Ensure marisa exists in the dict
        # The rm is re-created in setUp, but the update in setUp might not be persisting as expected if we are modifying a property on a mock?
        # Ah, in setUp we did self.rm.yukkuri_types.update({...}) but self.rm.yukkuri_types is just a dict we assigned.

        # Let's inspect what's happening.
        # self.rm.yukkuri_types is a dict.

        # Why did it fail? "ValueError: Unknown yukkuri type: marisa"
        # It means self.rm.yukkuri_types.get("marisa") returned None or empty dict (if empty dict is falsey, but create_yukkuri checks `if not data`)

        # Wait, empty dict evaluates to False in Python!
        # if not data: will be true if data is {}.

        # So we need some data in it even for defaults test?
        # Actually create_yukkuri accesses keys on it.
        # So "marisa": {} is indeed Falsey.

        self.rm.yukkuri_types["marisa"] = {"exists": True} # Just some dummy data so it's not empty
        entity = self.factory.create_yukkuri("marisa", 50, 50)

        sprite = self.world.get_component(entity, Sprite)
        self.assertEqual(sprite.image_name, "yukkuri_default.png")
        self.assertEqual(sprite.frame_count, 1)
        self.assertFalse(sprite.is_animating)

        stats = self.world.get_component(entity, YukkuriStats)
        self.assertEqual(stats.max_health, 50.0) # Default value (Baby)

    def test_create_yukkuri_unknown_type(self):
        with self.assertRaises(ValueError):
            self.factory.create_yukkuri("unknown", 0, 0)

    def test_create_item(self):
        entity = self.factory.create_item("cookie", 300, 400)

        self.assertTrue(self.world.has_component(entity, Transform))
        self.assertTrue(self.world.has_component(entity, Sprite))
        self.assertTrue(self.world.has_component(entity, Selectable))
        self.assertTrue(self.world.has_component(entity, ItemStats))
        self.assertTrue(self.world.has_component(entity, PhysicsBody))

        stats = self.world.get_component(entity, ItemStats)
        self.assertEqual(stats.name, "Cookie")
        self.assertEqual(stats.nutrition, 50)
        self.assertEqual(stats.fun, 10)
        self.assertEqual(stats.comfort, 0)

    def test_create_item_defaults(self):
        entity = self.factory.create_item("toy", 0, 0)

        stats = self.world.get_component(entity, ItemStats)
        self.assertEqual(stats.nutrition, 0)
        self.assertEqual(stats.comfort, 0)
        self.assertFalse(stats.is_portable)

        sprite = self.world.get_component(entity, Sprite)
        self.assertEqual(sprite.image_name, "item_default.png")

    def test_create_item_unknown_type(self):
        with self.assertRaises(ValueError):
            self.factory.create_item("unknown", 0, 0)

    def test_get_attr_object_access(self):
        # Verify that _get_attr works with objects/dataclasses as well as dicts
        class MockData:
            def __init__(self):
                self.test_attr = "value"

        data = MockData()
        self.assertEqual(self.factory._get_attr(data, "test_attr"), "value")
        self.assertEqual(self.factory._get_attr(data, "missing", "default"), "default")

    def test_create_entity_without_physics(self):
        # Create a new world/factory without physics system registered
        world = World()
        rm = MagicMock(spec=ResourceManager)

        # Setup yukkuri_types as a real dict, not a property on a mock
        # Note: If rm is a mock, rm.yukkuri_types = ... sets it on the instance
        rm.yukkuri_types = {"reimu": {"image": "reimu.png"}}

        world.services.register(rm, ResourceManager)

        factory = EntityFactory(world)

        entity = factory.create_yukkuri("reimu", 0, 0)
        self.assertFalse(world.has_component(entity, PhysicsBody))

if __name__ == '__main__':
    unittest.main()
