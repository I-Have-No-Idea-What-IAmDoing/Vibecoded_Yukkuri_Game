import math
import random
import pymunk
from loguru import logger
from ...engine.ecs import System, World
from ..components import Transform, MovementController, SteeringComponent, PhysicsBody
from ..yukkuri_components import AIState
from .physics import PhysicsSystem


class SteeringSystem(System):
    """
    System that calculates steering forces and updates MovementController.target_velocity.
    """

    def update(self, world: World, dt: float) -> None:
        components = world.get_components_tuple(
            Transform, MovementController, SteeringComponent, AIState, PhysicsBody
        )

        # Build spatial index for separation (or just use physics space query?)
        # For simple separation, we can query the physics space for neighbors.
        physics_system = world.services.try_get(PhysicsSystem)  # Or however we get it
        space = getattr(physics_system, "space", None) if physics_system else None

        # Or we can just iterate O(N^2) for now if N is small? 50 entities is small.
        # But let's verify if we can access other entities easily.
        # We will use Physics Space for neighbor query.

        for entity_id, (trans, movement, steering, ai_state, phys) in components:
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
            if dist_sq < 100.0:  # 10*10
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
                blend_factor = 1.0 - (math.sqrt(dist_sq) / 50.0)  # 0 when 50px away, 1 when at waypoint
                blend_factor = max(0.0, min(1.0, blend_factor))
                
                # Blend target position towards next waypoint
                target_pos = target_pos * (1.0 - blend_factor * 0.5) + next_waypoint * (blend_factor * 0.5)

            # Seek / Pursuit
            desired_velocity = pymunk.Vec2d(0, 0)
            
            # Check for Pursuit Mode (Intercept)
            # Only apply if targeting the FINAL waypoint (actual target) to avoid cutting corners into walls
            is_final_waypoint = (len(path) == 1)
            
            if steering.pursuit_enabled and is_final_waypoint and ai_state.current_target_id != -1:
                # Try to predict intercept
                target_phys = world.try_get_component(ai_state.current_target_id, PhysicsBody)
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
                        desired_velocity = (predicted_pos - current_pos).normalized() * steering.max_speed
                    else:
                         desired_velocity = (target_pos - current_pos).normalized() * steering.max_speed
                else:
                    desired_velocity = (target_pos - current_pos).normalized() * steering.max_speed
            else:
                # Standard Seek
                desired_velocity = (target_pos - current_pos).normalized() * steering.max_speed

            # Arrival (if last point)
            if is_final_waypoint:
                dist = math.sqrt(dist_sq)
                if dist < steering.arrival_radius:
                    if steering.arrival_radius > 0.001:
                        desired_velocity *= dist / steering.arrival_radius
                    else:
                        desired_velocity = pymunk.Vec2d(0, 0)

            # 2. Separation & Whisker Avoidance
            separation_force = pymunk.Vec2d(0, 0)
            avoidance_force = pymunk.Vec2d(0, 0)

            if space:
                # A. Neighbor Separation
                neighbor_radius = 50.0
                query_info = space.point_query(
                    current_pos, neighbor_radius, pymunk.ShapeFilter()
                )

                count = 0
                for info in query_info:
                    if info.shape.body == phys.body:
                        continue
                    if info.shape.sensor:
                        continue

                    diff = current_pos - info.point
                    dist_sep = diff.length
                    if dist_sep > 0.001:
                        separation_force += diff.normalized() / dist_sep
                        count += 1

                if count > 0:
                    separation_force = (
                        separation_force.normalized() * steering.max_speed
                    )

                # B. Whisker Avoidance (Raycasts)
                # Cast rays in direction of movement
                if movement.target_velocity.length > 10.0:
                    look_dir = movement.target_velocity.normalized()
                    whisker_len = 50.0
                    
                    # 3 Whiskers: Center, Left (30deg), Right (30deg)
                    # We need to detect Obstacles (Static)
                    # Assuming Obstacles are in a different group or we filter?
                    # For now, collide with anything that is not me and not a sensor.
                    
                    filter_ = pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS()) 
                    # Ideally mask out other characters to avoid avoidance jitter, but characters block path so maybe ok.
                    # Best to filter for STATIC obstacles (Environment).
                    # We don't have easy category access here, assuming default.
                    
                    rays = [
                        look_dir,
                        look_dir.rotated(math.radians(30)),
                        look_dir.rotated(math.radians(-30))
                    ]
                    
                    for ray_dir in rays:
                        end = current_pos + ray_dir * whisker_len
                        # segment_query_first to find closest hit
                        hit = space.segment_query_first(current_pos, end, 1.0, filter_)
                        
                        if hit and hit.shape and hit.shape.body != phys.body and not hit.shape.sensor:
                            # Avoid!
                            # Force is perpendicular to normal? Or just away from hit?
                            # Standard: Normal * Overlap?
                            # Simple: Reflect velocity? 
                            # Better: Steering force = Normal * MaxSpeed
                            avoidance_force += hit.normal * steering.max_speed
            
            # Combine
            # Priority: Avoidance > Separation > Seek
            # Weights defined in component
            total_force = (desired_velocity * steering.seek_weight) + \
                          (separation_force * steering.separation_weight) + \
                          (avoidance_force * steering.avoidance_weight)
            
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
            
            if steering.time_stuck > stuck_threshold_jitter and not steering.pursuit_enabled:
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
