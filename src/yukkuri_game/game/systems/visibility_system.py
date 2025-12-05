"""
Visibility System.
"""
import pymunk
import math
from ...engine.ecs import System, World
from ..components import Vision, Transform, PhysicsBody
from ..yukkuri_components import AIState
from .physics import PhysicsSystem

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

        obs_pos = pymunk.Vec2d(trans.x, trans.y)
        range_sq = vision.range * vision.range

        # Try to get rotation from PhysicsBody if available
        phys_comp = world.get_component(entity, PhysicsBody)
        obs_angle = phys_comp.body.angle if phys_comp else 0.0

        # Vector for angle check (if FOV < 360)
        # obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)

        for target_ent, (target_phys, target_trans) in targets:
            if entity == target_ent:
                continue

            target_pos = target_phys.body.position
            diff = target_pos - obs_pos
            dist_sq = diff.length_squared

            # 1. Broadphase: Distance Check
            if dist_sq > range_sq:
                continue

            # 2. Angle Check
            if vision.fov < 360:
                # TODO: Implement FOV check
                pass

            # 3. Narrowphase: Raycast
            # We want to check if there is an obstruction.
            # Filter: We want to hit Walls and other Units.
            # We use a default filter that hits everything for now.
            # To optimize, we should use collision masks.

            # segment_query_first returns the first shape hit.
            # If hit.shape is target.shape, then we see it.
            # If hit.shape is wall, we don't.

            hit = self.space.segment_query_first(obs_pos, target_pos, 1.0, pymunk.ShapeFilter())

            if hit:
                if hit.shape == target_phys.shape:
                    visible.add(target_ent)
                elif hit.shape.sensor:
                    # If we hit a sensor, it shouldn't block vision usually.
                    # But query_first stops at sensor if filter allows it.
                    # We might need full query if sensors clutter the space.
                    # For now assume sensors don't block if configured correctly in filter.
                    # But here we used default filter.
                    # If we hit a sensor that is NOT the target, we might falsely say blocked.
                    # Ideally we filter out sensors in query.
                    pass
                else:
                    # Hit wall or other unit
                    pass
            else:
                # If no shape is hit, the target is not visible.
                pass

        ai.visible_entities = visible
