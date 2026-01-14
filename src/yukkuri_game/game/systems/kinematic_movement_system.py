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
from ..collision_constants import CollisionCategories
from ..yukkuri_components import Flight, FlightState
from .physics import PhysicsSystem


class FakeHit:
    """Helper class to simulate a collision hit result."""

    def __init__(self, normal: pymunk.Vec2d, alpha: float) -> None:
        self.normal = normal
        self.alpha = alpha


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

    def __init__(self) -> None:
        self.space: pymunk.Space | None = None
        self.skin_width = 0.01
        self.event_bus: EventBus | None = None
        # Type hint must match System base class or handle the temporary None safely.
        # However, System defines self.world as World, so overriding with World | None is incompatible.
        # We should use a separate attribute or assume it's set before update.
        # But for now, we can use 'Any' or suppress, OR initialize it properly.
        # Let's use 'Any' for now to silence the incompatibility, or just type it as 'World' and initialize with cast(World, None) if we really have to.
        # Better: use a separate attribute for local storage like `self._world` if we need to store it,
        # but `update` method receives it anyway.
        # The error "Incompatible types in assignment" is because `System` likely annotations `world` (if it does).
        # Checking `ecs.py`... System doesn't seem to annotate `self.world` in __init__.
        # Ah, maybe it does in `System` class definition: `self.world: World`?
        # In `src/yukkuri_game/engine/ecs.py`, System might have `world` attribute.
        # Let's fix by removing `self.ecs_world` line 42 and just using `self.world` from base class if available,
        # or defining logic to handle "not initialized".
        # But `fixed_update` needs it.
        # Let's use `cast` to `World` when assigning `None` initially to satisfy mypy,
        # or just type it as `self.ecs_world: World | None` and ignore the error if it conflicts with a base class attribute of same name.
        # But `ecs_world` is a new attribute name, so it shouldn't conflict unless `System` has `ecs_world`.
        # Wait, the error was: `src/yukkuri_game/game/systems/kinematic_movement_system.py:42: error: Incompatible types in assignment (expression has type "World | None", base class "System" defined the type as "World")`
        # This implies `System` has `ecs_world`? Or I am misreading.
        # Maybe I renamed `world` to `ecs_world`?
        # Let's check `ecs.py` content I saw earlier. `System` class usually has `update(self, world, dt)`.
        # It doesn't usually store `world`.
        # Wait, line 42 in `kinematic` is `self.ecs_world: World | None = None`.
        # Maybe I added `ecs_world` to `System`?
        # Or maybe the error refers to `self.ecs_world = world` in `update`?
        # Let's just fix the assignment.
        self._kinematic_world: World | None = None
        self._poly_radius_cache: dict[pymunk.Poly, float] = {}

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent) -> None:
        if not self.space:
            return

        # Ensure we have the world. If ecs_world is None, we can't update.
        # Ensure we have the world. If _kinematic_world is None, we can't update.
        if self._kinematic_world:
            self.fixed_update(self._kinematic_world, event.dt)
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
                self._kinematic_world = world

        self._kinematic_world = world

    def fixed_update(self, world: World, dt: float) -> None:
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

            # --- Performance Optimization: Skip stationary entities ---
            # If both target velocity and current velocity are near-zero,
            # skip the expensive sweep logic entirely.
            target_vel_sq = controller.target_velocity.length_squared
            current_vel_sq = controller.current_velocity.length_squared
            if target_vel_sq < 0.0001 and current_vel_sq < 0.0001:
                # Entity is stationary, just sync transform and skip
                trans.prev_x = start_pos.x
                trans.prev_y = start_pos.y
                trans.x = start_pos.x
                trans.y = start_pos.y
                continue

            # 1. Depenetration (Fallback)
            clean_pos = self.resolve_penetration(phys, start_pos)
            if clean_pos != start_pos:
                phys.body.position = clean_pos
                start_pos = clean_pos

            trans.prev_x = start_pos.x
            trans.prev_y = start_pos.y

            # --- Flight Collision Filter Update ---
            flight = world.try_get_component(entity, Flight)
            if flight:
                self._update_flight_collision_filter(phys, flight)

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
            if phys.body.space:
                phys.body.space.reindex_shapes_for_body(phys.body)

            total_push = pymunk.Vec2d(0, 0)
            hits = 0

            if not self.space:
                break

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
                            # We accumulate the push vector to resolve multiple overlaps simultaneously.

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
        max_sq = 0.0
        for v in verts:
            # Vec2d doesn't have get_dist_sq, use (v - other).length_squared
            d_sq = (v - sweep_origin_local).length_squared
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
    ) -> None:
        body = phys.body

        # 1. Virtual Physics Integration
        input_vector = controller.target_velocity
        velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            friction = controller.friction
            # Apply damping to simulate friction when no input is given.
            damping = max(0.0, 1.0 - friction * dt)
            velocity = velocity * damping
            # Snap to zero if velocity is very low to prevent micro-sliding.
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

                if not self.space:
                    return

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
                if not self.space:
                    break

                body.position = target_pos
                self.space.reindex_shapes_for_body(body)

                found_overlap = False
                fallback_normal = pymunk.Vec2d(0, 0)

                for shape in body.shapes:
                    if shape.sensor:
                        continue

                    if not self.space:
                        continue
                    infos = self.space.shape_query(shape)
                    for info in infos:
                        if info.shape.body == body or info.shape.sensor:
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
                    if found_overlap:
                        break

                # Restore body
                body.position = original_pos
                if self.space:
                    self.space.reindex_shapes_for_body(body)

                if found_overlap:
                    # Simulate a hit at alpha=0
                    # Simulate a hit at alpha=0
                    best_alpha = 0.0
                    # Use typing.cast or similar if necessary, or ensure FakeHit matches protocol
                    # Assuming FakeHit is sufficient for duck typing if we ignore type checker here or make it comply
                    best_hit = pymunk.SegmentQueryInfo(
                        None, fallback_normal, pymunk.Vec2d(0, 0), 0.0
                    )  # type: ignore[arg-type]

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
                # Calculate the remaining movement after the collision.
                remainder = move_delta * (1.0 - safe_alpha)

                # Project the remainder onto the slide plane (remove component along the normal).
                dot = remainder.dot(best_hit.normal)
                remainder = remainder - best_hit.normal * dot

                move_delta = remainder

                # Also project velocity so subsequent frames don't push into the wall.
                v_dot = velocity.dot(best_hit.normal)
                velocity = velocity - best_hit.normal * v_dot

            else:
                # No hit, move full distance
                current_pos += move_delta
                move_delta = pymunk.Vec2d(0, 0)
                break

        body.position = current_pos
        controller.current_velocity = velocity

    def _update_flight_collision_filter(
        self, phys: PhysicsBody, flight: Flight
    ) -> None:
        """
        Updates the collision filter on all shapes of the physics body based on flight state.

        - GROUNDED/LANDING/TAKEOFF (low altitude): Collide with ground units, low obstacles, high obstacles, water.
        - FLYING/HOVERING (high altitude): Only collide with flying units and high obstacles.
        - SWOOPING (attack descent): Collide with ground units, low obstacles, high obstacles.
        """
        CC = CollisionCategories

        if flight.state in (FlightState.FLYING, FlightState.HOVERING):
            # High altitude: ignore ground units and low obstacles
            new_categories = CC.FLYING_UNIT
            new_mask = CC.FLYING_UNIT | CC.HIGH_OBSTACLE
        elif flight.state == FlightState.SWOOPING:
            # Swooping: can hit ground units but still ignores low obstacles for attack
            new_categories = CC.FLYING_UNIT
            new_mask = (
                CC.GROUND_UNIT | CC.FLYING_UNIT | CC.HIGH_OBSTACLE | CC.LOW_OBSTACLE
            )
        else:
            # GROUNDED, LANDING, TAKEOFF, FALLING: normal ground collision
            new_categories = CC.GROUND_UNIT
            new_mask = (
                CC.GROUND_UNIT | CC.LOW_OBSTACLE | CC.HIGH_OBSTACLE | CC.WATER | CC.ITEM
            )

        for shape in phys.body.shapes:
            if shape.sensor:
                continue
            # Preserve the group (for self-collision avoidance if used)
            current_filter = shape.filter
            shape.filter = pymunk.ShapeFilter(
                group=current_filter.group,
                categories=new_categories,
                mask=new_mask,
            )
