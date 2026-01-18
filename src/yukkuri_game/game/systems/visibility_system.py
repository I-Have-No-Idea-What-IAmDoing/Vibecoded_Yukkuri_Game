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

import pymunk
import math
from typing import Dict, List, Optional, Set, Tuple, cast

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import ComponentAddedEvent, ComponentRemovedEvent
from ..components import Vision, Transform, PhysicsBody
from ..yukkuri_components import AIState, Flight
from .physics import PhysicsSystem
from ..collision_constants import CollisionCategories
from ...engine.types import EntityID


class VisibilitySystem(System):
    """
    Calculates visible entities using spatial queries and raycasting.

    Uses temporal coherence caching to avoid redundant calculations
    when observers haven't moved significantly. Batch-processes observers
    to spread workload across frames.

    Attributes:
        space (Optional[pymunk.Space]): The physics space.
        update_index (int): Index for batch processing.
        batch_size (float): Fraction of observers processed per frame.
        body_to_entity (Dict[pymunk.Body, int]): Map of physics bodies to entity IDs.
        event_bus (Optional[EventBus]): The event bus.
        visibility_cache (Dict[int, Tuple[Set[EntityID], float, float]]): Cache for visibility results.
        cache_threshold (float): Movement threshold for cache invalidation.
    """

    # Fraction of observers processed per frame (0.2 = 20%)
    DEFAULT_BATCH_SIZE = 0.2

    # Cache invalidation threshold (pixels moved)
    CACHE_THRESHOLD = 10.0

    def __init__(self) -> None:
        """Initializes the VisibilitySystem."""
        self.space: Optional[pymunk.Space] = None
        self.update_index = 0
        self.batch_size = self.DEFAULT_BATCH_SIZE
        self.body_to_entity: Dict[pymunk.Body, int] = {}
        self.event_bus: Optional[EventBus] = None

        # Visibility cache: entity_id -> (visible_set, cached_x, cached_y)
        self.visibility_cache: Dict[int, Tuple[Set[EntityID], float, float]] = {}
        self.cache_threshold: float = self.CACHE_THRESHOLD

    def on_component_added(self, event: ComponentAddedEvent) -> None:
        """
        Handles ComponentAddedEvent to update body_to_entity map.

        Args:
            event (ComponentAddedEvent): The event data.
        """
        if event.component_type == PhysicsBody:
            self.body_to_entity[event.component.body] = event.entity_id

    def on_component_removed(self, event: ComponentRemovedEvent) -> None:
        """
        Handles ComponentRemovedEvent to update body_to_entity map.

        Args:
            event (ComponentRemovedEvent): The event data.
        """
        if event.component_type == PhysicsBody:
            if event.component and event.component.body in self.body_to_entity:
                del self.body_to_entity[event.component.body]

    def update(self, world: World, dt: float) -> None:
        """
        Updates visibility for a batch of entities.

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
                # Subscribe to both add and remove events
                self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
                self.event_bus.subscribe(
                    ComponentRemovedEvent, self.on_component_removed
                )

            # Populate body->entity map on first run.
            physics_bodies = world.get_components(PhysicsBody)
            self.body_to_entity = {
                comp.body: ent for ent, comp in physics_bodies.items()
            }

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
        phys_comp: Optional[PhysicsBody],
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
            phys_comp (Optional[PhysicsBody]): The physics component of the observer.
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

        visible: Set[EntityID] = set()

        obs_pos = pymunk.Vec2d(trans.x, trans.y)
        obs_angle = phys_comp.body.angle if phys_comp else 0.0

        obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)
        fov_cos = math.cos(math.radians(vision.fov / 2.0))

        # 1. Broadphase
        query_mask = CollisionCategories.GROUND_UNIT
        query_filter = pymunk.ShapeFilter(mask=query_mask)

        if not self.space:
            return

        # Flight altitude vision bonus
        flight = world.try_get_component(entity, Flight)
        effective_range = vision.range
        if flight and flight.altitude > 0 and flight.max_altitude > 0:
            # +50% vision range at max altitude
            altitude_factor = min(1.0, flight.altitude / flight.max_altitude)
            effective_range = vision.range * (1.0 + 0.5 * altitude_factor)

        # Broadphase: Query all entities within effective vision range.
        nearby_infos = self.space.point_query(obs_pos, effective_range, query_filter)

        vision_mask = (
            CollisionCategories.HIGH_OBSTACLE | CollisionCategories.GROUND_UNIT
        )
        vision_ray_filter = pymunk.ShapeFilter(mask=vision_mask)

        for info in nearby_infos:
            shape = info.shape
            body = shape.body

            if phys_comp and body == phys_comp.body:
                continue

            # Skip if we already saw this entity (Composite bodies have multiple shapes)
            if body is None:
                continue
            target_ent = self.body_to_entity.get(body)
            if target_ent is None:
                continue
            if target_ent in visible:
                continue

            target_pos = body.position
            diff = target_pos - obs_pos

            if diff.length_squared > effective_range * effective_range:
                continue

            # 2. Angle Check
            if vision.fov < 360:
                target_dir = diff.normalized()
                if obs_dir.dot(target_dir) < fov_cos:
                    continue

            # Narrowphase: Raycast to check line-of-sight.
            vision_ray_filter = pymunk.ShapeFilter(mask=vision_mask, group=entity)

            hit = self.space.segment_query_first(
                obs_pos, target_pos, 1.0, vision_ray_filter
            )

            if hit:
                # Skip if we hit our own body (can happen if ray originates inside our shape)
                if phys_comp and hit.shape.body == phys_comp.body:
                    # We hit ourselves first - need to check if target is visible beyond us
                    # Fall back to full segment query to find actual first non-self hit
                    hits = self.space.segment_query(
                        obs_pos, target_pos, 1.0, vision_ray_filter
                    )
                    for h in sorted(hits, key=lambda x: x.alpha):
                        if phys_comp and h.shape.body == phys_comp.body:
                            continue  # Skip our own shapes
                        if h.shape.sensor:
                            continue  # Skip sensors
                        if h.shape.body == body:
                            visible.add(EntityID(target_ent))  # Target is visible!
                        # Hit something else first - blocked
                        break
                elif hit.shape.body == body:
                    visible.add(EntityID(target_ent))
                # else: First hit is an obstruction - blocked.

        # Update cache with new visibility result.
        self.visibility_cache[entity] = (visible, trans.x, trans.y)
        ai.visible_entities = visible
