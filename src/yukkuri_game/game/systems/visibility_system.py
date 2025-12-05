"""
Module defining the Visibility System.
"""

import math
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ...engine.ecs import System, World
from ..components import Transform, PhysicsBody
from ..systems.physics import PhysicsSystem
from ..collision_constants import CollisionCategories

class VisibilitySystem(System):
    """
    Determines visibility between entities using the Pymunk geometry database.
    """

    def __init__(self):
        super().__init__()
        self.physics_system = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates visibility status.
        Currently, this might just be a service-like system that others query,
        or it could update a 'VisibleEntities' component.

        For now, it provides the `is_visible` method which can be used by AI.
        """
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)

    def is_visible(self, observer_id: int, target_id: int, world: World, range_limit: float = 500.0, fov: float = 360.0) -> bool:
        """
        Checks if target is visible to observer.

        Args:
            observer_id: Entity ID of the observer.
            target_id: Entity ID of the target.
            world: ECS World.
            range_limit: Maximum vision range.
            fov: Field of view in degrees.

        Returns:
            bool: True if visible.
        """
        if not self.physics_system:
             # Fallback if physics not ready
            return False

        obs_trans = world.get_component(observer_id, Transform)
        target_trans = world.get_component(target_id, Transform)

        if not obs_trans or not target_trans:
            return False

        # 1. Distance Check
        dx = target_trans.x - obs_trans.x
        dy = target_trans.y - obs_trans.y
        dist_sq = dx*dx + dy*dy

        if dist_sq > range_limit * range_limit:
            return False

        # 2. Angle Check (FOV)
        if fov < 360.0:
            obs_phys = world.get_component(observer_id, PhysicsBody)
            if obs_phys:
                # Get observer forward vector based on angle
                # Pymunk angle is in radians
                angle = obs_phys.body.angle
                forward = Vector2(math.cos(angle), math.sin(angle))

                target_vec = Vector2(dx, dy)
                if target_vec.length_sq > 0:
                    target_dir = target_vec.normalized()

                    # Dot product
                    dot = forward.dot(target_dir)

                    # Convert FOV to radians and check half angle
                    # FOV is total angle, so we compare against cos(fov/2)
                    fov_rad = math.radians(fov)
                    min_dot = math.cos(fov_rad / 2.0)

                    if dot < min_dot:
                        return False

        # 3. Raycast (Geometry Check)
        space = self.physics_system.space
        start = (obs_trans.x, obs_trans.y)
        end = (target_trans.x, target_trans.y)

        # Filter: Blocked by Walls.
        mask = CollisionCategories.WALL

        # Raycast
        # If mask is 0, we assume it's unset in tests, so use ALL?
        # But in game constant is WALL = 0b0100.

        # If the raycast hits ANYTHING that matches the mask, it blocks.

        filter_ = pymunk.ShapeFilter(mask=mask)

        # segment_query_first finds the first hit.
        hit = space.segment_query_first(start, end, 1.0, filter_)

        if hit and not hit.shape.sensor:
            return False

        return True
