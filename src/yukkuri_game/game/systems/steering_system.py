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

            # Seek
            desired_velocity = (
                target_pos - current_pos
            ).normalized() * steering.max_speed

            # Arrival (if last point)
            if len(path) == 1:
                dist = math.sqrt(dist_sq)
                if dist < steering.arrival_radius:
                    desired_velocity *= dist / steering.arrival_radius

            # 2. Separation
            separation_force = pymunk.Vec2d(0, 0)
            if space:
                # Query neighbors within radius
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

                    # Vector away from neighbor
                    # info.point is the close point on surface? No, point_query returns info about shapes near point.
                    # info.point is usually the point checked?
                    # point_query_nearest returns nearest point. point_query returns all shapes containing point?
                    # No, space.point_query returns all shapes within max_distance of point.
                    # info.point is "The closest point on the shape to the query point."

                    diff = current_pos - info.point  # vector FROM neighbor TO me
                    dist_sep = diff.length
                    if dist_sep > 0.001:
                        # normalize() / dist -> 1/dist
                        separation_force += diff.normalized() / dist_sep
                        count += 1

                if count > 0:
                    separation_force = (
                        separation_force.normalized() * steering.max_speed
                    )

            # Combine
            final_velocity = (desired_velocity * steering.seek_weight) + (
                separation_force * steering.separation_weight
            )

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
            if steering.time_stuck > 1.0:
                # Stage 1: Jitter
                # Apply random force to try to wiggle free
                jitter = (
                    pymunk.Vec2d(
                        random.uniform(-1, 1), random.uniform(-1, 1)
                    ).normalized()
                    * steering.max_force
                )
                movement.target_velocity += jitter

            if steering.time_stuck > 3.0:
                # Stage 2: Force Repath
                # Clearing path will cause Behavior Tree to request new path
                logger.warning(
                    f"Entity {entity_id} stuck for {steering.time_stuck:.1f}s. Forcing repath."
                )
                ai_state.path = None
                steering.time_stuck = 0.0
