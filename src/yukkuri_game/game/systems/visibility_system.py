"""
Visibility System - Line-of-Sight Calculation.

Determines what each entity can see based on vision range, FOV, and obstacles.
Uses spatial hashing for broadphase optimization and raycasting for narrowphase.

Algorithm:
1.  **Broadphase**: Query entities within vision range using point_query.
2.  **FOV Filter**: Check if target is within observer's field of view cone.
3.  **Narrowphase**: Raycast to target, checking for obstructions.

Optimizations:
-   Batch processing: Only 20% of observers updated per frame (temporal amortization).
-   Body-to-entity map: O(1) lookup of entity from physics body.
-   Visibility cache: Reuses results if observer moved < 10 pixels (temporal coherence).

Flight Integration:
-   Flying entities gain +50% vision range at max altitude.
-   Linear interpolation based on current altitude.

Output:
-   Populates AIState.visible_entities for use by AI decision making.
"""

import math

import pymunk

from ...engine.ecs import System, World
from ...engine.types import EntityID
from ..collision_constants import CollisionCategories
from ..components import AIState, Flight, PhysicsBody, Transform, Vision


class VisibilitySystem(System):
    """
    Calculates visible entities using spatial queries and raycasting.

    Uses temporal coherence caching to avoid redundant calculations
    when observers haven't moved significantly. Batch-processes observers
    to spread workload across frames.

    Attributes:
        update_index (int): Index for batch processing.
        batch_size (float): Fraction of observers processed per frame.
        visibility_cache (dict[int, tuple[set[EntityID], float, float]]): Cache for visibility results.
        cache_threshold (float): Movement threshold for cache invalidation.
    """

    # Fraction of observers processed per frame (0.2 = 20%)
    DEFAULT_BATCH_SIZE = 0.2

    # Cache invalidation threshold (pixels moved)
    CACHE_THRESHOLD = 10.0

    def __init__(self) -> None:
        """Initializes the VisibilitySystem."""
        self.update_index = 0
        self.batch_size = self.DEFAULT_BATCH_SIZE

        # Visibility cache: entity_id -> (visible_set, cached_x, cached_y)
        self.visibility_cache: dict[int, tuple[set[EntityID], float, float]] = {}
        self.cache_threshold: float = self.CACHE_THRESHOLD

    def update(self, world: World, dt: float) -> None:
        """
        Updates visibility for a batch of entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """

        # Get all observers
        observers_list = list(world.get_components_tuple(Vision, Transform, AIState))
        total_obs = len(observers_list)

        if total_obs == 0:
            return

        count = max(1, int(total_obs * self.batch_size))
        start = self.update_index

        batch_indices = []
        for i in range(count):
            batch_indices.append((start + i) % total_obs)

        self.update_index = (start + count) % total_obs

        for idx in batch_indices:
            ent, (vision, trans, ai) = observers_list[idx]
            # Entity->Body lookup requires ECS call (reverse map not maintained).
            phys_comp = world.try_get_component(ent, PhysicsBody)
            self.update_visibility(ent, vision, trans, ai, world, phys_comp)

    def update_visibility(
        self,
        entity: int,
        vision: Vision,
        trans: Transform,
        ai: AIState,
        world: World,
        phys_comp: PhysicsBody | None,
    ) -> None:
        """
        Calculates visible entities for a single observer.
        Uses caching with temporal coherence - reuses results if observer hasn't moved.

        Args:
            entity (int): The observer entity ID.
            vision (Vision): The vision component.
            trans (Transform): The transform component.
            ai (AIState): The AI state component to update.
            world (World): The ECS World.
            phys_comp (PhysicsBody | None): The physics component of the observer.
        """
        # Reuse cached result if observer hasn't moved significantly.
        if entity in self.visibility_cache:
            cached_visible, cached_x, cached_y = self.visibility_cache[entity]
            dx = trans.x - cached_x
            dy = trans.y - cached_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < self.cache_threshold * self.cache_threshold:
                # OPTIMIZATION: Reuse the existing set object to allow object identity checks
                ai.visible_entities = cached_visible
                return

        from .spatial_system import SpatialService
        spatial_service = world.services.try_get(SpatialService)
        if not spatial_service:
            return

        visible: set[EntityID] = set()

        obs_pos = pymunk.Vec2d(trans.x, trans.y)
        obs_angle = phys_comp.body.angle if phys_comp else 0.0

        obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)
        fov_cos = math.cos(math.radians(vision.fov / 2.0))

        # 1. Broadphase
        flight = world.try_get_component(entity, Flight)
        effective_range = vision.range
        if flight and flight.altitude > 0 and flight.max_altitude > 0:
            # +50% vision range at max altitude
            altitude_factor = min(1.0, flight.altitude / flight.max_altitude)
            effective_range = vision.range * (1.0 + 0.5 * altitude_factor)

        nearby_ents = spatial_service.get_entities_in_radius(obs_pos.x, obs_pos.y, effective_range)

        vision_mask = (
            CollisionCategories.HIGH_OBSTACLE | CollisionCategories.GROUND_UNIT
        )
        vision_ray_filter = pymunk.ShapeFilter(mask=vision_mask, group=entity)

        for target_ent in nearby_ents:
            if target_ent == entity:
                continue
            if target_ent in visible:
                continue

            target_trans = world.try_get_component(target_ent, Transform)
            if not target_trans:
                continue

            target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
            diff = target_pos - obs_pos

            if diff.length_squared > effective_range * effective_range:
                continue

            # 2. Angle Check
            if vision.fov < 360:
                target_dir = diff.normalized()
                if obs_dir.dot(target_dir) < fov_cos:
                    continue

            # 3. Narrowphase: Raycast to check line-of-sight.
            hit = spatial_service.raycast(
                world,
                obs_pos.x, obs_pos.y,
                target_pos.x, target_pos.y,
                shape_filter=vision_ray_filter,
                exclude_id=entity
            )

            if hit:
                hit_ent, _, _ = hit
                if hit_ent == target_ent:
                    visible.add(EntityID(target_ent))
                elif world.has_component(target_ent, Transform):
                    # We might have hit something else. We only add if it's the target.
                    pass

        # Update cache with new visibility result.
        self.visibility_cache[entity] = (visible, trans.x, trans.y)
        ai.visible_entities = visible
