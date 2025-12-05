"""
Kinematic Movement System.
Implements the Sweep-and-Slide algorithm for deterministic character movement.
"""

import pymunk
from typing import Optional
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController
from .physics import PhysicsSystem

class KinematicMovementSystem(System):
    """
    System responsible for moving Kinematic bodies using a sweep-and-slide algorithm
    against the static/dynamic geometry database.
    """

    def __init__(self):
        self.space: Optional[pymunk.Space] = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates kinematic entities.
        """
        if not self.space:
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                self.space = physics_system.space
            else:
                return

        for entity, (phys, controller) in world.get_components_tuple(PhysicsBody, MovementController):
            # Only handle Kinematic bodies
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            self.move_and_slide(phys, controller, dt)

    def move_and_slide(self, phys: PhysicsBody, controller: MovementController, dt: float):
        """
        Performs the sweep-and-slide movement logic.
        """
        body = phys.body
        shape = phys.shape

        # 1. Virtual Physics: Acceleration / Friction
        input_vector = controller.target_velocity
        current_velocity = controller.current_velocity

        # Calculate velocity change
        # If we have input (target_velocity != 0), we accelerate towards it.
        # If target is 0, we decelerate (friction).

        # Assuming target_velocity is the desired velocity vector (direction * max_speed)
        target = input_vector
        diff = target - current_velocity

        # If diff is small, just snap?
        # Or use simple proportional approach?
        # Using constant acceleration step:

        change_mag = controller.acceleration * dt

        if diff.length_squared > 0.000001:
            if change_mag >= diff.length:
                current_velocity = target
            else:
                current_velocity += diff.normalized() * change_mag

        # 2. Desired Displacement
        move_delta = current_velocity * dt

        # Early exit if negligible movement
        if move_delta.length_squared < 0.000001:
            controller.current_velocity = current_velocity
            return

        # 3. Sweep and Slide
        remaining_move = move_delta
        original_pos = body.position
        start_pos = body.position

        # Radius for capsule cast
        radius = 1.0
        if isinstance(shape, pymunk.Circle):
            radius = shape.radius

        query_filter = shape.filter

        iterations = 3
        for _ in range(iterations):
            if remaining_move.length_squared < 0.000001:
                break

            end_pos = start_pos + remaining_move

            # Cast
            infos = self.space.segment_query(start_pos, end_pos, radius, query_filter)

            # Sort by fraction (alpha)
            infos.sort(key=lambda x: x.alpha)

            hit = None
            for info in infos:
                # Ignore self
                if info.shape == shape:
                    continue
                # Ignore sensors
                if info.shape.sensor:
                    continue
                # Ignore internal edges/back-faces
                if info.normal.dot(remaining_move) >= 0:
                    continue

                hit = info
                break

            if hit:
                # Resolve Collision
                # Move to hit point minus epsilon buffer
                # safe_alpha = max(0, hit.alpha - epsilon)
                epsilon = 0.01
                dist = remaining_move.length
                safe_dist = max(0, dist * hit.alpha - epsilon)

                actual_move = remaining_move.normalized() * safe_dist
                start_pos += actual_move

                # Slide
                remainder = remaining_move * (1 - hit.alpha)
                # Project remainder onto wall tangent
                normal = hit.normal
                dot = remainder.dot(normal)
                slide_vec = remainder - normal * dot

                remaining_move = slide_vec

                # Stop if sliding into a wall that opposes movement significantly?
                # The loop handles subsequent hits.
            else:
                # No hit
                start_pos = end_pos
                remaining_move = pymunk.Vec2d(0, 0)
                break

        # 4. Commit Position
        body.position = start_pos

        # 5. Update Velocity based on actual movement
        # This ensures that if we hit a wall, our velocity is zeroed out in that direction
        # preventing "sticky" walls or velocity buildup.
        if dt > 0.000001:
            effective_velocity = (start_pos - original_pos) / dt
            controller.current_velocity = effective_velocity
