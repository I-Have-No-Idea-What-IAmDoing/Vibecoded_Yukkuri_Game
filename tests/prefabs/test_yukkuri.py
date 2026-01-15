import unittest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.prefabs.yukkuri import create_yukkuri
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.trait_service import TraitService


class TestYukkuriPrefab(unittest.TestCase):
    def test_create_yukkuri(self) -> None:
        world = World()
        # Mock ResourceManager
        rm = MagicMock(spec=ResourceManager)
        rm.yukkuri_types = {"reimu": {"image": "reimu.png", "max_health": 100}}
        # Mock tuning settings (visuals) which are accessed in prefab
        rm.tuning = MagicMock()
        rm.tuning.visuals.movement.bob_height = 5.0
        rm.tuning.visuals.movement.bob_speed = 10.0

        world.services.register(rm, ResourceManager)

        # Mock TraitService
        ts = MagicMock(spec=TraitService)
        # Ensure we have traits for random choice
        ts.get_all_trait_ids.return_value = ["trait1", "trait2"]
        # Ensure get_trait returns a dict so .get() works
        ts.get_trait.return_value = {}
        world.services.register(ts, TraitService)

        entity = create_yukkuri(world, "reimu", 10, 20)

        self.assertTrue(world.has_component(entity, Transform))
        self.assertTrue(world.has_component(entity, YukkuriStats))

        trans = world.get_component(entity, Transform)
        self.assertEqual(trans.x, 10)
        self.assertEqual(trans.y, 20)


if __name__ == "__main__":
    unittest.main()
