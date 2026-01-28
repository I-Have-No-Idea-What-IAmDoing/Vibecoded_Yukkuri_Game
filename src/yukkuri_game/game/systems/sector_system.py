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

from collections import defaultdict
import math

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import EntityDestroyedEvent
from ..components import Transform, Occluder


class SectorMap:
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
    """

    def __init__(self, width: float, height: float, sector_size: float):
        """
        Initializes the SectorMap.

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


class OccluderMap(SectorMap):
    """
    Specialized SectorMap for entities with Occluder components.
    Allows efficient querying of only occluders in a region.
    """

    pass


class SectorSystem(System):
    """
    System responsible for keeping the SectorMap updated with entity positions.

    Attributes:
        sector_map (SectorMap): The main entity sector map.
        occluder_map (OccluderMap): The occluder sector map.
        event_bus (EventBus | None): The event bus.
        cleanup_timer (float): Timer for periodic cleanup.
        cleanup_interval (float): Interval for cleanup in seconds.
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
        Initializes the SectorSystem.

        Args:
            event_bus (EventBus | None): The event bus.
            width (float): World width.
            height (float): World height.
            sector_size (float): Size of sectors.
        """
        self.sector_map = SectorMap(width, height, sector_size)
        self.occluder_map = OccluderMap(width, height, sector_size)
        self.event_bus = event_bus
        self._subscribed = False

        self.cleanup_timer = 0.0
        self.cleanup_interval = self.CLEANUP_INTERVAL  # Seconds

        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self._subscribed = True

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        """
        Handler for when an entity is destroyed.

        Args:
            event (EntityDestroyedEvent): The event data.
        """
        self.sector_map.remove_entity(event.entity_id)
        self.occluder_map.remove_entity(event.entity_id)

    def update(self, world: World, dt: float) -> None:
        """
        Updates entity positions in the SectorMap.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Lazy subscription if event_bus wasn't provided in init (backward compatibility)
        if not self._subscribed:
            event_bus = world.services.try_get(EventBus)
            if event_bus:
                self.event_bus = event_bus
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
                self._subscribed = True

        # Register map as service if not already.
        if not world.services.try_get(SectorMap):
            world.services.register(self.sector_map, SectorMap)
        if not world.services.try_get(OccluderMap):
            world.services.register(self.occluder_map, OccluderMap)

        # Iterate all entities with Transform
        for entity, (transform,) in world.get_components_tuple(Transform):
            # Optimization: Only update sector map if entity moved or is not yet tracked
            if (
                transform.x != transform.prev_x
                or transform.y != transform.prev_y
                or entity not in self.sector_map.entity_sectors
            ):
                self.sector_map.update_entity(entity, transform.x, transform.y)

        # Update OccluderMap
        for entity, (transform, occluder) in world.get_components_tuple(
            Transform, Occluder
        ):
            if (
                transform.x != transform.prev_x
                or transform.y != transform.prev_y
                or entity not in self.occluder_map.entity_sectors
            ):
                self.occluder_map.update_entity(entity, transform.x, transform.y)

        # Periodic cleanup of dead entities
        self.cleanup_timer += dt
        if self.cleanup_timer >= self.cleanup_interval:
            self.cleanup_timer = 0.0
            self.cleanup_dead_entities(world)

    def cleanup_dead_entities(self, world: World) -> None:
        """
        Removes entities from SectorMap that no longer exist in the world or have no Transform.

        Args:
            world (World): The ECS World.
        """
        # Cleanup main sector map
        to_remove = []
        for entity_id in self.sector_map.entity_sectors.keys():
            if not world.has_component(entity_id, Transform):
                to_remove.append(entity_id)

        for entity_id in to_remove:
            self.sector_map.remove_entity(entity_id)

        # Cleanup occluder map
        to_remove_occluder = []
        for entity_id in self.occluder_map.entity_sectors.keys():
            if not world.has_component(entity_id, Transform) or not world.has_component(
                entity_id, Occluder
            ):
                to_remove_occluder.append(entity_id)

        for entity_id in to_remove_occluder:
            self.occluder_map.remove_entity(entity_id)
