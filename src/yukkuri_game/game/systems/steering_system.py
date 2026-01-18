"""
Steering System - Autonomous Movement Control.

Calculates steering forces for AI-controlled entities and updates their
target velocities. Implements Reynolds-style steering behaviors including:
-   Seek/Arrival for path following.
-   Pursuit for intercept prediction.
-   Separation for crowd avoidance.
-   Whisker-based obstacle avoidance.

Processing occurs in two phases:
1.  MoveCommand-based: Direct movement orders from AI actions.
2.  Path-based: Following navigation paths from AIState.
"""

import math
from typing import Optional, Tuple
import pymunk
from loguru import logger

from ...engine import rng
from ...engine.ecs import System, World
from ..components import (
    Transform,
    MovementController,
    SteeringComponent,
    PhysicsBody,
    MoveCommand,
)
from ..yukkuri_components import AIState
from .physics import PhysicsSystem


class SteeringSystem(System):
    """
    System that calculates steering forces and updates MovementController.target_velocity.

    Supports two modes:
    1.  MoveCommand-based: AI issues MoveCommand, SteeringSystem processes it.
    2.  Path-based: AI sets path in AIState, SteeringSystem follows it.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the SteeringSystem, calculating forces and applying them.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        physics_system = world.services.try_get(PhysicsSystem)
        space = getattr(physics_system, "space", None) if physics_system else None
        current_time = world.time

        # --- Phase A: Process MoveCommand-based steering ---
        move_cmd_entities = world.get_components_tuple(
            Transform, MovementController, SteeringComponent, PhysicsBody, MoveCommand
        )

        for entity_id, (trans, movement, steering, phys, move_cmd) in move_cmd_entities:
            if move_cmd.expiration > 0 and current_time > move_cmd.expiration:
                world.remove_component(entity_id, MoveCommand)
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            current_pos = pymunk.Vec2d(trans.x, trans.y)
            target_pos = pymunk.Vec2d(move_cmd.target_pos.x, move_cmd.target_pos.y)

            # Track moving entity by updating target position each frame.
            if move_cmd.target_entity_id is not None:
                target_trans = world.try_get_component(
                    move_cmd.target_entity_id, Transform
                )
                if target_trans:
                    target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
                else:
                    world.remove_component(entity_id, MoveCommand)
                    movement.target_velocity = pymunk.Vec2d(0, 0)
                    continue

            to_target = target_pos - current_pos
            dist = to_target.length

            if dist < steering.arrival_radius:  # Close enough: stop.
                world.remove_component(entity_id, MoveCommand)
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            max_speed = steering.max_speed * move_cmd.speed_multiplier
            desired_velocity = to_target.normalized() * max_speed

            # Slow down within arrival zone for smooth stopping.
            if dist < steering.arrival_radius * 2:
                desired_velocity *= dist / (steering.arrival_radius * 2)

            # Exclude target body from avoidance so we can reach it.
            target_body = None
            if move_cmd.target_entity_id is not None:
                t_phys = world.try_get_component(move_cmd.target_entity_id, PhysicsBody)
                if t_phys:
                    target_body = t_phys.body

            # Apply separation and avoidance using shared helper
            separation_force, avoidance_force = self._calculate_steering_forces(
                space,
                current_pos,
                phys,
                movement,
                steering,
                target_body,
                move_cmd.target_entity_id,
            )

            total_force = (
                (desired_velocity * steering.seek_weight)
                + (separation_force * steering.separation_weight)
                + (avoidance_force * steering.avoidance_weight)
            )

            if total_force.length > max_speed:
                total_force = total_force.normalized() * max_speed

            movement.target_velocity = total_force

        # --- Phase B: Process Path-based steering ---
        components = world.get_components_tuple(
            Transform, MovementController, SteeringComponent, AIState, PhysicsBody
        )

        for entity_id, (trans, movement, steering, ai_state, phys) in components:
            # Skip if entity has MoveCommand (already processed above)
            if world.has_component(entity_id, MoveCommand):
                continue

            if not ai_state.path:
                # No path set - other behaviors may control velocity directly.
                continue

            current_pos = pymunk.Vec2d(trans.x, trans.y)
            path = ai_state.path

            # 1. Path Following (Seek / Arrival)
            # Find next waypoint
            if not path:
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            target_pos = pymunk.Vec2d(*path[0])
            dist_sq = (target_pos - current_pos).length_squared

            # Thresholds: 60px for intermediate waypoints, 10px for final arrival.
            pop_threshold_sq = 3600.0 if len(path) > 1 else 100.0

            if dist_sq < pop_threshold_sq:
                path.pop(0)
                if not path:
                    movement.target_velocity = pymunk.Vec2d(0, 0)
                    ai_state.path = None
                    continue
                target_pos = pymunk.Vec2d(*path[0])
                dist_sq = (target_pos - current_pos).length_squared

            # Blend towards next waypoint when close for smoother turns.
            if len(path) > 1 and dist_sq < 2500.0:  # Within 50px.
                next_waypoint = pymunk.Vec2d(*path[1])
                blend_factor = 1.0 - (
                    math.sqrt(dist_sq) / 50.0
                )  # 0 when 50px away, 1 when at waypoint
                blend_factor = max(0.0, min(1.0, blend_factor))

                # Blend target position towards next waypoint
                target_pos = target_pos * (1.0 - blend_factor * 0.5) + next_waypoint * (
                    blend_factor * 0.5
                )

            # Seek / Pursuit
            desired_velocity = pymunk.Vec2d(0, 0)

            # Check for Pursuit Mode (Intercept) OR Live Tracking
            # Only apply if targeting the FINAL waypoint (actual target) to avoid cutting corners into walls
            is_final_waypoint = len(path) == 1

            # Final waypoint + tracking entity: use live position instead of stale path endpoint.
            if is_final_waypoint and ai_state.current_target_id != -1:
                target_phys = world.try_get_component(
                    ai_state.current_target_id, PhysicsBody
                )
                if target_phys and target_phys.body:
                    target_pos = target_phys.body.position
                    dist_sq = (target_pos - current_pos).length_squared

            if (
                steering.pursuit_enabled
                and is_final_waypoint
                and ai_state.current_target_id != -1
            ):
                # Try to predict intercept (overrides live tracking with prediction)
                target_phys = world.try_get_component(
                    ai_state.current_target_id, PhysicsBody
                )
                if target_phys and target_phys.body:
                    t_vel = target_phys.body.velocity
                    to_target = target_pos - current_pos
                    dist = to_target.length

                    if dist > 0:
                        time_to_int = dist / steering.max_speed
                        predicted_pos = target_pos + t_vel * time_to_int
                        desired_velocity = (
                            predicted_pos - current_pos
                        ).normalized() * steering.max_speed
                    else:
                        desired_velocity = (
                            target_pos - current_pos
                        ).normalized() * steering.max_speed
                else:
                    desired_velocity = (
                        target_pos - current_pos
                    ).normalized() * steering.max_speed
            else:
                desired_velocity = (
                    target_pos - current_pos
                ).normalized() * steering.max_speed

            # Arrival (if last point)
            if is_final_waypoint:
                dist = math.sqrt(dist_sq)
                if dist < steering.arrival_radius:
                    if steering.arrival_radius > 0.001:
                        desired_velocity *= dist / steering.arrival_radius
                    else:
                        desired_velocity = pymunk.Vec2d(0, 0)

            # Exclude target from avoidance calculations.
            target_body = None
            if ai_state.current_target_id != -1:
                t_phys = world.try_get_component(
                    ai_state.current_target_id, PhysicsBody
                )
                if t_phys:
                    target_body = t_phys.body

            # 2. Separation & Whisker Avoidance
            separation_force, avoidance_force = self._calculate_steering_forces(
                space,
                current_pos,
                phys,
                movement,
                steering,
                target_body,
                ai_state.current_target_id,
            )

            # Weight-blend: Avoidance > Separation > Seek.
            total_force = (
                (desired_velocity * steering.seek_weight)
                + (separation_force * steering.separation_weight)
                + (avoidance_force * steering.avoidance_weight)
            )

            final_velocity = total_force

            # Clamp
            if final_velocity.length > steering.max_speed:
                final_velocity = final_velocity.normalized() * steering.max_speed

            movement.target_velocity = final_velocity

            # --- Stuck Detection ---
            # Triggers when target velocity is high but actual velocity is low.
            if movement.target_velocity.length_squared > 100.0:
                if movement.current_velocity.length < 5.0:
                    steering.time_stuck += dt
                else:
                    # Decay stuck timer when moving (2x rate for quick recovery)
                    steering.time_stuck = max(0.0, steering.time_stuck - dt * 2.0)
            else:
                steering.time_stuck = 0.0

            # --- Stuck Resolution ---
            # Two-tier resolution: jitter first, then skip waypoints or force repath.
            stuck_threshold_jitter = 3.0 if steering.pursuit_enabled else 1.0
            stuck_threshold_repath = 5.0 if steering.pursuit_enabled else 3.0

            # Stage 1: Apply random jitter to wiggle free.
            if (
                steering.time_stuck > stuck_threshold_jitter
                and not steering.pursuit_enabled
            ):
                jitter = (
                    pymunk.Vec2d(rng.uniform(-1, 1), rng.uniform(-1, 1)).normalized()
                    * steering.max_force
                )
                movement.target_velocity += jitter

            # Stage 2: Skip nearby waypoint or force complete repath.
            if steering.time_stuck > stuck_threshold_repath:
                is_stuck_close = False
                # Check if stuck near current waypoint (within 150px).
                if len(path) > 1:
                    raw_dist_sq = (pymunk.Vec2d(*path[0]) - current_pos).length_squared
                    if raw_dist_sq < 22500.0:
                        is_stuck_close = True

                if is_stuck_close:
                    # Skip intermediate waypoint if close enough
                    logger.warning(f"Entity {entity_id} stuck near waypoint. Skipping.")
                    path.pop(0)
                    steering.time_stuck = 0.0
                else:
                    # Force complete repath via Behavior Tree
                    logger.warning(
                        f"Entity {entity_id} stuck for {steering.time_stuck:.1f}s. Forcing repath."
                    )
                    ai_state.path = None
                    steering.time_stuck = 0.0

    def _calculate_steering_forces(
        self,
        space: Optional[pymunk.Space],
        current_pos: pymunk.Vec2d,
        phys: PhysicsBody,
        movement: MovementController,
        steering: SteeringComponent,
        target_body: Optional[pymunk.Body] = None,
        target_entity_id: Optional[int] = None,
    ) -> Tuple[pymunk.Vec2d, pymunk.Vec2d]:
        """
        Calculates separation and obstacle avoidance steering forces.

        Separation uses point queries to detect nearby entities and pushes
        away proportionally to distance. Avoidance uses three whisker raycasts
        (forward, +30°, -30°) to detect obstacles ahead.

        Args:
            space (Optional[pymunk.Space]): Pymunk physics space for queries.
            current_pos (pymunk.Vec2d): Entity's current position.
            phys (PhysicsBody): Entity's physics body (for self-exclusion).
            movement (MovementController): Movement controller with current velocity.
            steering (SteeringComponent): Steering parameters (radii, weights).
            target_body (Optional[pymunk.Body]): Optional body to exclude from avoidance.
            target_entity_id (Optional[int]): Optional entity ID to exclude.

        Returns:
            Tuple[pymunk.Vec2d, pymunk.Vec2d]: Tube of (separation_force, avoidance_force) vectors.
        """
        separation_force = pymunk.Vec2d(0, 0)
        avoidance_force = pymunk.Vec2d(0, 0)

        if not space:
            return separation_force, avoidance_force

        # Neighbor Separation
        # Query all physics bodies within separation radius (50px)
        neighbor_radius = 50.0
        query_info = space.point_query(
            current_pos, neighbor_radius, pymunk.ShapeFilter()
        )

        count = 0
        for info in query_info:
            if info.shape.body == phys.body:
                continue

            # Check Body exclusion
            if target_body and info.shape.body == target_body:
                continue

            # Check ID exclusion (via group)
            if (
                target_entity_id is not None
                and info.shape.filter.group == target_entity_id
            ):
                continue

            if info.shape.sensor:
                continue

            diff = current_pos - info.point
            dist_sep = diff.length
            if dist_sep > 0.001:
                separation_force += diff.normalized() / dist_sep
                count += 1

        if count > 0:
            separation_force = separation_force.normalized() * steering.max_speed

        # Whisker Avoidance (Raycasts)
        if movement.target_velocity.length > 10.0:
            look_dir = movement.target_velocity.normalized()
            whisker_len = 50.0
            filter_ = pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS())

            rays = [
                look_dir,
                look_dir.rotated(math.radians(30)),
                look_dir.rotated(math.radians(-30)),
            ]

            for ray_dir in rays:
                end = current_pos + ray_dir * whisker_len
                hit = space.segment_query_first(current_pos, end, 1.0, filter_)

                if (
                    hit
                    and hit.shape
                    and hit.shape.body != phys.body
                    and not hit.shape.sensor
                ):
                    # Also ignore target for avoidance? likely yes, we want to hit it (collide/interact)
                    # Unless it's an obstacle we arepathing around...
                    # But MoveToTarget usually means we want to touch it.
                    if target_body and hit.shape.body == target_body:
                        continue

                    if (
                        target_entity_id is not None
                        and hit.shape.filter.group == target_entity_id
                    ):
                        continue

                    avoidance_force += hit.normal * steering.max_speed

        return separation_force, avoidance_force
