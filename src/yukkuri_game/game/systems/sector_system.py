"""
Module defining the Sector System for efficient spatial partitioning and social propagation.
"""

from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict
import math
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import EntityDestroyedEvent
from ..components import Transform


class SectorMap:
    """
    Manages a grid of sectors for efficient spatial queries.
    Used for Social Propagation (Visual/Auditory) and optimizing other spatial lookups.
    """

    def __init__(self, width: float, height: float, sector_size: float):
        """
        Initializes the SectorMap.

        Args:
            width (float): Total width of the world.
            height (float): Total height of the world.
            sector_size (float): Size of each sector (width/height).
        """
        self.width = width
        self.height = height
        self.sector_size = sector_size

        self.cols = int(math.ceil(width / sector_size))
        self.rows = int(math.ceil(height / sector_size))

        # Stores set of entity IDs per sector index (col, row)
        self.sectors: Dict[Tuple[int, int], Set[int]] = defaultdict(set)

        # Track entity positions to optimize updates
        self.entity_sectors: Dict[int, Tuple[int, int]] = {}

    def get_sector_coords(self, x: float, y: float) -> Tuple[int, int]:
        """
        Returns the (col, row) coordinates for a given world position.
        Clamps to map boundaries.
        """
        col = int(x / self.sector_size)
        row = int(y / self.sector_size)

        # Clamp
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))

        return (col, row)

    def update_entity(self, entity_id: int, x: float, y: float) -> None:
        """
        Updates the entity's position in the sector map.
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
        """
        if entity_id in self.entity_sectors:
            sector = self.entity_sectors[entity_id]
            if entity_id in self.sectors[sector]:
                self.sectors[sector].remove(entity_id)
            del self.entity_sectors[entity_id]

    def get_entities_in_sector(self, col: int, row: int) -> Set[int]:
        """
        Returns all entities in a specific sector.
        """
        return self.sectors.get((col, row), set())

    def get_adjacent_sectors(self, col: int, row: int) -> List[Tuple[int, int]]:
        """
        Returns a list of valid (col, row) tuples for adjacent sectors (including diagonals).
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
    ) -> Set[int]:
        """
        Returns entities based on propagation rules.

        Args:
            x, y: Origin position.
            range_type: "visual" (Same + Adjacent) or "auditory_loud" (Same + Adjacent) or "auditory" (Same).
        """
        col, row = self.get_sector_coords(x, y)
        result = set()

        # Always include current sector
        result.update(self.get_entities_in_sector(col, row))

        if range_type in ["visual", "auditory_loud"]:
            # Include adjacent sectors
            for acol, arow in self.get_adjacent_sectors(col, row):
                result.update(self.get_entities_in_sector(acol, arow))

        return result


class SectorSystem(System):
    """
    System responsible for keeping the SectorMap updated with entity positions.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        width: float = 4000,
        height: float = 4000,
        sector_size: float = 500,
    ):
        self.sector_map = SectorMap(width, height, sector_size)
        self.event_bus = event_bus
        self._subscribed = False

        self.cleanup_timer = 0.0
        self.cleanup_interval = 5.0  # Seconds

        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self._subscribed = True

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        """
        Handler for when an entity is destroyed.
        """
        self.sector_map.remove_entity(event.entity_id)

    def update(self, world: World, dt: float) -> None:
        """
        Updates entity positions in the SectorMap.
        """
        # Lazy subscription if event_bus wasn't provided in init (backward compatibility)
        if not self._subscribed:
            event_bus = world.services.try_get(EventBus)
            if event_bus:
                self.event_bus = event_bus
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
                self._subscribed = True

        # We need to register the map as a service if it's not already
        if not world.services.try_get(SectorMap):
            world.services.register(self.sector_map, SectorMap)

        # Iterate all entities with Transform
        for entity, (transform,) in world.get_components_tuple(Transform):
            self.sector_map.update_entity(entity, transform.x, transform.y)

        # Periodic cleanup of dead entities
        self.cleanup_timer += dt
        if self.cleanup_timer >= self.cleanup_interval:
            self.cleanup_timer = 0.0
            self.cleanup_dead_entities(world)

    def cleanup_dead_entities(self, world: World) -> None:
        """
        Removes entities from SectorMap that no longer exist in the world or have no Transform.
        """
        to_remove = []
        for entity_id in self.sector_map.entity_sectors.keys():
            if not world.has_component(entity_id, Transform):
                to_remove.append(entity_id)

        for entity_id in to_remove:
            self.sector_map.remove_entity(entity_id)
