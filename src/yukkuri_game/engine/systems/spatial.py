"""
Sector System - Spatial Partitioning for Efficient Queries.
"""

import math
from collections import defaultdict
from collections.abc import Callable

import pymunk

from ..ecs import System, World
from ..event_bus import EventBus
from ..events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    EntityDestroyedEvent,
    WorldClearedEvent,
)
from yukkuri_game.engine.components import (
    FloatingText,
    Mount,
    MovementController,
    Occluder,
    PhysicsBody,
    Transform,
    Velocity,
)

from yukkuri_game.game.systems.visual_movement_system import VisualMovementSystem


class SpatialService:
    """
    Grid-based spatial index for efficient proximity queries.

    Entities are assigned to sectors based on their position.
    Queries return all entities in relevant sectors (superset);
    callers should filter by precise distance if needed.
    """

    def __init__(self, width: float, height: float, sector_size: float):
        self.width = width
        self.height = height
        self.sector_size = sector_size

        # Grid dimensions
        self.cols = int(math.ceil(width / sector_size))
        self.rows = int(math.ceil(height / sector_size))

        # Sector storage: (col, row) -> set of entity IDs
        self.sectors: dict[tuple[int, int], set[int]] = defaultdict(set)

        # Reverse lookup: entity_id -> current (col, row)
        self.entity_sectors: dict[int, tuple[int, int]] = {}

        # Physics body to entity mapping for raycasts
        self.body_to_entity: dict[pymunk.Body, int] = {}

        # Reference to the ECS World
        self.world: World | None = None

    def get_sector_coords(self, x: float, y: float) -> tuple[int, int]:
        col = int(x / self.sector_size)
        row = int(y / self.sector_size)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return (col, row)

    def update_entity(self, entity_id: int, x: float, y: float) -> None:
        new_sector = self.get_sector_coords(x, y)
        old_sector = self.entity_sectors.get(entity_id)

        if old_sector == new_sector:
            return

        if old_sector:
            if entity_id in self.sectors[old_sector]:
                self.sectors[old_sector].remove(entity_id)

        self.sectors[new_sector].add(entity_id)
        self.entity_sectors[entity_id] = new_sector

    def remove_entity(self, entity_id: int) -> None:
        if entity_id in self.entity_sectors:
            sector = self.entity_sectors[entity_id]
            if entity_id in self.sectors[sector]:
                self.sectors[sector].remove(entity_id)
            del self.entity_sectors[entity_id]

    def get_entities_in_sector(self, col: int, row: int) -> set[int]:
        return self.sectors.get((col, row), set())

    def get_adjacent_sectors(self, col: int, row: int) -> list[tuple[int, int]]:
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                ncol, nrow = col + dx, row + dy
                if 0 <= ncol < self.cols and 0 <= nrow < self.rows:
                    adjacent.append((ncol, nrow))
        return adjacent

    def clear(self) -> None:
        """Clears all stored entities from the index."""
        self.sectors.clear()
        self.entity_sectors.clear()

    def _get_physical_entities_in_bounds(
        self, min_x: float, min_y: float, max_x: float, max_y: float
    ) -> list[int]:
        """Queries Pymunk's physics space bounding box for physical entities.

        Args:
            min_x: Minimum X coordinate.
            min_y: Minimum Y coordinate.
            max_x: Maximum X coordinate.
            max_y: Maximum Y coordinate.

        Returns:
            list[int]: List of entity IDs matching physical bodies in the bounds.
        """
        if not hasattr(self, "world") or not self.world:
            return []
        from yukkuri_game.engine.protocols import IPhysicsService

        physics = self.world.services.try_get(IPhysicsService)
        if not physics or not physics.space:
            return []
        bb = pymunk.BB(min_x, min_y, max_x, max_y)
        shapes = physics.space.bb_query(bb, pymunk.ShapeFilter())
        entities: list[int] = []
        seen_entities: set[int] = set()
        is_occluder_map = isinstance(self, OccluderMap)
        for shape in shapes:
            if shape.body:
                ent_id = self.body_to_entity.get(shape.body)
                if ent_id is not None and ent_id not in seen_entities:
                    if is_occluder_map and not self.world.has_component(
                        ent_id, Occluder
                    ):
                        continue
                    seen_entities.add(ent_id)
                    entities.append(ent_id)
        return entities

    def get_entities_in_range(
        self, x: float, y: float, range_type: str = "visual"
    ) -> list[int]:
        """Retrieves entities within a range category from a position.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            range_type: The range classification (e.g. 'visual').

        Returns:
            list[int]: List of entity IDs in range.
        """
        col, row = self.get_sector_coords(x, y)
        result: list[int] = []
        sector_entities = self.sectors.get((col, row))
        if sector_entities:
            result.extend(sector_entities)

        min_col, max_col = col, col
        min_row, max_row = row, row

        if range_type in ["visual", "auditory_loud"]:
            for acol, arow in self.get_adjacent_sectors(col, row):
                adj_sector_entities = self.sectors.get((acol, arow))
                if adj_sector_entities:
                    result.extend(adj_sector_entities)
            min_col = max(0, col - 1)
            max_col = min(self.cols - 1, col + 1)
            min_row = max(0, row - 1)
            max_row = min(self.rows - 1, row + 1)

        min_x = min_col * self.sector_size
        max_x = (max_col + 1) * self.sector_size
        min_y = min_row * self.sector_size
        max_y = (max_row + 1) * self.sector_size

        phys_entities = self._get_physical_entities_in_bounds(
            min_x, min_y, max_x, max_y
        )
        if phys_entities:
            seen = set(result)
            for pe in phys_entities:
                if pe not in seen:
                    result.append(pe)
                    seen.add(pe)
        return result

    def get_entities_in_radius(self, x: float, y: float, radius: float) -> list[int]:
        """Retrieves entity IDs within a certain bounding radius.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Bounding query radius.

        Returns:
            list[int]: List of entity IDs within the radius.
        """
        min_x = x - radius
        max_x = x + radius
        min_y = y - radius
        max_y = y + radius
        start_col, start_row = self.get_sector_coords(min_x, min_y)
        end_col, end_row = self.get_sector_coords(max_x, max_y)
        result: list[int] = []
        for c in range(start_col, end_col + 1):
            for r in range(start_row, end_row + 1):
                sector_entities = self.sectors.get((c, r))
                if sector_entities:
                    result.extend(sector_entities)

        phys_entities = self._get_physical_entities_in_bounds(
            min_x, min_y, max_x, max_y
        )
        if phys_entities:
            seen = set(result)
            for pe in phys_entities:
                if pe not in seen:
                    result.append(pe)
                    seen.add(pe)
        return result

    def get_entities_in_rect(
        self, x: float, y: float, width: float, height: float
    ) -> list[int]:
        """Retrieves entity IDs within a rectangular bounding box.

        Args:
            x: Bottom-left/Top-left X coordinate.
            y: Bottom-left/Top-left Y coordinate.
            width: Width of the rect.
            height: Height of the rect.

        Returns:
            list[int]: List of entity IDs within the box.
        """
        min_x = x
        max_x = x + width
        min_y = y
        max_y = y + height
        start_col, start_row = self.get_sector_coords(min_x, min_y)
        end_col, end_row = self.get_sector_coords(max_x, max_y)
        result: list[int] = []
        for c in range(start_col, end_col + 1):
            for r in range(start_row, end_row + 1):
                sector_entities = self.sectors.get((c, r))
                if sector_entities:
                    result.extend(sector_entities)

        phys_entities = self._get_physical_entities_in_bounds(
            min_x, min_y, max_x, max_y
        )
        if phys_entities:
            seen = set(result)
            for pe in phys_entities:
                if pe not in seen:
                    result.append(pe)
                    seen.add(pe)
        return result

    def get_nearest_entity(
        self,
        world: World,
        x: float,
        y: float,
        component_filter: type | None = None,
        max_radius: float = 1000.0,
        exclude_ids: set[int] | None = None,
        predicate: Callable[[int], bool] | None = None,
    ) -> int:
        if exclude_ids is None:
            exclude_ids = set()
        candidates = self.get_entities_in_radius(x, y, max_radius)
        best_dist = float("inf")
        best_ent = -1
        for ent in candidates:
            if ent in exclude_ids:
                continue
            if component_filter and not world.has_component(ent, component_filter):
                continue
            if predicate and not predicate(ent):
                continue
            trans = world.try_get_component(ent, Transform)
            if not trans:
                continue
            dist = math.hypot(trans.x - x, trans.y - y)
            if dist < best_dist and dist <= max_radius:
                best_dist = dist
                best_ent = ent
        return best_ent

    def raycast(
        self, world: World, start_x: float, start_y: float, end_x: float, end_y: float, shape_filter: pymunk.ShapeFilter | None = None, exclude_id: int = -1
    ) -> tuple[int, float, float] | None:
        from yukkuri_game.engine.protocols import IPhysicsService
        physics_system = world.services.try_get(IPhysicsService)
        if not physics_system or not physics_system.space:
            return None
        start_pos = (start_x, start_y)
        end_pos = (end_x, end_y)
        qfilter = shape_filter or pymunk.ShapeFilter()
        hit = physics_system.space.segment_query_first(start_pos, end_pos, 1.0, qfilter)
        if not hit:
            return None
        if hit.shape and hit.shape.body:
            body = hit.shape.body
            ent_id = self.body_to_entity.get(body)
            if ent_id is not None and ent_id != exclude_id:
                return (ent_id, hit.point.x, hit.point.y)
            if ent_id == exclude_id:
                hits = physics_system.space.segment_query(start_pos, end_pos, 1.0, qfilter)
                for h in sorted(hits, key=lambda x: x.alpha):
                    if not h.shape or not h.shape.body or h.shape.sensor:
                        continue
                    h_ent_id = self.body_to_entity.get(h.shape.body)
                    if h_ent_id is not None and h_ent_id != exclude_id:
                        return (h_ent_id, h.point.x, h.point.y)
                    if h_ent_id is None and not h.shape.sensor:
                        return (-1, h.point.x, h.point.y)
                return None
            if not hit.shape.sensor:
                return (-1, hit.point.x, hit.point.y)
        return None


class OccluderMap(SpatialService):
    """
    Specialized SpatialService for entities with Occluder components.
    Allows efficient querying of only occluders in a region.
    """
    pass



class SpatialSystem(System):
    run_after = [VisualMovementSystem]

    """
    System responsible for keeping the SpatialService updated with entity positions.
    """
    DEFAULT_WORLD_WIDTH = 4000.0
    DEFAULT_WORLD_HEIGHT = 4000.0
    DEFAULT_SECTOR_SIZE = 500.0
    CLEANUP_INTERVAL = 5.0

    def __init__(
        self,
        event_bus: EventBus | None = None,
        width: float = DEFAULT_WORLD_WIDTH,
        height: float = DEFAULT_WORLD_HEIGHT,
        sector_size: float = DEFAULT_SECTOR_SIZE,
    ):
        self.width = width
        self.height = height
        self.sector_size = sector_size
        
        self.spatial_service = SpatialService(
            width, height, sector_size
        )
        self.occluder_map = OccluderMap(
            width, height, sector_size
        )
        self.event_bus = event_bus
        self._subscribed = False
        self._new_entities: set[int] = set()
        self._first_run: bool = True
        self.cleanup_timer = 0.0
        self.cleanup_interval = self.CLEANUP_INTERVAL
        self.body_to_entity: dict[pymunk.Body, int] = {}
        self._processed_entities: set[int] = set()

        if self.event_bus:
            self._subscribe_events()

    def _subscribe_events(self) -> None:
        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
            self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
            self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)
            self._subscribed = True

    def initialize(self) -> None:
        if hasattr(self, "ecs_world"):
            self._lazy_init(self.ecs_world)
            self._ensure_services(self.ecs_world)

    def _lazy_init(self, world: World) -> None:
        if not self._subscribed:
            event_bus = world.services.try_get(EventBus)
            if event_bus:
                self.event_bus = event_bus
                self._subscribe_events()

    def on_component_added(self, event: ComponentAddedEvent) -> None:
        if event.component_type == Transform or event.component_type == Occluder:
            self._new_entities.add(event.entity_id)
        elif event.component_type == PhysicsBody:
            self.body_to_entity[event.component.body] = event.entity_id
            if self.spatial_service:
                self.spatial_service.remove_entity(event.entity_id)

    def on_component_removed(self, event: ComponentRemovedEvent) -> None:
        if event.component_type == PhysicsBody:
            if event.component and event.component.body in self.body_to_entity:
                del self.body_to_entity[event.component.body]
            if hasattr(self, "ecs_world") and self.ecs_world:
                transform = self.ecs_world.try_get_component(
                    event.entity_id, Transform
                )
                if transform:
                    self.spatial_service.update_entity(
                        event.entity_id, transform.x, transform.y
                    )

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        if self.spatial_service:
            self.spatial_service.remove_entity(event.entity_id)
        if self.occluder_map:
            self.occluder_map.remove_entity(event.entity_id)

    def on_world_cleared(self, event: WorldClearedEvent) -> None:
        if self.spatial_service:
            self.spatial_service.clear()
        if self.occluder_map:
            self.occluder_map.clear()
        self.body_to_entity.clear()
        self._new_entities.clear()
        self._processed_entities.clear()
        self._first_run = True

    def _ensure_services(self, world: World) -> None:
        """Ensures that SpatialService and OccluderMap are created and registered."""
        from yukkuri_game.engine.protocols import ISpatialService
        registered = world.services.try_get(ISpatialService)
        if registered is not None:
            self.spatial_service = registered
        else:
            world.services.register(
                self.spatial_service, ISpatialService, replace=True
            )
        self.spatial_service.world = world
        self.spatial_service.body_to_entity = self.body_to_entity
        
        registered_occluder = world.services.try_get(OccluderMap)
        if registered_occluder is not None:
            self.occluder_map = registered_occluder
        else:
            world.services.register(
                self.occluder_map, OccluderMap, replace=True
            )
        self.occluder_map.world = world
        self.occluder_map.body_to_entity = self.body_to_entity

    def update(self, world: World, dt: float) -> None:
        if not self._subscribed:
            self._lazy_init(world)

        self._ensure_services(world)
        spatial_service = self.spatial_service
        occluder_map = self.occluder_map
        assert spatial_service is not None
        assert occluder_map is not None

        # If no event bus, we can't rely on ComponentAddedEvent, so we must full scan.
        # This is primarily for simplified unit tests.
        force_full_scan = self.event_bus is None

        if self._first_run or force_full_scan:
            for entity, (transform,) in world.get_components_tuple(Transform):
                if not world.has_component(entity, PhysicsBody):
                    spatial_service.update_entity(
                        entity, transform.x, transform.y
                    )
                if world.has_component(entity, Occluder):
                    occluder_map.update_entity(entity, transform.x, transform.y)
            self._first_run = False
            self._new_entities.clear()
        
        if not force_full_scan and self._new_entities:
            for entity in self._new_entities:
                transform = world.try_get_component(entity, Transform)
                if transform:
                    if not world.has_component(entity, PhysicsBody):
                        spatial_service.update_entity(
                            entity, transform.x, transform.y
                        )
                    if world.has_component(entity, Occluder):
                        occluder_map.update_entity(
                            entity, transform.x, transform.y
                        )
            self._new_entities.clear()

        self._processed_entities.clear()

        def check_and_update(entity: int, transform: Transform) -> None:
            if entity in self._processed_entities:
                return
            self._processed_entities.add(entity)
            if transform.x != transform.prev_x or transform.y != transform.prev_y:
                if not world.has_component(entity, PhysicsBody):
                    spatial_service.update_entity(
                        entity, transform.x, transform.y
                    )
                if world.has_component(entity, Occluder):
                    occluder_map.update_entity(entity, transform.x, transform.y)

        for ent, (t, _) in world.get_components_tuple(Transform, Velocity):
            check_and_update(ent, t)

        for ent, (t, body) in world.get_components_tuple(Transform, PhysicsBody):
            if body.body.body_type != pymunk.Body.STATIC:
                check_and_update(ent, t)

        for ent, (t, _) in world.get_components_tuple(Transform, MovementController):
            check_and_update(ent, t)

        for ent, (t, mount) in world.get_components_tuple(Transform, Mount):
            if mount.parent_id != -1:
                check_and_update(ent, t)

        for ent, (t, _) in world.get_components_tuple(Transform, FloatingText):
            check_and_update(ent, t)

        self.cleanup_timer += dt
        if self.cleanup_timer >= self.cleanup_interval:
            self.cleanup_timer = 0.0
            self.cleanup_dead_entities(world)

    def cleanup_dead_entities(self, world: World) -> None:
        if self.spatial_service:
            to_remove = [eid for eid in self.spatial_service.entity_sectors.keys() if not world.has_component(eid, Transform)]
            for eid in to_remove:
                self.spatial_service.remove_entity(eid)
        if self.occluder_map:
            to_remove_occluder = [eid for eid in self.occluder_map.entity_sectors.keys() if not world.has_component(eid, Transform) or not world.has_component(eid, Occluder)]
            for eid in to_remove_occluder:
                self.occluder_map.remove_entity(eid)
