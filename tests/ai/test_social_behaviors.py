import unittest
import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats, Needs
from yukkuri_game.game.components import Transform
from yukkuri_game.game.ai.behaviors.actions.searching import FindSocialTarget
from py_trees.common import Status

class TestSocialBehaviors(unittest.TestCase):
    def setUp(self):
        self.world = World()
        # Mock GameService/NavigationService not strictly needed for FindSocialTarget 
        # as it iterates entities directly.

        # Setup "Self"
        self.ai = AIState()
        self.stats = YukkuriStats(type_id="reimu", name="Self")
        self.transform = Transform(x=100, y=100)
        
        self.entity_id = self.world.create_entity(
            self.ai, self.stats, self.transform, Needs()
        )

        from yukkuri_game.game.systems.spatial_system import SpatialService
        self.spatial_service = SpatialService(1000, 1000, 500)
        self.world.services.register(self.spatial_service, SpatialService)
        # Update entity in spatial service
        self.spatial_service.update_entity(self.entity_id, 100, 100)

    def test_find_social_target_friend(self):
        """Test finding a compatible (same type) friend."""
        # Setup Friend (Reimu) nearby
        friend_id = self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Friend"),
            Transform(x=150, y=100) # 50px away
        )
        self.spatial_service.update_entity(friend_id, 150, 100)
        
        # Setup Enemy (Marisa) nearby - should be ignored
        enemy_id = self.world.create_entity(
            YukkuriStats(type_id="marisa", name="Enemy"),
            Transform(x=120, y=100) # Closer, but incompatible
        )
        self.spatial_service.update_entity(enemy_id, 120, 100)

        action = FindSocialTarget("Find Friend", self.entity_id, self.world, criteria="friend")
        status = action.update()

        self.assertEqual(status, Status.SUCCESS)
        self.assertEqual(self.ai.current_target_id, friend_id)

    def test_find_social_target_enemy(self):
        """Test finding an incompatible (diff type) enemy."""
        # Setup Friend (Reimu) nearby - should be ignored
        friend_id = self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Friend"),
            Transform(x=120, y=100) # Closer, but compatible
        )
        self.spatial_service.update_entity(friend_id, 120, 100)
        
        # Setup Enemy (Marisa) nearby
        enemy_id = self.world.create_entity(
            YukkuriStats(type_id="marisa", name="Enemy"),
            Transform(x=150, y=100) # 50px away
        )
        self.spatial_service.update_entity(enemy_id, 150, 100)

        action = FindSocialTarget("Find Enemy", self.entity_id, self.world, criteria="enemy")
        status = action.update()

        self.assertEqual(status, Status.SUCCESS)
        self.assertEqual(self.ai.current_target_id, enemy_id)

    def test_find_any_target(self):
        """Test finding any nearby target."""
        # Reimu (Friend) at dist 50
        friend_id = self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Friend"),
            Transform(x=150, y=100)
        )
        self.spatial_service.update_entity(friend_id, 150, 100)
        # Marisa (Enemy) at dist 20 (Closer)
        enemy_id = self.world.create_entity(
            YukkuriStats(type_id="marisa", name="Enemy"),
            Transform(x=120, y=100)
        )
        self.spatial_service.update_entity(enemy_id, 120, 100)

        action = FindSocialTarget("Find Any", self.entity_id, self.world, criteria="any")
        status = action.update()

        self.assertEqual(status, Status.SUCCESS)
        self.assertEqual(self.ai.current_target_id, enemy_id) # Should pick closest

    def test_respects_failed_targets(self):
        """Test that ignored targets are skipped."""
        friend_id = self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Friend"),
            Transform(x=150, y=100)
        )
        self.spatial_service.update_entity(friend_id, 150, 100)
        
        self.ai.failed_targets.add(friend_id)

        action = FindSocialTarget("Find Friend", self.entity_id, self.world, criteria="friend")
        status = action.update()

        self.assertEqual(status, Status.FAILURE)

if __name__ == "__main__":
    unittest.main()
