"""
Visibility System.
Optimized to use Spatial Hash for broadphase (O(N*logM)) instead of O(N*M).
Uses Event Bus to maintain Entity Map incrementally.
"""

import pymunk
import math
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import ComponentAddedEvent, ComponentRemovedEvent
from ..components import Vision, Transform, PhysicsBody
from ..yukkuri_components import AIState
from .physics import PhysicsSystem
from .physics import PhysicsSystem
from ..collision_constants import CollisionCategories
from ...engine.types import EntityID
from typing import cast


class VisibilitySystem(System):
    """
    Calculates visibility using spatial hashing, raycasting and caching.

    Attributes:
        space (Optional[pymunk.Space]): The physics space.
        update_index (int): Index for batch processing.
        batch_size (float): Fraction of entities to update per frame (0.2 = 20%).
        body_to_entity (Dict[pymunk.Body, int]): Map of bodies to entity IDs.
        event_bus (Optional[EventBus]): The event bus.
    """

    def __init__(self) -> None:
        """Initializes the VisibilitySystem."""
        self.space: pymunk.Space | None = None
        self.update_index = 0
        self.batch_size = 0.2  # Process 20% of entities per frame
        self.body_to_entity: dict[pymunk.Body, int] = {}
        self.event_bus: EventBus | None = None
        
        # --- Performance Optimization: Visibility Caching ---
        # Cache visibility results per observer.
        # Key: entity_id -> (visible_set, cached_x, cached_y)
        # Invalidate cache if observer moves more than cache_threshold pixels.
        self.visibility_cache: dict[int, tuple[set[int], float, float]] = {}
        self.cache_threshold: float = 10.0  # Invalidate if moved > 10 pixels

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

        Returns:
            None
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

            # Initial population of the map, runs only once.
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
            
            # Optimization: Try to get body from our map (reverse lookup is slow? No we only have Body->Entity)
            # We need Entity -> Body. 
            # Let's fallback to ECS for Observer Body, it's only 1 call per observer.
            # But we can optimize if we cache it? 
            # For now, just passing the body if found avoids logic inside.
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

        Returns:
            None
        """
        # --- Cache Check: Temporal Coherence ---
        # If observer hasn't moved significantly, reuse cached visibility.
        if entity in self.visibility_cache:
            cached_visible, cached_x, cached_y = self.visibility_cache[entity]
            dx = trans.x - cached_x
            dy = trans.y - cached_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < self.cache_threshold * self.cache_threshold:
                # Cache hit! Reuse previous visibility result.
                ai.visible_entities = {cast(EntityID, x) for x in cached_visible}
                return
        
        visible: set[EntityID] = set()

        obs_pos = pymunk.Vec2d(trans.x, trans.y)
        # phys_comp passed as argument
        obs_angle = phys_comp.body.angle if phys_comp else 0.0
        # obs_shape is unused in the loop, logic relies on body
        # obs_shape = phys_comp.shape if phys_comp else None

        # Collect all shapes of the observer (Composite Body Support)
        obs_shapes = []
        if phys_comp:
            obs_shapes = list(phys_comp.body.shapes)

        obs_dir = pymunk.Vec2d(1, 0).rotated(obs_angle)
        fov_cos = math.cos(math.radians(vision.fov / 2.0))

        # 1. Broadphase
        query_mask = CollisionCategories.YUKKURI
        query_filter = pymunk.ShapeFilter(mask=query_mask)

        if not self.space:
            return

        # Optimization: Use point_query only? Or shape_query with a Sensor Circle?
        # Creating a sensor circle is expensive per entity per frame.
        # point_query is fast but only finds shapes overlapping a point (useless for range).
        # point_query in pymunk finds shapes within `max_dist` of point. This is exactly what we need.
        nearby_infos = self.space.point_query(obs_pos, vision.range, query_filter)

        vision_mask = CollisionCategories.WALL | CollisionCategories.YUKKURI
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

            if diff.length_squared > vision.range * vision.range:
                continue

            # 2. Angle Check
            if vision.fov < 360:
                target_dir = diff.normalized()
                if obs_dir.dot(target_dir) < fov_cos:
                    continue

            # 3. Narrowphase: Raycast
            # We cast to the target's center.
            
            # Note: group filter only works if shapes are configured with the same group ID.
            # Since we can't guarantee that, we still need to check for self-hits.
            vision_ray_filter = pymunk.ShapeFilter(mask=vision_mask, group=entity)
            
            # Optimization: Use segment_query_first to stop at the first hit.
            # This avoids sorting and iterating through multiple hits.
            hit = self.space.segment_query_first(obs_pos, target_pos, 1.0, vision_ray_filter)
            
            if hit:
                # Skip if we hit our own body (can happen if ray originates inside our shape)
                if phys_comp and hit.shape.body == phys_comp.body:
                    # We hit ourselves first - need to check if target is visible beyond us
                    # Fall back to full segment query to find actual first non-self hit
                    hits = self.space.segment_query(obs_pos, target_pos, 1.0, vision_ray_filter)
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
                    # First hit is the target - visible!
                    visible.add(EntityID(target_ent))
                # else: First hit is something else (wall, other entity) - blocked
            # else: No hit at all - shouldn't happen but target is not visible

            # --- OLD LOGIC (Preserved for reference) ---
            # hits = self.space.segment_query(obs_pos, target_pos, 1.0, vision_ray_filter)
            # hits.sort(key=lambda x: x.alpha)
            #
            # blocked = False
            #
            # for hit in hits:
            #     if hit.shape in obs_shapes:
            #         continue
            #
            #     if hit.shape.sensor:
            #         continue
            #
            #     if hit.shape.body == body:
            #         # Hit target!
            #         break
            #     else:
            #         # Hit something else
            #         blocked = True
            #         break
            #
            # if not blocked:
            #    visible.add(target_ent)
            # -------------------------------------------

        # Store result in cache for temporal coherence
        # Cast visible to set[int] for storage in dict[int, ...], though EntityID is int
        visible_ints: set[int] = {int(x) for x in visible}
        self.visibility_cache[entity] = (visible_ints, trans.x, trans.y)
        ai.visible_entities = visible
