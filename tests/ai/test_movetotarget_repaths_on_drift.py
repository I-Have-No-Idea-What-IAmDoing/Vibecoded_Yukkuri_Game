import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.components import Transform, MovementController
from yukkuri_game.game.yukkuri_components import AIState, Needs
from yukkuri_game.game.ai.behavior import MoveToTarget
from py_trees.common import Status


class TestMoveToTargetDrift(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        self.nav_service = MagicMock(spec=NavigationService)
        self.world.services.register(self.nav_service, service_type=NavigationService)

    def test_repaths_on_drift(self):
        try:
            # Setup Entity
            ai = AIState()
            trans = Transform(x=0, y=0)
            move = MovementController()
            needs = Needs()

            entity_id = self.world.create_entity(trans, ai, move, needs)

            # Setup Target Entity - placed >150px away to avoid close-range optimization
            target_trans = Transform(x=200, y=0)
            target_id = self.world.create_entity(target_trans)

            ai.current_target_id = target_id
            ai.visible_entities.add(target_id)  # Make visible

            # Fake existing path to target's OLD position (200, 0)
            ai.path = [(100.0, 0.0), (200.0, 0.0)]
            ai.state_data = {
                "path_destination": (200.0, 0.0),  # Stored dest
                "last_repath_time": 0.0,  # Ready for repath
            }

            action = MoveToTarget(entity_id=entity_id, world=self.world)

            # 1. Update with target at (100,0) - No Drift (Dest matches target)
            status = action.update()
            self.assertEqual(status, Status.RUNNING)
            self.assertIsNotNone(ai.path)  # Should keep path
            self.assertFalse(ai.state_data.get("pursuit_repath", False))

            # 2. Move Target significantly (to 300, 0) -> Drift = 100 > 50
            target_trans.x = 300.0

            # Advance time slightly to ensure time.time() > last_repath_time (0.0)
            # (It definitely is)

            status = action.update()

            # Expect path cleared and pursuit_repath set
            self.assertEqual(status, Status.RUNNING)
            self.assertIsNone(ai.path, "Path should be cleared due to drift")
            self.assertTrue(
                ai.state_data["pursuit_repath"], "Should flag for pursuit repath"
            )

            # 3. Next update should request path with Priority 0

            # To verify priority, we need to inspect the mock call
            status = action.update()
            self.assertEqual(status, Status.RUNNING)
            self.assertTrue(ai.state_data["path_requesting"])

            # Check mock call
            # Mock args: (entity_id, start_pos, end_pos, capabilities=..., priority=...)
            self.nav_service.request_path.assert_called()
            args, kwargs = self.nav_service.request_path.call_args

            # Priority should be 0 (High)
            self.assertEqual(
                kwargs.get("priority"), 0, "Should request with Priority 0"
            )

            # Also, pursuit_repath should be consumed (False)
            self.assertFalse(ai.state_data["pursuit_repath"])
        except Exception as e:
            import traceback

            with open("test_fail.log", "w") as f:
                traceback.print_exc(file=f)
            raise e


if __name__ == "__main__":
    unittest.main()
