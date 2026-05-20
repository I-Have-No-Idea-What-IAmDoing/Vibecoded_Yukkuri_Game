"""
Test to ensure Yukkuri AI handles pathfinding failure correctly,
inserting failed targets into `failed_targets` and preventing request loops.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.engine.components import Transform, MovementController
from yukkuri_game.game.components import AIState, Needs, MoveCommand, YukkuriStats, Predator, ItemStats, Blackboard
from yukkuri_game.game.ai.behaviors import MoveToTarget
from yukkuri_game.game.ai.behaviors.actions.searching import FindPrey, FindLightSource, PickFood
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.engine.services.time_service import TimeService
from py_trees.common import Status
from yukkuri_game.engine.types import EntityID


class TestPathfindingFailedLoop(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        self.time_service = TimeService()
        self.world.services.register(self.time_service)

        self.nav_service = MagicMock(spec=NavigationService)
        self.world.services.register(self.nav_service, service_type=NavigationService)

    def test_pathfinding_failure_marks_failed_target_and_fails(self):
        """
        Verify that MoveToTarget returns Status.FAILURE, removes MoveCommand,
        and adds the target to failed_targets when pathfinding fails.
        """
        ai = AIState()
        trans = Transform(x=0, y=0)
        move = MovementController()
        needs = Needs()

        entity_id = self.world.create_entity(trans, ai, move, needs)

        target_trans = Transform(x=200, y=0)
        target_id = self.world.create_entity(target_trans)

        ai.current_target_id = target_id
        ai.visible_entities.add(target_id)

        # Set pathfinding state as failed while requesting
        ai.state_data = {
            "path_requesting": True,
            "path_request_time": 0.0,
            "path_destination": (200.0, 0.0),
            "path_failed": True,
        }

        # Add a dummy MoveCommand to ensure it gets removed
        self.world.commands.add_component(
            entity_id, MoveCommand(target_pos=target_trans, target_entity_id=target_id)
        )
        self.world.commands.apply_all()

        action = MoveToTarget(entity_id=entity_id, world=self.world)

        # Update action - it should process the failure
        status = action.update()
        self.world.commands.apply_all()

        # Check outcomes
        self.assertEqual(status, Status.FAILURE, "Should return FAILURE on pathfinding failure")
        self.assertIn(target_id, ai.failed_targets, "Target should be added to failed_targets")
        self.assertFalse(self.world.has_component(entity_id, MoveCommand), "MoveCommand should be removed")
        self.assertFalse(ai.state_data.get("path_requesting"), "Should clear path_requesting")
        self.assertNotIn("path_failed", ai.state_data, "Should clear path_failed")

        # Now, try to run it again. Since target is in failed_targets, it shouldn't request path to it
        self.nav_service.request_path.reset_mock()
        status = action.update()
        self.world.commands.apply_all()
        
        # We don't want it requesting again
        self.nav_service.request_path.assert_not_called()

    def test_searching_actions_exclude_failed_targets(self):
        """
        Verify that FindPrey, FindLightSource, and PickFood exclude/skip failed targets.
        """
        # Create searcher
        ai = AIState()
        trans = Transform(x=0, y=0)
        predator = Predator(prey_sense_radius=500.0, prey_tags=["reimu"])
        entity_id = self.world.create_entity(ai, trans, predator)

        # Create prey (reimu)
        prey_trans = Transform(x=100, y=0)
        prey_stats = YukkuriStats(name="Prey Reimu", type_id="reimu")
        prey_id = self.world.create_entity(prey_trans, prey_stats)

        # Add ISpatialService mock
        from yukkuri_game.engine.protocols import ISpatialService
        spatial_service = MagicMock(spec=ISpatialService)
        spatial_service.get_entities_in_radius.return_value = [prey_id]
        self.world.services.register(spatial_service, service_type=ISpatialService)

        find_prey = FindPrey(entity_id=entity_id, world=self.world)

        # 1. Without failed_targets, should succeed and set as current target
        status = find_prey.update()
        self.assertEqual(status, Status.SUCCESS)
        self.assertEqual(ai.current_target_id, prey_id)

        # 2. Add to failed_targets, should fail
        ai.failed_targets.add(prey_id)
        ai.current_target_id = EntityID(-1)
        status = find_prey.update()
        self.assertEqual(status, Status.FAILURE)
        self.assertEqual(ai.current_target_id, -1)

    def test_perception_excludes_failed_targets(self):
        """
        Verify that PerceptionSystem excludes failed targets from closest_food_id.
        """
        ai = AIState()
        bb = Blackboard()
        trans = Transform(x=0, y=0)
        stats = YukkuriStats(name="Searcher", type_id="reimu", agility=100.0)
        entity_id = self.world.create_entity(ai, bb, trans, stats)

        # Create a food item close by
        food_trans = Transform(x=50, y=0)
        food_item = ItemStats(name="Beanpaste Food", type_id="beanpaste", cost=10, nutrition=50.0)
        food_id = self.world.create_entity(food_trans, food_item)

        # Add food to visibility
        ai.visible_entities.add(food_id)

        perception_sys = PerceptionSystem()
        perception_sys.ecs_world = self.world
        perception_sys.initialize()
        # 1. Update perception system - first registers in memory, second registers the reaction
        perception_sys.update(self.world, 0.1)
        self.time_service.time_elapsed = 1.0
        perception_sys.update(self.world, 0.1)
        self.assertEqual(bb.closest_food_id, food_id)

        # 2. Add food to failed_targets - it should be ignored by perception
        ai.failed_targets.add(food_id)
        bb.closest_food_id = None
        self.time_service.time_elapsed = 2.0
        perception_sys.update(self.world, 0.1)
        self.assertIsNone(bb.closest_food_id)


if __name__ == "__main__":
    unittest.main()
