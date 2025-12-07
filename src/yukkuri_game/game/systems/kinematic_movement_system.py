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

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent):
        if not self.space:
            return

        # Ensure we have the world. If ecs_world is None, we can't update.
        if self.ecs_world:
            self.fixed_update(self.ecs_world, event.dt)
        else:
            logger.warning("KinematicMovementSystem: Fixed update skipped because world is not initialized.")

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
        components = world.get_components_tuple(PhysicsBody, MovementController, Transform)

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
        # Only 1 iteration needed for fallback
        max_iterations = 1

        for _ in range(max_iterations):
            phys.body.position = current_pos

            # Using body-based shape query to handle Composite Shapes automatically
            # Note: shape_query on space doesn't support "query all shapes of a body".
            # We iterate shapes.

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

                    best_push = pymunk.Vec2d(0,0)

                    for point in contact_set.points:
                        if point.distance < -0.001:
                            push = contact_set.normal * (-point.distance)
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

        phys.body.position = pos # Restore
        return current_pos

    def _get_poly_radius(self, shape: pymunk.Poly) -> float:
        """Calculates the radius of a circle that fully circumscribes the polygon."""
        # Check cache if available? Pymunk doesn't cache this.
        # Find max distance from centroid (0,0 in local space usually) to vertices.
        # But wait, vertices are relative to body, not shape offset?
        # shape.get_vertices() returns vertices in world coords? No, local coords?
        # Actually Pymunk Poly vertices are relative to body position + rotation.
        # But for radius calculation, we just need distance from "center".
        # Which center? The one we use for sweeping.
        # We sweep from `shape.body.local_to_world(shape.offset)`.
        # So we need max distance from `shape.offset` to any vertex.

        # For a Poly, get_vertices() returns vertices in local coordinates (relative to the body's center, if not offset).
        # We perform the sweep from `body.local_to_world(shape.offset)`.
        # Therefore, we need the radius of the circle centered at `shape.offset` that encloses all vertices.

        verts = shape.get_vertices()

        # We don't need to transform verts to world, because we calculate the radius in local space.
        # `shape.offset` is the center of our sweep capsule in local space.
        # Note: pymunk.Poly doesn't always have an 'offset' attribute exposed like Circle,
        # but if we are sweeping from the "shape center", we should define what that is.
        # If the shape is defined around (0,0), then offset is (0,0).
        # If the user created a Poly offset from the body center, the vertices reflect that.

        # Pymunk's Poly vertices are stored relative to the body's position.
        # If we sweep from the body's position (plus any explicit offset we use for the sweep),
        # we generally assume the sweep starts at body.position (which is local 0,0).
        # However, `move_and_slide` calculates `shape_center_world = shape.body.local_to_world(shape.offset)`.
        # `pymunk.Poly` does NOT have an `offset` property. It relies on the vertices' positions.
        # So `shape.offset` will likely fail if we try to access it on a Poly unless we monkey-patched it.
        # But `move_and_slide` accesses `shape.offset`!
        # If `shape.offset` exists on Poly, we use it. If not, we assume (0,0).

        # Let's fix the potential AttributeError here and in move_and_slide.

        sweep_origin_local = getattr(shape, 'offset', pymunk.Vec2d(0, 0))

        max_sq = 0.0
        for v in verts:
            d_sq = v.get_dist_sq(sweep_origin_local)
            if d_sq > max_sq:
                max_sq = d_sq

        return math.sqrt(max_sq)


    def move_and_slide(self, phys: PhysicsBody, controller: MovementController, trans: Transform, dt: float):
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
        # Instead of max_slides=4 and simple rejection, we use a loop that handles multiple planes.
        # Max slides should be higher to handle complex jagged geometry.
        max_slides = 5

        for i in range(max_slides):
            if move_delta.length_squared < 0.000001:
                break

            target_pos = current_pos + move_delta

            # Perform Sweep for ALL shapes in the body (Composite Support)
            best_hit = None
            best_alpha = 1.0

            for shape in body.shapes:
                if shape.sensor: continue

                # Determine radius for segment query approximation
                # Note: Segment query is perfect for Circles/Capsules.
                # For Polys, it is an approximation if we just use a radius.
                # Pymunk doesn't have a "Shape Sweep" function exposed easily in Python without CFFI complexity
                # or helper functions. segment_query with radius is the standard "Capsule Cast".
                # If the shape is a Poly, we might want to cast a ray from the vertices?
                # For now, we assume shapes are circular-ish or we use the bounding radius.
                # Using specific shape logic:
                radius = 0.0
                if hasattr(shape, 'radius') and shape.radius > 0:
                    radius = shape.radius
                elif isinstance(shape, pymunk.Poly):
                    # Fix: Use circumscribing radius for Poly to prevent tunneling
                    radius = self._get_poly_radius(shape)

                # Fix: Rename variable for clarity
                # shape_center_world is the center of the shape in world coordinates
                shape_offset = getattr(shape, 'offset', pymunk.Vec2d(0, 0))
                shape_center_world = shape.body.local_to_world(shape_offset)
                shape_dest = shape_center_world + move_delta

                # We query using the shape's radius
                results = self.space.segment_query(shape_center_world, shape_dest, radius, shape.filter)

                for info in results:
                    if info.shape.body == body: continue
                    if info.shape.sensor: continue

                    # Backface check
                    if info.normal.dot(move_delta) > 0.0001:
                         continue

                    if info.alpha < best_alpha:
                        best_alpha = info.alpha
                        best_hit = info

            if best_hit:
                # Move to hit
                md_len = move_delta.length
                safe_alpha = max(0.0, best_hit.alpha - (self.skin_width / md_len)) if md_len > 0.0001 else 0.0

                step_move = move_delta * safe_alpha
                current_pos += step_move

                # Slide Logic
                remainder = move_delta * (1.0 - safe_alpha)

                # Project remainder along the surface
                # New Velocity = Old Velocity - Normal * (Old Velocity . Normal)
                # But we must be careful of acute angles (V-traps).

                # Simple projection
                dot = remainder.dot(best_hit.normal)
                remainder = remainder - best_hit.normal * dot

                # Re-check if this new remainder is valid against previous normals?
                # In this loop, we just update move_delta and retry sweep.
                # If we are stuck in a V, the next sweep will hit the other wall immediately (alpha ~ 0).
                # Then we project against that normal.
                # If the normals oppose, remainder becomes 0.

                move_delta = remainder

                # Update velocity to reflect the slide (for next frame consistency)
                v_dot = velocity.dot(best_hit.normal)
                velocity = velocity - best_hit.normal * v_dot

            else:
                # No hit, move full distance
                current_pos += move_delta
                move_delta = pymunk.Vec2d(0, 0)
                break

        body.position = current_pos
        controller.current_velocity = velocity
