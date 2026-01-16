import math
import random
import time
import pymunk
from loguru import logger
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
    1. MoveCommand-based: AI issues MoveCommand, SteeringSystem processes it.
    2. Path-based: AI sets path in AIState, SteeringSystem follows it.
    """

    def update(self, world: World, dt: float) -> None:
        physics_system = world.services.try_get(PhysicsSystem)
        space = getattr(physics_system, "space", None) if physics_system else None
        current_time = time.time()

        # --- Phase A: Process MoveCommand-based steering ---
        # This is the new decoupled architecture from Proposal 4
        move_cmd_entities = world.get_components_tuple(
            Transform, MovementController, SteeringComponent, PhysicsBody, MoveCommand
        )

        for entity_id, (trans, movement, steering, phys, move_cmd) in move_cmd_entities:
            # Check expiration
            if move_cmd.expiration > 0 and current_time > move_cmd.expiration:
                world.remove_component(entity_id, MoveCommand)
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            current_pos = pymunk.Vec2d(trans.x, trans.y)
            target_pos = pymunk.Vec2d(move_cmd.target_pos.x, move_cmd.target_pos.y)

            # If tracking an entity, update target position
            if move_cmd.target_entity_id is not None:
                target_trans = world.try_get_component(
                    move_cmd.target_entity_id, Transform
                )
                if target_trans:
                    target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
                else:
                    # Target lost, remove command
                    world.remove_component(entity_id, MoveCommand)
                    movement.target_velocity = pymunk.Vec2d(0, 0)
                    continue

            # Calculate distance
            to_target = target_pos - current_pos
            dist = to_target.length

            # Arrival check
            if dist < steering.arrival_radius:
                world.remove_component(entity_id, MoveCommand)
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            # Calculate desired velocity with speed multiplier
            max_speed = steering.max_speed * move_cmd.speed_multiplier
            desired_velocity = to_target.normalized() * max_speed

            # Apply arrival slowdown
            if dist < steering.arrival_radius * 2:
                desired_velocity *= dist / (steering.arrival_radius * 2)

            # Resolve target body for exclusion (don't avoid what we want to touch)
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
                # No path, no steering (unless other behaviors set target_velocity)
                # If we rely solely on SteeringSystem for movement, we should zero it out,
                # but valid behavior might set target_velocity manually (e.g. wander).
                # Only override if we are in a 'MOVING' state or have a path?
                # Let's assume valid path means we should steer.
                continue

            current_pos = pymunk.Vec2d(trans.x, trans.y)
            path = ai_state.path

            # 1. Path Following (Seek / Arrival)
            # Find next waypoint
            if not path:
                movement.target_velocity = pymunk.Vec2d(0, 0)
                continue

            # Pop waypoints if reached
            # First point in path is often start, or close to it.
            # We want to move to path[0] if we are not there.
            # Check distance to path[0]
            # Since path can be raw coords, assuming list of tuples or path objects.
            # NavigationService returns list[tuple[float, float]].

            target_pos = pymunk.Vec2d(*path[0])
            dist_sq = (target_pos - current_pos).length_squared

            # Waypoint reached threshold (e.g. 10px)
            # Waypoint reached threshold
            # Use looser threshold for intermediate waypoints to ensure fluid movement
            # and prevent getting stuck orbiting a specific pixel.
            # Final waypoint needs to be stricter to ensure we actually arrive.

            # Default to 30px (900 sq) for intermediate, 10px (100 sq) for final
            pop_threshold_sq = 900.0
            if len(path) == 1:
                pop_threshold_sq = 100.0

            if dist_sq < pop_threshold_sq:
                path.pop(0)
                if not path:
                    # Arrived at final destination
                    movement.target_velocity = pymunk.Vec2d(0, 0)
                    ai_state.path = None  # Clear path
                    # Maybe trigger event or state change?
                    continue
                target_pos = pymunk.Vec2d(*path[0])
                dist_sq = (target_pos - current_pos).length_squared

            # Path Smoothing: Blend direction towards next waypoint when close to current
            # This creates smoother curves instead of sharp turns at waypoints
            if len(path) > 1 and dist_sq < 2500.0:  # Within 50px of current waypoint
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

            # If tracking an entity, update the final target position to its LIVE position
            # This prevents arriving at a stale "phantom" location if the target moved while we were walking.
            if is_final_waypoint and ai_state.current_target_id != -1:
                target_phys = world.try_get_component(
                    ai_state.current_target_id, PhysicsBody
                )
                if target_phys and target_phys.body:
                    target_pos = target_phys.body.position
                    # Recalculate distance to new live target
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

                    # Time to intercept
                    # T = dist / (my_speed - target_speed_towards_me?)
                    # Simple approximation: T = dist / max_speed
                    if steering.max_speed > 0.1:
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
                # Standard Seek
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

            # Resolve target body for exclusion
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

            # Combine
            # Priority: Avoidance > Separation > Seek
            # Weights defined in component
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

            # Debug/Stuck Check logic
            # Only increment if we intend to move (have path) but are moving very slowly
            if movement.target_velocity.length_squared > 100.0:  # INTENDING to move
                if movement.current_velocity.length < 5.0:
                    steering.time_stuck += dt
                else:
                    steering.time_stuck = max(
                        0.0, steering.time_stuck - dt * 2.0
                    )  # Decay
            else:
                steering.time_stuck = 0.0

            # Stuck Resolution
            # During pursuit mode, use higher threshold and skip jitter (causes erratic chase)
            stuck_threshold_jitter = 3.0 if steering.pursuit_enabled else 1.0
            stuck_threshold_repath = 5.0 if steering.pursuit_enabled else 3.0

            if (
                steering.time_stuck > stuck_threshold_jitter
                and not steering.pursuit_enabled
            ):
                # Stage 1: Jitter (only when NOT pursuing)
                # Apply random force to try to wiggle free
                jitter = (
                    pymunk.Vec2d(
                        random.uniform(-1, 1), random.uniform(-1, 1)
                    ).normalized()
                    * steering.max_force
                )
                movement.target_velocity += jitter

            if steering.time_stuck > stuck_threshold_repath:
                # Stage 2: Force Repath
                # Clearing path will cause Behavior Tree to request new path
                logger.warning(
                    f"Entity {entity_id} stuck for {steering.time_stuck:.1f}s. Forcing repath."
                )
                ai_state.path = None
                steering.time_stuck = 0.0

    def _calculate_steering_forces(
        self,
        space: pymunk.Space | None,
        current_pos: pymunk.Vec2d,
        phys: PhysicsBody,
        movement: MovementController,
        steering: SteeringComponent,
        target_body: pymunk.Body | None = None,
        target_entity_id: int | None = None,
    ) -> tuple[pymunk.Vec2d, pymunk.Vec2d]:
        """
        Calculate separation and obstacle avoidance forces.

        Returns:
            Tuple of (separation_force, avoidance_force).
        """
        separation_force = pymunk.Vec2d(0, 0)
        avoidance_force = pymunk.Vec2d(0, 0)

        if not space:
            return separation_force, avoidance_force

        # A. Neighbor Separation
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

        # B. Whisker Avoidance (Raycasts)
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
