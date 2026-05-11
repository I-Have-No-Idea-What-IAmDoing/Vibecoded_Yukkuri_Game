import unittest
import time
import sys
import os
import pymunk
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.navigation_system import NavigationSystem
from yukkuri_game.game.systems.navigation_update_system import NavigationUpdateSystem
from yukkuri_game.game.systems.steering_system import SteeringSystem
from yukkuri_game.game.systems.visibility_system import VisibilitySystem
# Need visibility system for Close-Range logic to work!

from yukkuri_game.game.components import (
    Transform,
    PhysicsBody,
    MovementController,
    SteeringComponent,
    Vision,
)
from yukkuri_game.game.components import AIState, Needs
from yukkuri_game.game.ai.behaviors import MoveToTarget


class TestPredatorMovingTarget(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        # Import NavigationService directly
        from yukkuri_game.game.ai.navigation_service import NavigationService
        
        NavServiceClass = NavigationService

        self.nav_service = NavServiceClass(
            world_width=1000, world_height=1000, grid_step_size=25, deterministic_mode=True
        )
        self.world.services.register(self.nav_service, service_type=NavServiceClass)

        self.nav_system = NavigationSystem()
        self.nav_update_system = NavigationUpdateSystem()
        self.steering_system = SteeringSystem()
        self.visibility_system = VisibilitySystem()

        self.world.add_system(self.nav_system)
        self.world.add_system(self.nav_update_system)
        self.world.add_system(self.steering_system)
        self.world.add_system(self.visibility_system)

        # time.sleep(0.1) # Removed unnecessary sleep
        self.space = pymunk.Space()

        # We need PhysicsSystem or similar to update physics?
        # Actually SteeringSystem uses physics body velocity.
        # But we are manually moving them in the test loop...
        # Wait, if we use PhysicsBody logic in SteeringSystem, we need bodies to be in space?
        # SteeringSystem query uses `space.point_query`. `space` comes from PhysicsSystem.
        # In this test we mock physics by updating transforms manually?
        # But SteeringSystem reads `velocity` from `PhysicsBody`.
        # I need to ensure PhysicsBodies have velocity if I want intercept logic to work.
        pass

    def tearDown(self):
        self.nav_service.shutdown()

    def test_chase_moving_target(self):
        try:
            # 1. Setup Predator
            predator_ai = AIState()
            predator_move = MovementController()
            predator_steer = SteeringComponent(max_speed=100.0, pursuit_enabled=True)
            predator_vision = Vision(range=500.0)

            # Body needed for steering checks
            p_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            p_shape = pymunk.Circle(p_body, 10)
            predator_phys = PhysicsBody(body=p_body, shape=p_shape)

            predator_id = self.world.create_entity(
                Transform(x=100, y=100),
                predator_ai,
                predator_move,
                predator_steer,
                predator_phys,
                predator_vision,
                Needs(),  # Required by MoveToTarget
            )

            # 2. Setup Prey
            prey_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            prey_shape = pymunk.Circle(prey_body, 10)
            prey_phys = PhysicsBody(body=prey_body, shape=prey_shape)

            prey_id = self.world.create_entity(
                Transform(x=300, y=100),  # 200px away
                prey_phys,
            )

            # 3. Assign Target
            predator_ai.current_target_id = prey_id
            predator_ai.visible_entities.add(
                prey_id
            )  # Make prey visible for Close-Range + LKP

            # Reduce interference from separation and avoidance for cleaner test
            predator_steer.separation_weight = 0.0
            predator_steer.avoidance_weight = 0.0

            # 4. Behavior
            move_action = MoveToTarget(
                entity_id=predator_id, world=self.world, speed=100.0
            )

            # 5. Simulation
            prey_speed = 50.0
            dt = 0.1

            # Mock physics system
            mock_phys_sys = MagicMock()
            mock_phys_sys.space = self.space
            self.space.add(p_body, p_shape)
            self.space.add(prey_body, prey_shape)

            from yukkuri_game.game.systems.physics import PhysicsSystem

            self.world.services.register(mock_phys_sys, service_type=PhysicsSystem)

            positions_log = []

            for _ in range(50):  # 5 seconds
                # Update Prey (Move Right)
                prey_trans = self.world.get_component(prey_id, Transform)
                prey_trans.x += prey_speed * dt
                prey_phys.body.position = (prey_trans.x, prey_trans.y)
                prey_phys.body.velocity = (prey_speed, 0)

                # Logic Tick
                self.visibility_system.update(self.world, dt)

                status = move_action.update()

                self.nav_system.update(self.world, dt)
                self.nav_update_system.update(self.world, dt)
                self.steering_system.update(self.world, dt)

                # Apply predator movement
                pred_trans = self.world.get_component(predator_id, Transform)
                pred_trans.x += predator_move.target_velocity.x * dt
                pred_trans.y += predator_move.target_velocity.y * dt
                predator_phys.body.position = (pred_trans.x, pred_trans.y)
                predator_phys.body.velocity = predator_move.target_velocity

                dist = prey_trans.x - pred_trans.x
                positions_log.append(dist)
                # time.sleep(0.001) # Removed unnecessary sleep in deterministic loop

            final_dist = positions_log[-1]
            min_dist = min(positions_log)
            initial_dist = positions_log[0]
            print(f"Initial: {initial_dist}, Min: {min_dist}, Final: {final_dist}")

            # Success criteria:
            # 1. Minimum distance achieved is significantly less than initial (predator caught up at some point)
            # 2. The predator got closer than 100px at some point
            self.assertLess(
                min_dist,
                initial_dist * 0.5,
                f"Predator never closed gap. Initial: {initial_dist}, Min: {min_dist}",
            )
            self.assertLess(
                min_dist,
                100.0,
                f"Predator never got close enough. Min dist: {min_dist}",
            )
        except Exception as e:
            import traceback

            with open("integration_fail.log", "w") as f:
                traceback.print_exc(file=f)
            raise e


if __name__ == "__main__":
    unittest.main()
