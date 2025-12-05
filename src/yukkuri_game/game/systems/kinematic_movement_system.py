"""
Kinematic Movement System.
Implements the Sweep-and-Slide algorithm for deterministic character movement.
"""

import pymunk
from typing import Optional
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, Transform
from .physics import PhysicsSystem

class KinematicMovementSystem(System):
    """
    System responsible for moving Kinematic bodies using a sweep-and-slide algorithm
    against the static/dynamic geometry database.

    This system implements a FIXED TIMESTEP update loop internally to ensure
    determinism regardless of the frame rate.
    """

    def __init__(self):
        self.space: Optional[pymunk.Space] = None
        self.accumulator = 0.0
        self.time_step = 1.0 / 60.0
        self.max_frame_time = 0.25

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

        # Clamp dt
        if dt > self.max_frame_time:
            dt = self.max_frame_time

        self.accumulator += dt

        while self.accumulator >= self.time_step:
            self.fixed_update(world, self.time_step)
            self.accumulator -= self.time_step

    def fixed_update(self, world: World, dt: float):
        """
        Runs the deterministic movement logic.
        """
        # Note: get_components_tuple returns (ent, [comp1, comp2, ...])
        components = world.get_components_tuple(PhysicsBody, MovementController, Transform)

        for entity, (phys, controller, trans) in components:
            # Only handle Kinematic bodies
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Update prev position for interpolation BEFORE moving
            trans.prev_x = phys.body.position.x
            trans.prev_y = phys.body.position.y

            self.move_and_slide(phys, controller, trans, dt)

            # Note: trans is updated inside move_and_slide now, but we can verify
            if trans.x != phys.body.position.x:
                 trans.x = phys.body.position.x
                 trans.y = phys.body.position.y

    def move_and_slide(self, phys: PhysicsBody, controller: MovementController, trans: Transform, dt: float):
        """
        Performs the sweep-and-slide movement logic.
        """
        body = phys.body
        shape = phys.shape

        # 1. Virtual Physics: Acceleration / Friction
        input_vector = controller.target_velocity
        current_velocity = controller.current_velocity

        # Calculate velocity change
        target = input_vector
        diff = target - current_velocity
        change_mag = controller.acceleration * dt

        if diff.length_squared > 0.000001:
            if change_mag >= diff.length:
                current_velocity = target
            else:
                current_velocity += diff.normalized() * change_mag

        controller.current_velocity = current_velocity

        # 2. Desired Displacement
        move_delta = current_velocity * dt

        # Early exit if negligible movement
        if move_delta.length_squared < 0.000001:
            return

        # 3. Sweep and Slide
        remaining_move = move_delta
        original_pos = body.position
        start_pos = body.position

        # Determine appropriate radius for sweep
        radius = 1.0
        if isinstance(shape, pymunk.Circle):
             radius = shape.radius
        elif isinstance(shape, pymunk.Poly):
             # For Poly, use the bounding box or an average dimension?
             # Or use a small radius and rely on the shape itself being moved?
             # No, segment_query with radius effectively sweeps a circle (Capsule).
             # If we sweep a capsule of radius R, we are simulating a Circle of radius R moving.
             # If the character IS a box, this approximation might be wrong.
             # But the proposal says "Approximation: We approximate characters as Circles or Capsules".
             # So if the character HAS a Box shape, we should probably approximate it as a Circle for movement.
             # Calculate radius from bounding box.
             bb = shape.bb
             width = bb.right - bb.left
             height = bb.top - bb.bottom
             radius = min(width, height) / 2.0
        elif hasattr(shape, 'radius'):
             radius = shape.radius

        query_filter = shape.filter

        # Skin width to avoid getting stuck in walls
        skin_width = 0.01

        iterations = 3
        for i in range(iterations):
            if remaining_move.length_squared < 0.000001:
                break

            # Extend cast by skin width to detect collision slightly early?
            # Or just cast exactly. Pymunk segment_query checks against shapes.
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
                # Ignore internal edges/back-faces (moving away from wall)
                if info.normal.dot(remaining_move) >= 0:
                    continue

                hit = info
                break

            if hit:
                # Resolve Collision

                safe_fraction = max(0.0, hit.alpha - (skin_width / remaining_move.length) if remaining_move.length > 0 else 0)

                # Move to the safe spot
                actual_move = remaining_move * safe_fraction
                start_pos += actual_move

                # Slide
                # Remainder is the part of the vector we couldn't travel
                remainder = remaining_move * (1.0 - safe_fraction)

                # Project remainder onto wall tangent
                normal = hit.normal
                dot = remainder.dot(normal)
                slide_vec = remainder - normal * dot

                remaining_move = slide_vec
            else:
                # No hit
                start_pos = end_pos
                remaining_move = pymunk.Vec2d(0, 0)
                break

        # 4. Commit Position
        body.position = start_pos

        # Update Transform immediately (requested by review)
        trans.x = start_pos.x
        trans.y = start_pos.y

        # 5. Update Velocity based on actual movement
        if dt > 0.000001:
            effective_velocity = (start_pos - original_pos) / dt
            controller.current_velocity = effective_velocity
