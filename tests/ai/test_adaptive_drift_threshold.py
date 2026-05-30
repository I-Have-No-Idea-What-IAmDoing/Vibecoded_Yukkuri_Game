import unittest
import sys
import os
import pymunk
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.engine.components import Transform, MovementController, PhysicsBody
from yukkuri_game.game.components import AIState, Needs
from yukkuri_game.game.ai.behaviors import MoveToTarget
from yukkuri_game.engine.services.time_service import TimeService


class TestAdaptiveDrift(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)
        self.nav_service = MagicMock(spec=NavigationService)
        self.world.services.register(self.nav_service, service_type=NavigationService)
        self.time_service = TimeService()
        self.world.services.register(self.time_service)

    def test_adaptive_threshold(self):
        try:
            # Setup
            ai = AIState()
            trans = Transform(x=-200, y=0)
            move = MovementController()
            needs = Needs()
            entity_id = self.world.create_entity(trans, ai, move, needs)

            # Setup Target with PhysicsBody
            target_trans = Transform(x=100, y=0)
            target_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            target_body.position = (100, 0)
            target_shape = pymunk.Circle(target_body, 10)
            target_phys = PhysicsBody(body=target_body, shape=target_shape)
            target_id = self.world.create_entity(target_trans, target_phys)

            ai.current_target_id = target_id
            ai.visible_entities.add(target_id)

            action = MoveToTarget(entity_id=entity_id, world=self.world)

            # Helper to set state
            def set_path_dest(dest, last_repath_time=0.0):
                ai.path = [(50, 0), dest]
                ai.state_data = {
                    "path_destination": dest,
                    "last_repath_time": last_repath_time,
                    "path_requesting": False,
                }

            # Case 1: Slow Target (Speed 0) -> Threshold should be 50px (2500 sq)
            target_body.velocity = (0, 0)
            set_path_dest((100, 0))

            # Move target 40px (DistSq 1600 < 2500) -> No Repath
            target_trans.x = 140
            action.update()
            try:
                action.world.commands.apply_all()
            except AttributeError:
                pass
            self.assertIsNotNone(
                ai.path,
                "Slow target, drift 40px should not trigger repath (Threshold 50px)",
            )

            # Case 2: Fast Target (Speed 100) -> Threshold should be tighter
            # Calculation: val = max(20.0, 50.0 - (100 * 0.3)) = 20.0 (400 sq)
            target_body.velocity = (100, 0)
            set_path_dest((100, 0))  # Reset

            # Move target 30px (DistSq 900 > 400) -> Should Repath
            target_trans.x = 130

            # Ensure cooldown doesn't block (using time.time() inside, so set last_repath_time to 0)
            self.time_service.time_elapsed = 60.0

            action.update()
            try:
                action.world.commands.apply_all()
            except AttributeError:
                pass
            self.assertIsNone(
                ai.path,
                "Fast target, drift 30px should trigger repath (Threshold ~20px)",
            )
            self.assertTrue(ai.state_data.get("pursuit_repath"))
        except Exception as e:
            import traceback
            import tempfile

            log_path = os.path.join(tempfile.gettempdir(), "test_adaptive_fail.log")
            with open(log_path, "w") as f:
                traceback.print_exc(file=f)
            raise e


if __name__ == "__main__":
    unittest.main()
