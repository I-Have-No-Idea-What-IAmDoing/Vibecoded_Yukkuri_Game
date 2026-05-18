import unittest
import time
import sys
import os
import pymunk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.ai.navigation_service import (
    NavigationService,
    TraversalCapability,
)
from yukkuri_game.game.systems.navigation_system import NavigationSystem
from yukkuri_game.game.systems.navigation_update_system import NavigationUpdateSystem
from yukkuri_game.engine.components import Transform, PhysicsBody
from yukkuri_game.game.components import AIState


class TestNavigationIntegration(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        # Initialize Navigation Service
        self.nav_service = NavigationService(
            world_width=1000,
            world_height=1000,
            grid_step_size=25,
            deterministic_mode=True,
        )
        self.world.services.register(self.nav_service)

        # Initialize Systems
        self.nav_system = NavigationSystem()
        self.nav_update_system = NavigationUpdateSystem()

        self.world.add_system(self.nav_system)
        self.world.add_system(self.nav_update_system)

        # Start thread
        # time.sleep(0.1) # Removed unnecessary sleep

        # Space for physics bodies (needed for pymunk shapes)
        self.space = pymunk.Space()

    def tearDown(self):
        self.nav_service.shutdown()

    def test_navigation_flow_with_obstacle(self):
        """
        Integration test:
        1. Spawn Entity
        2. Spawn Obstacle (Wall)
        3. Request Path
        4. Verify path avoids obstacle
        """
        # 1. Create a Yukkuri-like entity
        ai_state_comp = AIState()

        yukkuri_id = self.world.create_entity(Transform(x=100, y=100), ai_state_comp)

        # 2. Add an obstacle blocked logic
        # 25px grid.
        # Start: 100, 100
        # Goal:  300, 100
        # Wall:  200, 50 to 200, 150 (Center 200, 100, Width 50, Height 100)

        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (200, 100)
        shape = pymunk.Poly.create_box(body, (50, 100))  # 50px wide, 100px tall
        self.space.add(body, shape)

        # Manually ensure BB is cached (pymunk does this on step usually)
        shape.cache_bb()

        # Create Wall Entity -> Triggers NavigationUpdateSystem
        wall_id = self.world.create_entity(
            PhysicsBody(body=body, shape=shape), Transform(x=200, y=100)
        )

        # Wait for nav service to process the obstacle update (throttled/queued)
        # The update_obstacle_rect is instant on grid, but graph rebuild is async if using HPA*
        # Our implementation updates grid immediately.
        # Graph rebuild might be triggered if using Abstract Search.
        # Wait for nav service to process the obstacle update
        # We must call world.update() to let NavigationUpdateSystem run and mark grid dirty.
        self.world.update(1.0)

        # 3. Request Path
        start = (100.0, 100.0)
        end = (300.0, 100.0)
        self.nav_service.request_path(yukkuri_id, start, end, TraversalCapability.WALK)

        # 4. Wait for result
        found_path = False
        path = None

        # Loop to process systems
        for _ in range(200):  # 2 seconds max
            self.world.update(
                0.01
            )  # Runs NavigationUpdateSystem (nop) and NavigationSystem (checks results)

            if ai_state_comp.path:
                found_path = True
                path = ai_state_comp.path
                break

            if ai_state_comp.state_data and ai_state_comp.state_data.get("path_failed"):
                self.fail("Pathfinding reported failure")

            # time.sleep(0.01) # Removed unnecessary sleep

        self.assertTrue(found_path, "Path was not found in time")
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 2)

        # 5. Verify path validity (should detour)
        # Check if any point in path is inside the obstacle rect
        # Wall Logic:
        # Center 200, 100. Size 50, 100.
        # X range: 175 to 225
        # Y range: 50 to 150

        # The path should NOT pass through the wall.
        # Simple check: Does it go above or below the wall?
        # A straight line would be y=100.
        # Detour usually goes to corners.

        has_detour = False
        min_y = 1000.0
        max_y = -1000.0

        for node in path:
            x, y = node
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            # Additional check: If x is roughly in wall range (175-225)
            # Y should be safely outside 50-150 range.
            if 175 <= x <= 225:
                # 25px grid... margin of error.
                # If Y is inside 60-140, it's colliding.
                if 60 <= y <= 140:
                    self.fail(
                        f"Path collision detected at {node} inside wall (200,100)"
                    )

        # Verify it actually moved away from Y=100
        # Either min_y < 50 or max_y > 150
        self.assertTrue(
            min_y < 60 or max_y > 140,
            f"Path {path} did not detour significantly. Y-Range: {min_y}-{max_y}",
        )


if __name__ == "__main__":
    unittest.main()
