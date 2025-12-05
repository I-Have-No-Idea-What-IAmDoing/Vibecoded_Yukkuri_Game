"""
Visibility System.
"""
import pymunk
import math
from loguru import logger
from ...engine.ecs import System, World
from ..components import Vision, Transform, PhysicsBody
from ..yukkuri_components import AIState
from .physics import PhysicsSystem
from ..collision_constants import CollisionCategories

class VisibilitySystem(System):
    """
    Calculates visibility using raycasting and caching.
    """

    def __init__(self):
        self.space = None
        self.update_index = 0
        self.batch_size = 0.2  # Process 20% of entities per frame

    def update(self, world: World, dt: float) -> None:
        if not self.space:
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                self.space = physics_system.space
            else:
                return

        # Get all observers (Entities with Vision and AIState)
        observers_list = list(world.get_components_tuple(Vision, Transform, AIState))
        total_obs = len(observers_list)

        if total_obs == 0:
            return

        count = max(1, int(total_obs * self.batch_size))

        # Determine range of indices to process this frame
        start = self.update_index

        batch_indices = []
        for i in range(count):
            batch_indices.append((start + i) % total_obs)

        self.update_index = (start + count) % total_obs

        # Potential Targets: All entities with PhysicsBody
        # We cache this list once per frame (it's fast enough)
        targets = list(world.get_components_tuple(PhysicsBody, Transform))

        for idx in batch_indices:
            ent, (vision, trans, ai) = observers_list[idx]
            self.update_visibility(ent, vision, trans, ai, targets, world)

    def update_visibility(self, entity, vision, trans, ai, targets, world):
        visible = set()
        logger.trace(f"Updating visibility for entity {entity}")

        obs_pos = pymunk.Vec2d(trans.x, trans.y)
        range_sq = vision.range * vision.range

        # Try to get rotation from PhysicsBody if available
        phys_comp = world.get_component(entity, PhysicsBody)
        obs_angle = phys_comp.body.angle if phys_comp else 0.0

        # FOV vectors
        obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)
        fov_cos = math.cos(math.radians(vision.fov / 2.0))

        # Vision Blocker Mask: Walls and Yukkuris (Units)
        # We want to know if the ray hits a WALL or another UNIT before hitting the TARGET.
        # But wait, if the ray hits the TARGET first, it's visible.
        # So we query against EVERYTHING that blocks vision (Walls + Units).

        vision_mask = CollisionCategories.WALL | CollisionCategories.YUKKURI
        vision_filter = pymunk.ShapeFilter(mask=vision_mask)

        for target_ent, (target_phys, target_trans) in targets:
            if entity == target_ent:
                continue

            target_pos = target_phys.body.position
            diff = target_pos - obs_pos
            dist_sq = diff.length_squared

            # 1. Broadphase: Distance Check
            if dist_sq > range_sq:
                continue

            # 2. Angle Check (FOV)
            if vision.fov < 360:
                target_dir = diff.normalized()
                if obs_dir.dot(target_dir) < fov_cos:
                    continue

            # 3. Narrowphase: Raycast
            # Check for obstruction

            # segment_query_first returns the FIRST shape hit.
            # We want to see if that shape belongs to the target or is a transparent sensor,
            # or is an obstacle.

            hit = self.space.segment_query_first(obs_pos, target_pos, 1.0, vision_filter)

            if hit:
                if hit.shape == target_phys.shape:
                    # We hit the target directly
                    visible.add(target_ent)
                elif hit.shape.sensor:
                    # Hit a sensor (should be filtered out by mask usually, but if not...)
                    # If we hit a sensor that is NOT the target (targets might have sensor shapes if they are children)
                    # For now, assume sensors don't block vision.
                    # But segment_query_first stops at the first hit.
                    # If the first hit is a sensor, we don't know if there is a wall behind it.
                    # Ideally, sensors should not be in the vision_mask.
                    pass
                else:
                    # Hit something else (Wall or another Unit)
                    # Blocked.
                    pass
            else:
                # No hit?
                # This is weird if the target has a shape and is in the mask.
                # If target is NOT in the mask (e.g. Item or Poop?), then we won't hit it.
                # If we assume Items don't block vision but can be seen...
                # The logic above assumes we MUST hit the target shape to see it.
                # If target is not in mask, we won't hit it.
                # So if hit is None, it means line of sight is clear of OBSTACLES.
                # So it is visible!

                visible.add(target_ent)

        ai.visible_entities = visible
