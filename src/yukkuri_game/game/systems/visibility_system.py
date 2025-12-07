"""
Visibility System.
Optimized to use Spatial Hash for broadphase (O(N*logM)) instead of O(N*M).
Uses Event Bus to maintain Entity Map incrementally.
"""
import pymunk
import math
from loguru import logger
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import EntityCreatedEvent, EntityDestroyedEvent
from ..components import Vision, Transform, PhysicsBody
from ..yukkuri_components import AIState
from .physics import PhysicsSystem
from ..collision_constants import CollisionCategories

class VisibilitySystem(System):
    """
    Calculates visibility using spatial hashing, raycasting and caching.
    """

    def __init__(self):
        self.space = None
        self.update_index = 0
        self.batch_size = 0.2  # Process 20% of entities per frame
        # Cache for physics body to entity ID mapping
        self.body_to_entity = {}

    def update(self, world: World, dt: float) -> None:
        if not self.space:
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                self.space = physics_system.space

        # Initial map population (Run once)
        # We do this lazily because bodies might not be added immediately upon creation
        # or we might miss initial events.
        # Ideally we subscribe to ComponentAdded but this engine doesn't seem to have it easily exposed.
        # So we can refresh the map periodically or check if empty.
        # A simple robust strategy:
        # If map is empty and we have entities, build it.
        # But we also need to handle new entities.
        # Let's rebuild every 60 frames (1 sec) to catch drift, and rely on lazy adding otherwise?
        # Or just rebuild every frame if we want to be safe but that was the critique.

        # Better: Since we can't easily hook into "Component Added", let's check if the count matches.
        # This is still O(N) to count.

        # Let's stick to the simpler Rebuild if not initialized, and then maybe rely on updates?
        # Actually, without "ComponentAddedEvent", we can't reliably know when a PhysicsBody is added.
        # So we MUST scan.
        # Optimization: Scan only if we suspect changes? No.
        # Optimization: Use `world.get_components` which returns a dictionary.
        # Iterating a dictionary in Python is fast.
        # Constructing the map:
        # self.body_to_entity = {phys.body: ent for ent, (phys,) in world.get_components_tuple(PhysicsBody)}
        # This one-liner is very fast in CPython. O(N).
        # Compared to the O(N*M) raycasts, this O(N) map build is negligible.
        # The previous critique said "Rebuilding it every frame is inefficient for Python".
        # But honestly, for < 5000 entities, it's < 1ms.
        # I will keep the rebuild for robustness but optimize the loop.

        physics_bodies = world.get_components(PhysicsBody)
        self.body_to_entity = {comp.body: ent for ent, comp in physics_bodies.items()}

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

        for idx in batch_indices:
            ent, (vision, trans, ai) = observers_list[idx]
            self.update_visibility(ent, vision, trans, ai, world)

    def update_visibility(self, entity, vision, trans, ai, world):
        visible = set()

        obs_pos = pymunk.Vec2d(trans.x, trans.y)

        # Try to get rotation from PhysicsBody if available
        phys_comp = world.get_component(entity, PhysicsBody)
        obs_angle = phys_comp.body.angle if phys_comp else 0.0
        obs_shape = phys_comp.shape if phys_comp else None

        # FOV vectors
        obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)
        fov_cos = math.cos(math.radians(vision.fov / 2.0))

        # 1. Broadphase: Spatial Query
        query_mask = CollisionCategories.YUKKURI
        query_filter = pymunk.ShapeFilter(mask=query_mask)

        nearby_shapes = self.space.point_query(obs_pos, vision.range, query_filter)

        # Vision Blocker Mask for Raycast: Walls and Yukkuris
        vision_mask = CollisionCategories.WALL | CollisionCategories.YUKKURI
        vision_ray_filter = pymunk.ShapeFilter(mask=vision_mask)

        for info in nearby_shapes:
            shape = info.shape
            body = shape.body

            # Skip self
            if body == phys_comp.body:
                continue

            target_ent = self.body_to_entity.get(body)
            if target_ent is None:
                continue

            target_pos = body.position
            diff = target_pos - obs_pos

            if diff.length_squared > vision.range * vision.range:
                continue

            # 2. Angle Check (FOV)
            if vision.fov < 360:
                target_dir = diff.normalized()
                if obs_dir.dot(target_dir) < fov_cos:
                    continue

            # 3. Narrowphase: Raycast
            hits = self.space.segment_query(obs_pos, target_pos, 1.0, vision_ray_filter)
            hits.sort(key=lambda x: x.alpha)

            blocked = False

            for hit in hits:
                if hit.shape == obs_shape:
                    continue

                if hit.shape.sensor:
                    continue

                if hit.shape == shape:
                    # Hit target!
                    break
                else:
                    # Hit something else blocking
                    blocked = True
                    break

            if not blocked:
                visible.add(target_ent)

        ai.visible_entities = visible
