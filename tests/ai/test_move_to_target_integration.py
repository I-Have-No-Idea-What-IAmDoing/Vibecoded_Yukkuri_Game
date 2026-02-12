import unittest
import pymunk
from unittest.mock import MagicMock
from yukkuri_game.game.ai.behaviors import MoveToTarget
from yukkuri_game.game.components import Transform, PhysicsBody, MovementController, MoveCommand
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats, Needs
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.ai.navigation_service import NavigationService
import py_trees


class TestPathfindingRobustness(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.entity_id = self.world.create_entity()

        # Mock components
        self.world.add_component(self.entity_id, Transform(x=0, y=0))
        self.world.add_component(self.entity_id, AIState())
        self.world.add_component(
            self.entity_id, YukkuriStats(name="Test", type_id="test")
        )
        self.world.add_component(self.entity_id, Needs(energy=100.0))
        self.world.add_component(self.entity_id, MovementController())

        # Mock Physics
        self.space = pymunk.Space()
        body = pymunk.Body(1, 1)
        body.position = (0, 0)
        # Use a filter that doesn't match the raycast filter (0b1)
        # We'll set the category of the entity to something else or 0, so it doesn't block the ray
        shape = pymunk.Circle(body, 10)
        shape.filter = pymunk.ShapeFilter(categories=0b10)  # Category 2
        self.space.add(body, shape)
        self.world.add_component(self.entity_id, PhysicsBody(body=body, shape=shape))

        # Mock Services
        self.nav_service = MagicMock(spec=NavigationService)
        self.world.services.register(self.nav_service, NavigationService)

        # Mock Blackboard
        py_trees.blackboard.Blackboard().set("dt", 0.1)

    def test_move_to_target_straight_line(self) -> None:
        """Test that entity moves towards target in a straight line when path is clear"""
        action = MoveToTarget(entity_id=self.entity_id, world=self.world)
        ai = self.world.get_component(self.entity_id, AIState)
        ai.state_data = {"target_x": 100, "target_y": 0}

        # Mock pathfinding to return a straight line
        ai.path = [(50, 0), (100, 0)]

        status = action.update()
        self.assertEqual(status, py_trees.common.Status.RUNNING)

        # MoveToTarget now adds a MoveCommand instead of setting velocity directly
        self.assertTrue(self.world.has_component(self.entity_id, MoveCommand))
        cmd = self.world.get_component(self.entity_id, MoveCommand)
        self.assertEqual(cmd.target_pos, pymunk.Vec2d(100, 0))


if __name__ == "__main__":
    unittest.main()
