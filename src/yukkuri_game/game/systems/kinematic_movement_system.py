"""
Kinematic Movement System.
Implements the Sweep-and-Slide algorithm for deterministic character movement.
"""

import pymunk
from typing import Optional
from loguru import logger
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

        # 1. Move all Kinematic Bodies
        for entity, (phys, controller, trans) in components:
            # Only handle Kinematic bodies
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Update prev position for interpolation BEFORE moving
            trans.prev_x = phys.body.position.x
            trans.prev_y = phys.body.position.y

            self.move_and_slide(phys, controller, trans, dt)

            # Reindex shape immediately so subsequent queries in this frame (or by other entities)
            # see the new position. This is crucial for unit-vs-unit collision accuracy within the same frame.
            if self.space:
                self.space.reindex_shapes_for_body(phys.body)

            # Note: trans is updated inside move_and_slide now, but we can verify
            if trans.x != phys.body.position.x:
                 trans.x = phys.body.position.x
                 trans.y = phys.body.position.y

        # 2. Step the Physics Space (Spatial Hash Update)
        # We do this AFTER moving kinematic bodies so the hash is consistent for the NEXT frame,
        # or for any non-kinematic physics (if added later).
        # Also, reindex_shapes_for_body handles the immediate update, but step() handles global maintenance.
        if self.space:
            self.space.step(dt)

    def move_and_slide(self, phys: PhysicsBody, controller: MovementController, trans: Transform, dt: float):
        """
        Performs the sweep-and-slide movement logic.
        """
        body = phys.body
        shape = phys.shape

        # 1. Virtual Physics: Acceleration / Friction
        input_vector = controller.target_velocity
        current_velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            # Apply Friction (Damping)
            friction = controller.friction
            # Simple damping: vel = vel * (1 - friction * dt)
            # Ensure we don't flip direction if friction is huge
            damping = max(0.0, 1.0 - friction * dt)
            current_velocity = current_velocity * damping

            # Snap to 0 if very small
            if current_velocity.length_squared < 0.0001:
                current_velocity = pymunk.Vec2d(0, 0)
        else:
            # Apply Acceleration
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
            # Even if not moving, sync transform
            trans.x = body.position.x
            trans.y = body.position.y
            return

        # 3. Sweep and Slide
        remaining_move = move_delta
        original_intent = move_delta # Save for dot product check
        original_pos = body.position
        start_pos = body.position

        # Determine appropriate radius for sweep
        radius = 1.0
        if isinstance(shape, pymunk.Circle):
             radius = shape.radius
        elif isinstance(shape, pymunk.Poly):
             # For Poly, use max dimension to be safe (circumscribed-ish)
             bb = shape.bb
             width = bb.right - bb.left
             height = bb.top - bb.bottom
             radius = max(width, height) / 2.0
        elif hasattr(shape, 'radius'):
             radius = shape.radius

        query_filter = shape.filter

        # Skin width to avoid getting stuck in walls
        skin_width = 0.01

        iterations = 3
        for i in range(iterations):
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

                # 4. Filter internal edges or back-faces
                # If moving away from normal, ignore
                if info.normal.dot(remaining_move) > 0.0001:
                     continue

                hit = info
                break

            if hit:
                # Resolve Collision
                # logger.trace(f"Collision detected with normal {hit.normal} at alpha {hit.alpha}")

                safe_fraction = max(0.0, hit.alpha - (skin_width / remaining_move.length) if remaining_move.length > 0 else 0)

                # Move to the safe spot
                actual_move = remaining_move * safe_fraction
                start_pos += actual_move

                # Slide
                remainder = remaining_move * (1.0 - safe_fraction)
                normal = hit.normal

                dot = remainder.dot(normal)
                slide_vec = remainder - normal * dot

                # Corner Handling / Opposing Intent
                # If the slide vector opposes the ORIGINAL intent, we might be wedged.
                # However, sliding along a wall usually means dot(slide, original) > 0.
                # If we hit a second wall that reflects us BACK, dot might be negative.

                if slide_vec.dot(original_intent) < 0:
                     # Stop movement if sliding pushes us back against our will
                     remaining_move = pymunk.Vec2d(0, 0)
                     break

                remaining_move = slide_vec
            else:
                # No hit
                start_pos = end_pos
                remaining_move = pymunk.Vec2d(0, 0)
                break

        # 4. Commit Position
        body.position = start_pos

        # Update Transform immediately to ensure rendering sync
        trans.x = start_pos.x
        trans.y = start_pos.y

        # 5. Update Velocity based on actual movement
        if dt > 0.000001:
            effective_velocity = (start_pos - original_pos) / dt
            controller.current_velocity = effective_velocity
