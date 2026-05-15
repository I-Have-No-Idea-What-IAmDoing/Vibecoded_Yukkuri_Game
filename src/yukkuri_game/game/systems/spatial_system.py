"""
Sector System - Spatial Partitioning for Efficient Queries.

Divides the game world into fixed-size grid sectors for O(1) spatial lookups.
Critical for performance when many entities need proximity checks.

Use Cases:
-   GossipSystem: Find witnesses within visual/auditory range.
-   FamilySystem: Find nearby family members for benefits.
-   PerceptionSystem: Query visible entities without O(N^2) scans.
-   NavigationService: Obstacle queries in limited areas.

Sector Structure:
-   World divided into SECTOR_SIZE x SECTOR_SIZE cells (default 500px).
-   Each sector tracks entity IDs within its bounds.
-   Entities automatically moved between sectors on position update.

Range Types (for get_entities_in_range):
-   "visual": Same sector + 8 adjacent sectors (3x3 area).
-   "auditory_loud": Same as visual (loud sounds carry far).
-   "auditory": Same sector only (quiet sounds are local).

Performance:
-   Entity update: O(1) amortized.
-   Range query: O(k) where k = entities in touched sectors.
-   Periodic cleanup removes stale entity references.
"""

import math
from collections import defaultdict
from collections.abc import Callable

import pymunk

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    EntityDestroyedEvent,
)
from ..components import (
    FloatingText,
    Mount,
    MovementController,
    Occluder,
    PhysicsBody,
    Transform,
    Velocity,
)



class SpatialService:
    """
    Grid-based spatial index for efficient proximity queries.

    Entities are assigned to sectors based on their position.
    Queries return all entities in relevant sectors (superset);
    callers should filter by precise distance if needed.

    Attributes:
        width (float): Total world width in pixels.
        height (float): Total world height in pixels.
        sector_size (float): Size of each sector cell.
        cols (int): Number of columns in the grid.
        rows (int): Number of rows in the grid.
        sectors (dict[tuple[int, int], set[int]]): Map of (col, row) to set of entity IDs.
        entity_sectors (dict[int, tuple[int, int]]): Reverse lookup of entity ID to (col, row).
        body_to_entity (dict[pymunk.Body, int]): Map of physics bodies to entity IDs (populated by SpatialSystem).
    """

    def __init__(self, width: float, height: float, sector_size: float):
        """
        Initializes the SpatialService.

        Args:
            width (float): Total world width in pixels.
            height (float): Total world height in pixels.
            sector_size (float): Size of each sector cell (width and height).
        """
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

    def get_sector_coords(self, x: float, y: float) -> tuple[int, int]:
        """
        Returns the (col, row) coordinates for a given world position.
        Clamps to map boundaries.

        Args:
            x (float): X coordinate.
            y (float): Y coordinate.

        Returns:
            tuple[int, int]: (col, row) indices.
        """
        # Convert world coordinates to grid indices.
        col = int(x / self.sector_size)
        row = int(y / self.sector_size)

        # Clamp
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))

        return (col, row)

    def update_entity(self, entity_id: int, x: float, y: float) -> None:
        """
        Updates the entity's position in the sector map.

        Args:
            entity_id (int): ID of the entity.
            x (float): New X coordinate.
            y (float): New Y coordinate.
        """
        new_sector = self.get_sector_coords(x, y)
        old_sector = self.entity_sectors.get(entity_id)

        if old_sector == new_sector:
            return

        if old_sector:
            # We don't delete the key from entity_sectors yet, just remove from sector set
            if entity_id in self.sectors[old_sector]:
                self.sectors[old_sector].remove(entity_id)

        self.sectors[new_sector].add(entity_id)
        self.entity_sectors[entity_id] = new_sector

    def remove_entity(self, entity_id: int) -> None:
        """
        Removes an entity from the sector map.

        Args:
            entity_id (int): ID of the entity to remove.
        """
        if entity_id in self.entity_sectors:
            sector = self.entity_sectors[entity_id]
            if entity_id in self.sectors[sector]:
                self.sectors[sector].remove(entity_id)
            del self.entity_sectors[entity_id]

    def get_entities_in_sector(self, col: int, row: int) -> set[int]:
        """
        Returns all entities in a specific sector.

        Args:
            col (int): Column index.
            row (int): Row index.

        Returns:
            set[int]: Set of entity IDs in the sector.
        """
        return self.sectors.get((col, row), set())

    def get_adjacent_sectors(self, col: int, row: int) -> list[tuple[int, int]]:
        """
        Returns a list of valid (col, row) tuples for adjacent sectors (including diagonals).

        Args:
            col (int): Center column index.
            row (int): Center row index.

        Returns:
            list[tuple[int, int]]: List of adjacent (col, row) coordinates.
        """
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                ncol, nrow = col + dx, row + dy
                if 0 <= ncol < self.cols and 0 <= nrow < self.rows:
                    adjacent.append((ncol, nrow))
        return adjacent

    def get_entities_in_range(
        self, x: float, y: float, range_type: str = "visual"
    ) -> list[int]:
        """
        Returns entities based on propagation rules.

        Args:
            x (float): Origin X coordinate.
            y (float): Origin Y coordinate.
            range_type (str): "visual" (Same + Adjacent) or "auditory_loud" (Same + Adjacent) or "auditory" (Same).

        Returns:
            list[int]: List of entity IDs in range.
        """
        col, row = self.get_sector_coords(x, y)
        result: list[int] = []

        # Always include current sector (the sector the entity is currently standing in)
        sector_entities = self.sectors.get((col, row))
        if sector_entities:
            result.extend(sector_entities)

        if range_type in ["visual", "auditory_loud"]:
            # Include adjacent sectors
            for acol, arow in self.get_adjacent_sectors(col, row):
                adj_sector_entities = self.sectors.get((acol, arow))
                if adj_sector_entities:
                    result.extend(adj_sector_entities)

        return result

    def get_entities_in_radius(self, x: float, y: float, radius: float) -> list[int]:
        """
        Returns all entities in sectors overlapping the given radius.
        Note: This returns a superset of entities (all entities in touched sectors).
        Distance checking should be done by the caller for precision.

        Args:
            x (float): Center X coordinate.
            y (float): Center Y coordinate.
            radius (float): The search radius.

        Returns:
            list[int]: List of entity IDs in possible range.
        """
        # Calculate bounding box of the circle
        min_x = x - radius
        max_x = x + radius
        min_y = y - radius
        max_y = y + radius

        # Convert to sector indices
        start_col, start_row = self.get_sector_coords(min_x, min_y)
        end_col, end_row = self.get_sector_coords(max_x, max_y)

        result: list[int] = []

        # Iterate over rectangular range of sectors
        for c in range(start_col, end_col + 1):
            for r in range(start_row, end_row + 1):
                sector_entities = self.sectors.get((c, r))
                if sector_entities:
                    result.extend(sector_entities)

        return result

    def get_entities_in_rect(
        self, x: float, y: float, width: float, height: float
    ) -> list[int]:
        """
        Returns all entities in sectors overlapping the given rectangle.
        Note: This returns a superset of entities (all entities in touched sectors).

        Args:
            x (float): Top-left positions X (world space).
            y (float): Top-left positions Y (world space).
            width (float): Rectangle width.
            height (float): Rectangle height.

        Returns:
            list[int]: List of entity IDs in possible range.
        """
        min_x = x
        max_x = x + width
        min_y = y
        max_y = y + height

        # Convert to sector indices
        start_col, start_row = self.get_sector_coords(min_x, min_y)
        end_col, end_row = self.get_sector_coords(max_x, max_y)

        result: list[int] = []

        # Iterate over rectangular range of sectors
        for c in range(start_col, end_col + 1):
            for r in range(start_row, end_row + 1):
                sector_entities = self.sectors.get((c, r))
                if sector_entities:
                    result.extend(sector_entities)

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
        """
        Finds the nearest entity to a position using the spatial grid.

        Args:
            world (World): The ECS World.
            x (float): Origin X coordinate.
            y (float): Origin Y coordinate.
            component_filter (type | None): Optional component type to filter by.
            max_radius (float): Maximum search radius.
            exclude_ids (set[int] | None): Set of entity IDs to ignore.
            predicate (Callable[[int], bool] | None): Optional custom filter function.

        Returns:
            int: Entity ID, or -1 if none found.
        """
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
        """
        Performs a raycast using the physics engine and returns the first entity hit.

        Args:
            world (World): The ECS World.
            start_x (float): Ray start X.
            start_y (float): Ray start Y.
            end_x (float): Ray end X.
            end_y (float): Ray end Y.
            shape_filter (pymunk.ShapeFilter | None): Optional collision filter.
            exclude_id (int): Entity ID to ignore (usually the raycaster).

        Returns:
            tuple[int, float, float] | None: (entity_id, hit_x, hit_y) or None.
        """
        from .physics import PhysicsSystem
        
        physics_system = world.services.try_get(PhysicsSystem)
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

            # If we hit ourselves (exclude_id), do full query to find next hit
            hits = physics_system.space.segment_query(start_pos, end_pos, 1.0, qfilter)
            for h in sorted(hits, key=lambda x: x.alpha):
                if not h.shape or not h.shape.body or h.shape.sensor:
                    continue
                h_ent_id = self.body_to_entity.get(h.shape.body)
                if h_ent_id is not None and h_ent_id != exclude_id:
                    return (h_ent_id, h.point.x, h.point.y)

        return None


class OccluderMap(SpatialService):
    """
    Specialized SpatialService for entities with Occluder components.
    Allows efficient querying of only occluders in a region.
    """

    pass


class SpatialSystem(System):
    """
    System responsible for keeping the SpatialService updated with entity positions.

    Attributes:
        spatial_service (SpatialService): The main entity sector map.
        occluder_map (OccluderMap): The occluder sector map.
        event_bus (EventBus | None): The event bus.
        cleanup_timer (float): Timer for periodic cleanup.
        cleanup_interval (float): Interval for cleanup in seconds.
        body_to_entity (dict[pymunk.Body, int]): Maintains physics body mappings.
    """

    # World bounds and partitioning defaults
    DEFAULT_WORLD_WIDTH = 4000.0
    DEFAULT_WORLD_HEIGHT = 4000.0
    DEFAULT_SECTOR_SIZE = 500.0

    # Housekeeping
    CLEANUP_INTERVAL = 5.0  # Seconds

    def __init__(
        self,
        event_bus: EventBus | None = None,
        width: float = DEFAULT_WORLD_WIDTH,
        height: float = DEFAULT_WORLD_HEIGHT,
        sector_size: float = DEFAULT_SECTOR_SIZE,
    ):
        """
        Initializes the SpatialSystem.

        Args:
            event_bus (EventBus | None): The event bus.
            width (float): World width.
            height (float): World height.
            sector_size (float): Size of sectors.
        """
        self.spatial_service = SpatialService(width, height, sector_size)
        self.occluder_map = OccluderMap(width, height, sector_size)
        self.event_bus = event_bus
        self._subscribed = False

        # New entity tracking for optimization
        self._new_entities: set[int] = set()
        self._first_run: bool = True

        self.cleanup_timer = 0.0
        self.cleanup_interval = self.CLEANUP_INTERVAL  # Seconds
        self.body_to_entity: dict[pymunk.Body, int] = {}
        self.spatial_service.body_to_entity = self.body_to_entity

        # Reusable set to track processed entities within a single update tick.
        self._processed_entities: set[int] = set()

        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
            from ...engine.events import ComponentRemovedEvent
            self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
            self._subscribed = True

    def initialize(self) -> None:
        """Initialize system and subscribe to events if not already done."""
        if hasattr(self, "ecs_world"):
            self._lazy_init(self.ecs_world)

    def _lazy_init(self, world: World) -> None:
        """Helper to initialize subscriptions with a specific world."""
        if not self._subscribed:
            # Try to get EventBus from world services
            event_bus = world.services.try_get(EventBus)
            if event_bus:
                self.event_bus = event_bus
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
                self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
                from ...engine.events import ComponentRemovedEvent
                self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
                self._subscribed = True
            else:
                # Fallback: If no EventBus, we can't track new entities efficiently.
                # Fallback to full iteration mode.
                self._fallback_mode = True

    def on_component_added(self, event: ComponentAddedEvent) -> None:
        """Handler for component addition."""
        # Track new transforms or occluders to ensure they get added to maps
        if event.component_type == Transform or event.component_type == Occluder:
            self._new_entities.add(event.entity_id)
        elif event.component_type == PhysicsBody:
            self.body_to_entity[event.component.body] = event.entity_id

    def on_component_removed(self, event: ComponentRemovedEvent) -> None:
        """Handler for component removal."""
        if event.component_type == PhysicsBody:
            if event.component and event.component.body in self.body_to_entity:
                del self.body_to_entity[event.component.body]

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        """
        Handler for when an entity is destroyed.

        Args:
            event (EntityDestroyedEvent): The event data.
        """
        self.spatial_service.remove_entity(event.entity_id)
        self.occluder_map.remove_entity(event.entity_id)

    def update(self, world: World, dt: float) -> None:
        """
        Updates entity positions in the SpatialService.

        Optimization:
        Instead of iterating ALL transforms every frame, we only iterate:
        1. Newly created entities (via ComponentAddedEvent or _first_run)
        2. Entities that are likely to move (Velocity, PhysicsBody, Mount, etc.)
        3. Static entities are skipped after initial processing.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Ensure lazy init
        if not self._subscribed:
            self._lazy_init(world)

        # Register map as service if not already.
        if not world.services.try_get(SpatialService):
            world.services.register(self.spatial_service, SpatialService)
        if not world.services.try_get(OccluderMap):
            world.services.register(self.occluder_map, OccluderMap)

        # Fallback Mode: Check all entities if EventBus is missing (for legacy tests)
        if hasattr(self, "_fallback_mode") and self._fallback_mode:
            for entity, (transform,) in world.get_components_tuple(Transform):
                moved = transform.x != transform.prev_x or transform.y != transform.prev_y
                if moved or entity not in self.spatial_service.entity_sectors:
                    self.spatial_service.update_entity(entity, transform.x, transform.y)

                if world.has_component(entity, Occluder):
                    if moved or entity not in self.occluder_map.entity_sectors:
                        self.occluder_map.update_entity(entity, transform.x, transform.y)

            # Periodic cleanup still needed
            self.cleanup_timer += dt
            if self.cleanup_timer >= self.cleanup_interval:
                self.cleanup_timer = 0.0
                self.cleanup_dead_entities(world)
            return

        # 1. Handle First Run - Full Scan
        # Catches entities created before system initialization or if events were missed
        if self._first_run:
            for entity, (transform,) in world.get_components_tuple(Transform):
                self.spatial_service.update_entity(entity, transform.x, transform.y)
                if world.has_component(entity, Occluder):
                    self.occluder_map.update_entity(entity, transform.x, transform.y)
            self._first_run = False
            self._new_entities.clear()  # Clear duplicates

        # 2. Process New Entities (Added since last frame)
        if self._new_entities:
            for entity in self._new_entities:
                transform = world.try_get_component(entity, Transform)
                if transform:
                    self.spatial_service.update_entity(entity, transform.x, transform.y)
                    if world.has_component(entity, Occluder):
                        self.occluder_map.update_entity(entity, transform.x, transform.y)
            self._new_entities.clear()

        # 3. Process Moving Entities
        # Reuse the instance set to avoid per-frame allocation.
        self._processed_entities.clear()

        def check_and_update(entity: int, transform: Transform) -> None:
            if entity in self._processed_entities:
                return
            self._processed_entities.add(entity)

            # Check for movement
            if transform.x != transform.prev_x or transform.y != transform.prev_y:
                self.spatial_service.update_entity(entity, transform.x, transform.y)

                # Update OccluderMap if present
                if world.has_component(entity, Occluder):
                    self.occluder_map.update_entity(entity, transform.x, transform.y)

        # Iterate dynamic groups

        # Velocity (Kinematic/Dynamic movement)
        for ent, (t, _) in world.get_components_tuple(Transform, Velocity):
            check_and_update(ent, t)

        # PhysicsBody (Pymunk bodies, skip static ones)
        for ent, (t, body) in world.get_components_tuple(Transform, PhysicsBody):
            if body.body.body_type != pymunk.Body.STATIC:
                check_and_update(ent, t)

        # MovementController (Logic controlled movement)
        for ent, (t, _) in world.get_components_tuple(Transform, MovementController):
            check_and_update(ent, t)

        # Mounts (Attached entities move with parents)
        for ent, (t, mount) in world.get_components_tuple(Transform, Mount):
            if mount.parent_id != -1:
                check_and_update(ent, t)

        # Floating Text (Visual movement)
        for ent, (t, _) in world.get_components_tuple(Transform, FloatingText):
            check_and_update(ent, t)

        # Periodic cleanup of dead entities
        self.cleanup_timer += dt
        if self.cleanup_timer >= self.cleanup_interval:
            self.cleanup_timer = 0.0
            self.cleanup_dead_entities(world)

    def cleanup_dead_entities(self, world: World) -> None:
        """
        Removes entities from SpatialService that no longer exist in the world or have no Transform.

        Args:
            world (World): The ECS World.
        """
        # Cleanup main sector map
        to_remove = []
        for entity_id in self.spatial_service.entity_sectors.keys():
            if not world.has_component(entity_id, Transform):
                to_remove.append(entity_id)

        for entity_id in to_remove:
            self.spatial_service.remove_entity(entity_id)

        # Cleanup occluder map
        to_remove_occluder = []
        for entity_id in self.occluder_map.entity_sectors.keys():
            if not world.has_component(entity_id, Transform) or not world.has_component(
                entity_id, Occluder
            ):
                to_remove_occluder.append(entity_id)

        for entity_id in to_remove_occluder:
            self.occluder_map.remove_entity(entity_id)
