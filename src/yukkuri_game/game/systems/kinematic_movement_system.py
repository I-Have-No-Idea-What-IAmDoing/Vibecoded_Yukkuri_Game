"""
Kinematic Movement System - Deterministic Character Controller.

Implements a robust Sweep-and-Slide algorithm for collision resolution,
providing deterministic movement suitable for networked games and replays.

Algorithm Overview:
1.  **Depenetration Pass**: Resolve any existing overlaps before movement.
2.  **Virtual Physics**: Integrate velocity based on input (acceleration/friction).
3.  **Sweep Pass**: Cast shape along movement vector to detect collisions.
4.  **Slide Resolution**: Project remaining velocity along collision surface.
5.  **Multi-Plane Handling**: Supports corner resolution (prevents V-corner sticking).

Performance Optimizations:
-   Stationary entities skip sweep logic entirely.
-   Polygon radius caching avoids repeated circumscribed circle calculations.
-   Fallback overlap check only triggers when sweep query misses edge cases.

Flight Integration:
-   Flying entities dynamically update collision filters based on altitude.
-   Ground units collide with LOW_OBSTACLE, flying units only with HIGH_OBSTACLE.
-   Swooping state enables ground unit collision for attack passes.

Fixed Timestep:
-   Movement runs via PhysicsFixedUpdateEvent for determinism.
-   Decoupled from render framerate for consistent physics behavior.
"""

import math
from typing import TYPE_CHECKING

import pymunk
from loguru import logger

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import PhysicsFixedUpdateEvent
from ..collision_constants import CollisionCategories
from ..components import MovementController, PhysicsBody, Transform
from ..skill_service import SkillService
from ..yukkuri_components import Flight, FlightState, YukkuriStats
from .physics import PhysicsSystem

if TYPE_CHECKING:
    pass


class FakeHit:
    """Synthetic hit result for fallback overlap detection."""

    def __init__(self, normal: pymunk.Vec2d, alpha: float) -> None:
        self.normal = normal
        self.alpha = alpha


class KinematicMovementSystem(System):
    """
    Moves kinematic bodies using sweep-and-slide against world geometry.

    Features:
    -   Capsule/circle sweeping (no bounding box approximation).
    -   Multi-plane slide resolution for corners.
    -   Pre-step depenetration fallback.
    -   Composite shape support (stacked entities).

    Attributes:
        space (pymunk.Space | None): Physics space reference.
        skin_width (float): Collision skin width.
        event_bus (EventBus | None): EventBus reference.
        _kinematic_world (World | None): World reference for fixed updates.
        _poly_radius_cache (dict[pymunk.Poly, float]): Cache for polygon radii.
        skill_service (SkillService | None): SkillService reference.
    """

    def __init__(self) -> None:
        """Initializes the KinematicMovementSystem."""
        self.space: pymunk.Space | None = None
        self.skin_width = 0.01  # Collision skin to prevent surface penetration
        self.event_bus: EventBus | None = None
        self._kinematic_world: "World | None" = None
        self._poly_radius_cache: dict[pymunk.Poly, float] = {}
        self.skill_service: SkillService | None = None

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent) -> None:
        """
        Handles PhysicsFixedUpdateEvent to run deterministic physics.

        Args:
            event (PhysicsFixedUpdateEvent): The fixed update event.
        """
        if not self.space:
            return

        if self._kinematic_world:
            self.fixed_update(self._kinematic_world, event.dt)
        else:
            logger.warning(
                "KinematicMovementSystem: Fixed update skipped because world is not initialized."
            )

    def update(self, world: "World", dt: float) -> None:
        """
        Updates the system, initializing services on first run.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
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

        self.skill_service = world.services.try_get(SkillService)
        self._kinematic_world = world

    def fixed_update(self, world: "World", dt: float) -> None:
        """
        Runs the deterministic movement logic.

        Args:
            world (World): The ECS World.
            dt (float): Fixed delta time.
        """
        components = world.get_components_tuple(
            PhysicsBody, MovementController, Transform
        )

        # Lazy import to avoid circular dependency
        from ..skill_constants import SkillId

        for entity, (phys, controller, trans) in components:
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Sync Transform to Body
            start_pos = phys.body.position

            # Stationary entities skip sweep logic entirely.
            target_vel_sq = controller.target_velocity.length_squared
            current_vel_sq = controller.current_velocity.length_squared
            if target_vel_sq < 0.0001 and current_vel_sq < 0.0001:
                trans.prev_x = start_pos.x
                trans.prev_y = start_pos.y
                trans.x = start_pos.x
                trans.y = start_pos.y
                continue

            # Resolve any existing overlaps before movement.
            clean_pos = self.resolve_penetration(phys, start_pos)
            if clean_pos != start_pos:
                phys.body.position = clean_pos
                start_pos = clean_pos

            trans.prev_x = start_pos.x
            trans.prev_y = start_pos.y

            # Flight Collision Filter Update
            flight = world.try_get_component(entity, Flight)
            if flight:
                self._update_flight_collision_filter(phys, flight)

            stats = world.try_get_component(entity, YukkuriStats)
            agility = stats.agility if stats else 1.0

            dist_moved = self.move_and_slide(phys, controller, trans, dt, agility)

            # Award athletics XP based on distance traveled.
            if dist_moved > 0.1 and self.skill_service:
                self.skill_service.add_xp(entity, SkillId.ATHLETICS, dist_moved * 0.01)

            # Sync Transform back
            trans.x = phys.body.position.x
            trans.y = phys.body.position.y

    def resolve_penetration(self, phys: PhysicsBody, pos: pymunk.Vec2d) -> pymunk.Vec2d:
        """
        Checks if the body is currently overlapping static geometry and pushes it out.

        This is a fallback mechanism. A perfect sweep system shouldn't need this often.

        Args:
            phys (PhysicsBody): The entity's physics body.
            pos (pymunk.Vec2d): The current position.

        Returns:
            pymunk.Vec2d: The resolved position.
        """
        current_pos = pos
        max_iterations = 3  # Multiple passes handle complex corner overlaps.

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
                    if info.shape.body == phys.body or info.shape.sensor:
                        continue

                    if info.shape.sensor:
                        continue

                    contact_set = info.contact_point_set
                    if len(contact_set.points) == 0:
                        continue

                    best_push = pymunk.Vec2d(0, 0)

                    for point in contact_set.points:
                        if point.distance < -0.001:
                            # Pymunk's normal points A->B, so we push A away via -Normal * Distance.
                            push = contact_set.normal * (point.distance)

                            if push.length_squared > best_push.length_squared:
                                best_push = push

                    if best_push.length_squared > 0:
                        total_push += best_push
                        hits += 1

            if hits > 0:
                if total_push.length_squared < 0.000001:
                    break
                current_pos += total_push  # Accumulate all pushes.
            else:
                break

        phys.body.position = pos  # Restore
        return current_pos

    def _get_poly_radius(self, shape: pymunk.Poly) -> float:
        """Returns the circumscribed radius of a polygon shape. Cached for performance."""
        if shape in self._poly_radius_cache:
            return self._poly_radius_cache[shape]

        verts = shape.get_vertices()
        sweep_origin_local = getattr(shape, "offset", pymunk.Vec2d(0, 0))

        max_sq = 0.0
        for v in verts:
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
        agility: float = 1.0,
    ) -> float:
        """
        Executes the sweep-and-slide movement algorithm.

        Args:
            phys (PhysicsBody): The entity's physics body.
            controller (MovementController): The movement controller component.
            trans (Transform): The entity's transform component.
            dt (float): Fixed delta time.
            agility (float): Agility multiplier.

        Returns:
            float: The distance actually moved.
        """
        body = phys.body
        start_pos = body.position

        # 1. Virtual Physics Integration
        input_vector = controller.target_velocity
        velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            friction = controller.friction
            damping = max(0.0, 1.0 - friction * dt)
            velocity = velocity * damping
            if (
                velocity.length_squared < 0.0001
            ):  # Snap to zero to prevent micro-sliding.
                velocity = pymunk.Vec2d(0, 0)
        else:
            diff = input_vector - velocity
            change = controller.acceleration * agility * dt
            if change >= diff.length:
                velocity = input_vector
            else:
                velocity += diff.normalized() * change

        controller.current_velocity = velocity

        # 2. Sweep Movement
        move_delta = velocity * dt
        if move_delta.length_squared < 0.000001:
            return 0.0

        current_pos = body.position

        # Rigorous Slide Logic
        max_slides = 5

        for i in range(max_slides):
            if move_delta.length_squared < 0.000001:
                break

            # Pymunk does not support sweeping circles natively with segment query in the same way for all shapes,
            # but we approximate or use the shape's specific sweep if possible.
            # Here we are iterating shapes and checking segment queries.

            target_pos = current_pos + move_delta

            # Perform Sweep for ALL shapes in the body
            best_hit: pymunk.SegmentQueryInfo | FakeHit | None = None
            best_alpha = 1.0

            for shape in body.shapes:
                if shape.sensor:
                    continue

                radius = 0.0
                if hasattr(shape, "radius") and shape.radius > 0:
                    radius = shape.radius
                elif isinstance(shape, pymunk.Poly):
                    radius = self._get_poly_radius(shape)

                # Calculate shape offset for sweep origin.
                shape_offset = getattr(shape, "offset", pymunk.Vec2d(0, 0))
                rotated_offset = shape_offset.rotated(body.angle)
                shape_center_world = current_pos + rotated_offset
                shape_dest = shape_center_world + move_delta

                if not self.space:
                    return 0.0

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

                    if info.alpha < best_alpha:  # Record closest hit.
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
                    best_alpha = 0.0
                    best_hit = FakeHit(fallback_normal, 0.0)

            if best_hit:
                md_len = move_delta.length
                safe_alpha = (
                    max(0.0, best_hit.alpha - (self.skin_width / md_len))
                    if md_len > 0.0001
                    else 0.0
                )

                step_move = move_delta * safe_alpha
                current_pos += step_move

                # Project remaining movement onto slide plane.
                remainder = move_delta * (1.0 - safe_alpha)
                dot = remainder.dot(best_hit.normal)
                remainder = remainder - best_hit.normal * dot

                move_delta = remainder

                # Project velocity to prevent next frame from pushing into wall.
                v_dot = velocity.dot(best_hit.normal)
                velocity = velocity - best_hit.normal * v_dot

            else:
                current_pos += move_delta
                move_delta = pymunk.Vec2d(0, 0)
                break

        body.position = current_pos
        controller.current_velocity = velocity

        return (body.position - start_pos).length

    def _update_flight_collision_filter(
        self, phys: PhysicsBody, flight: Flight
    ) -> None:
        """
        Updates the collision filter on all shapes of the physics body based on flight state.

        - GROUNDED/LANDING/TAKEOFF (low altitude): Collide with ground units, low obstacles, high obstacles, water.
        - FLYING/HOVERING (high altitude): Only collide with flying units and high obstacles.
        - SWOOPING (attack descent): Collide with ground units, low obstacles, high obstacles.

        Args:
            phys (PhysicsBody): The entity's physics body.
            flight (Flight): The flight component.
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
