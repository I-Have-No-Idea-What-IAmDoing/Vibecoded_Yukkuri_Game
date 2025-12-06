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
             # For Poly, calculate radius from bounding box.
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
                # Determine if the normal opposes our movement.
                # If dot(normal, direction) > 0, we are moving away from the wall (back-face).
                # Note: We should be careful about "inside" cases.
                # If alpha is 0 (already intersecting), and dot > 0 (moving away), we ignore.
                # If alpha is 0, and dot < 0 (moving deeper), we block.

                # Check if we are moving against the normal (into the wall)
                # But allow hits if alpha is near zero (inside), even if normal seems to point same way
                # (which shouldn't happen usually for convex shapes, but for segments it might depend on winding)

                # Note: Pymunk segment query normals are relative to the segment, not necessarily opposing the ray?
                # Actually, standard Pymunk segment query returns normal facing the ray origin if outside.
                # If inside, it might be tricky.

                # Relaxed check: Only skip if we are CLEARLY moving away (dot > epsilon) AND alpha is not tiny.
                # If alpha is tiny, we might be inside and the normal might be weird, so we should process it to slide out/stop.

                dot = info.normal.dot(remaining_move)
                if dot > 0.0001 and info.alpha > 0.001:
                     continue

                hit = info
                break

            if hit:
                # Resolve Collision
                # logger.trace(f"Collision detected with normal {hit.normal} at alpha {hit.alpha}")

                if hit.alpha <= 0.00001:
                    # We are starting inside or extremely close.
                    # Stop movement to prevent tunneling further.
                    # Ideally we should push out, but for kinematic controller, just stopping the component
                    # of movement into the wall is safer than teleporting.

                    # If we are stuck, we just slide.
                    pass

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

                # Subtract component parallel to normal to slide
                slide_vec = remainder - normal * dot

                # Safety check: If slide_vec is extremely small or opposes original intention significantly?
                # Actually, standard projection is fine.

                remaining_move = slide_vec
            else:
                # No hit
                # Safety Check: Did we tunnel?
                # Pymunk segment_query can miss collisions near corners or complex geometry.
                # We perform a point_query at the destination to ensure we are not overlapping.

                pq_info = self.space.point_query_nearest(end_pos, radius + skin_width, query_filter)
                if pq_info and pq_info.shape and not pq_info.shape.sensor and pq_info.shape != shape:
                    # Check overlap
                    # point_query_nearest returns distance to the shape surface.
                    # Overlap if distance < radius.
                    # Note: pq_info.distance is positive if outside, negative if inside shape.

                    overlap = radius - pq_info.distance
                    if overlap > 0:
                        # We tunneled or are overlapping.
                        # Push out along the gradient (normal).
                        # pq_info.gradient points OUT of the shape.

                        # Fix position
                        correction = pq_info.gradient * overlap
                        end_pos += correction

                        # Also treat this as a collision for sliding purposes?
                        # If we just correct position, we might keep pushing into it next frame.
                        # Ideally we should reflect velocity or slide.
                        # But since 'remaining_move' was fully consumed (we thought no hit),
                        # we assume we reached the end.
                        # Correcting position is enough to prevent deep tunneling.
                        pass

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
