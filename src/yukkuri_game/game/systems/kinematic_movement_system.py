"""
Kinematic Movement System.
Implements a Robust Sweep-and-Slide algorithm for deterministic character movement.
Includes multi-plane sliding to prevent corner jitter and a pre-step depenetration pass.
"""

import pymunk
import math
from loguru import logger
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import PhysicsFixedUpdateEvent
from ..components import PhysicsBody, MovementController, Transform
from .physics import PhysicsSystem


class FakeHit:
    """Helper class to simulate a collision hit result."""

    def __init__(self, n, a):
        self.normal = n
        self.alpha = a


class KinematicMovementSystem(System):
    """
    System responsible for moving Kinematic bodies using a sweep-and-slide algorithm
    against the static/dynamic geometry database.

    Features:
    - Fixed Timestep Update
    - Capsule/Circle Sweeping (No Box approximation)
    - Multi-plane slide resolution (prevents V-corner getting stuck)
    - Pre-step Depenetration (Fallback)
    - Composite Shape Sweep Support
    """

    def __init__(self):
        self.space: pymunk.Space = None
        self.skin_width = 0.01
        self.event_bus = None
        self.ecs_world = None
        self._poly_radius_cache = {}

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent):
        if not self.space:
            return

        # Ensure we have the world. If ecs_world is None, we can't update.
        if self.ecs_world:
            self.fixed_update(self.ecs_world, event.dt)
        else:
            logger.warning(
                "KinematicMovementSystem: Fixed update skipped because world is not initialized."
            )

    def update(self, world: World, dt: float) -> None:
        """
        Updates kinematic entities.
        """
        if not self.space:
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                self.space = physics_system.space

        if not self.event_bus:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(PhysicsFixedUpdateEvent, self.on_fixed_update)
                self.ecs_world = world

        self.ecs_world = world

    def fixed_update(self, world: World, dt: float):
        """
        Runs the deterministic movement logic.
        """
        components = world.get_components_tuple(
            PhysicsBody, MovementController, Transform
        )

        for entity, (phys, controller, trans) in components:
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # 0. Sync Transform to Body
            start_pos = phys.body.position

            # 1. Depenetration (Fallback)
            clean_pos = self.resolve_penetration(phys, start_pos)
            if clean_pos != start_pos:
                phys.body.position = clean_pos
                start_pos = clean_pos

            trans.prev_x = start_pos.x
            trans.prev_y = start_pos.y

            # 2. Perform Movement
            self.move_and_slide(phys, controller, trans, dt)

            # 3. Sync Transform back
            trans.x = phys.body.position.x
            trans.y = phys.body.position.y

    def resolve_penetration(self, phys: PhysicsBody, pos: pymunk.Vec2d) -> pymunk.Vec2d:
        """
        Checks if the body is currently overlapping static geometry and pushes it out.
        This is a fallback mechanism. A perfect sweep system shouldn't need this often.
        """
        current_pos = pos
        # Increase iterations to handle complex overlaps
        max_iterations = 3

        for iter_idx in range(max_iterations):
            phys.body.position = current_pos
            # Force update of shapes to match body position
            phys.body.space.reindex_shapes_for_body(phys.body)

            total_push = pymunk.Vec2d(0, 0)
            hits = 0

            for shape in phys.body.shapes:
                infos = self.space.shape_query(shape)
                if not infos:
                    continue

                for info in infos:
                    # Ignore self and sensors
                    if info.shape.body == phys.body or info.shape.sensor:
                        continue

                    # Ignore sensors on the other body too (e.g. hitboxes)
                    if info.shape.sensor:
                        continue

                    contact_set = info.contact_point_set
                    if len(contact_set.points) == 0:
                        continue

                    best_push = pymunk.Vec2d(0, 0)

                    for point in contact_set.points:
                        if point.distance < -0.001:
                            # IMPORTANT: Pymunk's shape_query normal points from QueryShape -> SpaceShape (A->B).
                            # If we want to push QueryShape (A) away from SpaceShape (B), we need to push in direction -Normal.
                            # Since distance is negative (penetration), "Normal * Distance" is "-Normal * Positive".
                            # This pushes A away from B.

                            push = contact_set.normal * (point.distance)

                            # Accumulate max penetration depth per contact normal?
                            # Using just one best push per shape query might be enough
                            if push.length_squared > best_push.length_squared:
                                best_push = push

                    if best_push.length_squared > 0:
                        total_push += best_push
                        hits += 1

            if hits > 0:
                if total_push.length_squared < 0.000001:
                    break
                # Average push? Or sum? Sum is safer for corners.
                current_pos += total_push
            else:
                break

        phys.body.position = pos  # Restore
        return current_pos

    def _get_poly_radius(self, shape: pymunk.Poly) -> float:
        """Calculates the radius of a circle that fully circumscribes the polygon."""

        # Check cache if available.
        if shape in self._poly_radius_cache:
            return self._poly_radius_cache[shape]

        verts = shape.get_vertices()

        # We don't need to transform verts to world, because we calculate the radius in local space.
        # `shape.offset` is the center of our sweep capsule in local space.

        # Pymunk's Poly vertices are stored relative to the body's position.
        # If `shape.offset` exists on Poly, we use it. If not, we assume (0,0).

        sweep_origin_local = getattr(shape, "offset", pymunk.Vec2d(0, 0))

        max_sq = 0.0
        for v in verts:
            d_sq = v.get_dist_sq(sweep_origin_local)
            if d_sq > max_sq:
                max_sq = d_sq

        radius = math.sqrt(max_sq)
        self._poly_radius_cache[shape] = radius
        return radius

    def move_and_slide(
        self,
        phys: PhysicsBody,
        controller: MovementController,
        trans: Transform,
        dt: float,
    ):
        body = phys.body

        # 1. Virtual Physics Integration
        input_vector = controller.target_velocity
        velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            friction = controller.friction
            damping = max(0.0, 1.0 - friction * dt)
            velocity = velocity * damping
            if velocity.length_squared < 0.0001:
                velocity = pymunk.Vec2d(0, 0)
        else:
            diff = input_vector - velocity
            change = controller.acceleration * dt
            if change >= diff.length:
                velocity = input_vector
            else:
                velocity += diff.normalized() * change

        controller.current_velocity = velocity

        # 2. Sweep Movement
        move_delta = velocity * dt
        if move_delta.length_squared < 0.000001:
            return

        current_pos = body.position

        # Rigorous Slide Logic
        max_slides = 5

        for i in range(max_slides):
            if move_delta.length_squared < 0.000001:
                break

            target_pos = current_pos + move_delta

            # Perform Sweep for ALL shapes in the body
            best_hit = None
            best_alpha = 1.0

            for shape in body.shapes:
                if shape.sensor:
                    continue

                radius = 0.0
                if hasattr(shape, "radius") and shape.radius > 0:
                    radius = shape.radius
                elif isinstance(shape, pymunk.Poly):
                    radius = self._get_poly_radius(shape)

                # Bugfix: shape_center_world must be calculated from CURRENT_POS, not body.position
                # Calculate offset relative to body
                shape_offset = getattr(shape, "offset", pymunk.Vec2d(0, 0))
                rotated_offset = shape_offset.rotated(body.angle)
                shape_center_world = current_pos + rotated_offset
                shape_dest = shape_center_world + move_delta

                results = self.space.segment_query(
                    shape_center_world, shape_dest, radius, shape.filter
                )

                for info in results:
                    if info.shape.body == body:
                        continue
                    if info.shape.sensor:
                        continue

                    # Backface check
                    if info.normal.dot(move_delta) > 0.0001:
                        continue

                    if info.alpha < best_alpha:
                        best_alpha = info.alpha
                        best_hit = info

            # Fallback: If no hit detected, verify if target_pos is penetrating
            # This handles cases where segment_query misses start-overlap or corner cases
            if best_hit is None:
                 # Temporarily move body to target to check for overlap
                 original_pos = body.position
                 body.position = target_pos
                 self.space.reindex_shapes_for_body(body)

                 found_overlap = False
                 fallback_normal = pymunk.Vec2d(0, 0)

                 for shape in body.shapes:
                     if shape.sensor: continue

                     infos = self.space.shape_query(shape)
                     for info in infos:
                         if info.shape.body == body or info.shape.sensor or info.shape.sensor:
                             continue

                         contact_set = info.contact_point_set
                         if len(contact_set.points) > 0:
                             # Check if meaningful penetration
                             # Use same threshold as resolve_penetration
                             # Only block if we are actually penetrating, not just touching
                             min_dist = 0.0
                             for p in contact_set.points:
                                 if p.distance < min_dist:
                                     min_dist = p.distance

                             if min_dist < -0.001:
                                 # We have a penetration at target
                                 # Find the normal that opposes movement
                                 # Use the normal from contact set
                                 normal = contact_set.normal

                                 surface_normal = -normal

                                 # Only consider if it opposes movement?
                                 if surface_normal.dot(move_delta) < 0:
                                     found_overlap = True
                                     fallback_normal = surface_normal
                                     break
                     if found_overlap: break

                 # Restore body
                 body.position = original_pos
                 self.space.reindex_shapes_for_body(body)

                 if found_overlap:
                     # Simulate a hit at alpha=0
                     best_alpha = 0.0
                     best_hit = FakeHit(fallback_normal, 0.0)

            if best_hit:
                # Move to hit
                md_len = move_delta.length
                safe_alpha = (
                    max(0.0, best_hit.alpha - (self.skin_width / md_len))
                    if md_len > 0.0001
                    else 0.0
                )

                step_move = move_delta * safe_alpha
                current_pos += step_move

                # Slide Logic
                remainder = move_delta * (1.0 - safe_alpha)

                dot = remainder.dot(best_hit.normal)
                remainder = remainder - best_hit.normal * dot

                move_delta = remainder

                v_dot = velocity.dot(best_hit.normal)
                velocity = velocity - best_hit.normal * v_dot

            else:
                # No hit, move full distance
                current_pos += move_delta
                move_delta = pymunk.Vec2d(0, 0)
                break

        body.position = current_pos
        controller.current_velocity = velocity
