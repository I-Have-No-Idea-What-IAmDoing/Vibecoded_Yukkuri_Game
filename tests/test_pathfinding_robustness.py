
import unittest
import pymunk
from unittest.mock import MagicMock
from src.yukkuri_game.game.ai.behavior import MoveToTarget
from src.yukkuri_game.game.components import Transform, PhysicsBody
from src.yukkuri_game.game.yukkuri_components import AIState
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.services import GameService
from src.yukkuri_game.game.ai.navigation_service import NavigationService
import py_trees

class TestPathfindingRobustness(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.entity_id = self.world.create_entity()

        # Mock components
        self.world.add_component(self.entity_id, Transform(x=0, y=0))
        self.world.add_component(self.entity_id, AIState())

        # Mock Physics
        self.space = pymunk.Space()
        body = pymunk.Body(1, 1)
        body.position = (0, 0)
        # Use a filter that doesn't match the raycast filter (0b1)
        # We'll set the category of the entity to something else or 0, so it doesn't block the ray
        shape = pymunk.Circle(body, 10)
        shape.filter = pymunk.ShapeFilter(categories=0b10) # Category 2
        self.space.add(body, shape)
        self.world.add_component(self.entity_id, PhysicsBody(body=body, shape=shape))

        # Mock Services
        self.nav_service = MagicMock(spec=NavigationService)
        self.world.services.register(NavigationService, self.nav_service)

        # Mock Blackboard
        py_trees.blackboard.Blackboard().set("dt", 0.1)

    def test_move_to_target_straight_line(self):
        """Test that entity moves towards target in a straight line when path is clear"""
        action = MoveToTarget(entity_id=self.entity_id, world=self.world)
        ai = self.world.get_component(self.entity_id, AIState)
        ai.state_data = {"target_x": 100, "target_y": 0}

        # Mock pathfinding to return a straight line
        ai.path = [(50, 0), (100, 0)]

        status = action.update()
        self.assertEqual(status, py_trees.common.Status.RUNNING)

        trans = self.world.get_component(self.entity_id, Transform)
        # Should have moved towards 50, 0 (or 100, 0 if string pulling worked)
        # Since physics is mocked but not stepped, we check if velocity was set
        phys = self.world.get_component(self.entity_id, PhysicsBody)
        self.assertNotEqual(phys.body.velocity, (0, 0))

    def test_string_pulling_skips_node(self):
        """Test that string pulling skips intermediate nodes if clear"""
        action = MoveToTarget(entity_id=self.entity_id, world=self.world)
        ai = self.world.get_component(self.entity_id, AIState)
        ai.state_data = {"target_x": 100, "target_y": 0}

        # Path with a slight detour that is actually clear
        # Start (0,0) -> (20, 10) -> (50, 0) -> (100, 0)
        ai.path = [(20, 10), (50, 0), (100, 0)]

        # Since the space is empty, raycast should pass for all

        status = action.update()
        self.assertEqual(status, py_trees.common.Status.RUNNING)

        # Check if the first node was popped (skipped)
        # Logic:
        # (0,0) to (20,10) -> Clear
        # (0,0) to (50,0) -> Clear (Index 1)
        # (0,0) to (100,0) -> Clear (Index 2) - potentially out of range for "look ahead 3 nodes" if max is 3
        # The code looks ahead up to 3 nodes. indices 0, 1, 2.
        # min(3, 3) -> range(2, 0, -1) -> 2, 1.
        # Index 2 is (100, 0). If clear, pop 0 and 1.

        # Wait, let's check the range logic in behavior.py
        # for i in range(min(len(ai.path), 3) - 1, 0, -1):
        # len=3. min(3,3)-1 = 2. range(2, 0, -1) -> i=2, i=1.
        # If i=2 is clear, can_skip_to_index=2.
        # Loop `for _ in range(can_skip_to_index): ai.path.pop(0)`
        # Pops 2 times.
        # Remaining path: [(100, 0)]

        self.assertEqual(len(ai.path), 1)
        self.assertEqual(ai.path[0], (100, 0))

    def test_stuck_detection(self):
        """Test that stuck timer increases and triggers repath"""
        action = MoveToTarget(entity_id=self.entity_id, world=self.world)
        ai = self.world.get_component(self.entity_id, AIState)
        ai.state_data = {"target_x": 100, "target_y": 0}
        ai.path = [(100, 0)]

        # Force stuck timer
        action.stuck_timer = 1.1 # Above threshold
        action.last_position = (0, 0)

        status = action.update()

        self.assertEqual(status, py_trees.common.Status.RUNNING)
        self.assertEqual(action.stuck_timer, 0.0)
        self.assertIsNone(ai.path) # Should have cleared path to force repath

if __name__ == '__main__':
    unittest.main()
