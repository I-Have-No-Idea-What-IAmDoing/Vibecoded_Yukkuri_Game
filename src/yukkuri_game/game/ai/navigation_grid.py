import math
from dataclasses import dataclass

import numpy as np

from .navigation_constants import TerrainType, TraversalCapability


@dataclass(slots=True)
class NavNode:
    position: tuple[int, int]
    access_mask: int
    cost: float = 1.0


class NavigationGrid:
    """
    A unified navigation grid using numpy for storage.
    Stores traversal capabilities (bitmask) and movement costs.
    """

    def __init__(self, world_width: int, world_height: int, grid_step_size: int = 25):
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size

        self.width = int(math.ceil(world_width / grid_step_size)) + 1
        self.height = int(math.ceil(world_height / grid_step_size)) + 1

        # Grid storage:
        # access_mask: uint8 (TraversalCapability bitmask)
        # cost: float32 (Movement cost)
        self.cells = np.zeros(
            (self.width, self.height), dtype=[("access_mask", "u1"), ("cost", "f4")]
        )

        # Initialize default values
        # Default: All capabilities (WALK | FLY | SWIM currently not strictly separate in bits,
        # but locally we want default walkable).
        # Actually default should be 0 or all?
        # In the old system, everything was walkable by default.
        # Here, let's assume everything is ground-walkable and air-flyable by default unless blocked.
        # But usually we strictly define blocking.
        # Let's set default to fully traversable.
        default_mask = TraversalCapability.WALK | TraversalCapability.FLY
        self.cells["access_mask"] = default_mask
        self.cells["cost"] = TerrainType.GRASS.value  # Default cost

    def get_node(self, x: int, y: int) -> NavNode | None:
        """
        Returns a NavNode object for the given grid coordinates.

        Args:
            x (int): Grid X coordinate.
            y (int): Grid Y coordinate.

        Returns:
            NavNode | None: The node if coordinates are valid, else None.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            cell = self.cells[x, y]
            return NavNode(
                position=(x, y), access_mask=cell["access_mask"], cost=cell["cost"]
            )
        return None

    def set_obstacle(self, x: int, y: int, mask: int, cost: float = 1.0) -> None:
        """
        Sets the obstacle mask and cost at the given coordinates.

        Args:
            x (int): Grid X coordinate.
            y (int): Grid Y coordinate.
            mask (int): Traversal capability mask.
            cost (float): Movement cost. Defaults to 1.0.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[x, y]["access_mask"] = mask
            self.cells[x, y]["cost"] = cost

    def update_obstacle_rect(
        self,
        world_x: float,
        world_y: float,
        width: float,
        height: float,
        is_blocking: bool,
        block_mask: int,  # Bits to set/clear. If blocking, we CLEAR these bits from access_mask.
    ) -> None:
        """
        Updates a rectangular area.

        If is_blocking is True, the bits in block_mask are CLEARED (removed from allowed capabilities).
        If is_blocking is False, the bits in block_mask are SET (added to allowed capabilities).

        Args:
            world_x (float): Center X in world coordinates.
            world_y (float): Center Y in world coordinates.
            width (float): Width in world units.
            height (float): Height in world units.
            is_blocking (bool): True to remove capabilities (block), False to add (clear).
            block_mask (int): The capability bits to modify.
        """
        half_w = width / 2
        half_h = height / 2

        min_gx = int(math.ceil((world_x - half_w) / self.grid_step_size))
        max_gx = int(math.floor((world_x + half_w) / self.grid_step_size)) + 1
        min_gy = int(math.ceil((world_y - half_h) / self.grid_step_size))
        max_gy = int(math.floor((world_y + half_h) / self.grid_step_size)) + 1

        # Clamp bounds
        min_gx = max(0, min_gx)
        max_gx = min(self.width, max_gx + 1)  # Slice upper bound is exclusive
        min_gy = max(0, min_gy)
        max_gy = min(self.height, max_gy + 1)

        if min_gx < max_gx and min_gy < max_gy:
            view = self.cells["access_mask"][min_gx:max_gx, min_gy:max_gy]
            if is_blocking:
                # Remove capabilities (bitwise AND with inverse of block_mask)
                # But numpy doesn't support &= ~mask directly on views easily if dtype is slightly different,
                # but here it is u1.
                # ~block_mask might be negative in python int, need to ensure u1
                inv_mask = np.uint8(~block_mask & 0xFF)
                np.bitwise_and(view, inv_mask, out=view)
            else:
                # Add capabilities
                np.bitwise_or(view, np.uint8(block_mask), out=view)

    def is_walkable(self, x: int, y: int, capability_mask: int) -> bool:
        """
        Checks if a cell is traversable by an entity with the given capability mask.

        Args:
            x (int): Grid X coordinate.
            y (int): Grid Y coordinate.
            capability_mask (int): The entity's capabilities.

        Returns:
            bool: True if traversable.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            cell_mask = self.cells[x, y]["access_mask"]
            # If any bit overlaps, it is traversable?
            # Or does the cell need to support ALL capabilities required?
            # Usually: The cell defines "what can traverse here".
            # E.g. Cell=WALK. Entity=WALK. (WALK & WALK) > 0 -> OK.
            # Cell=FLY. Entity=WALK. (FLY & WALK) == 0 -> Blocked.
            return bool((cell_mask & capability_mask) > 0)
        return False

    def get_cost(self, x: int, y: int) -> float:
        """
        Gets the movement cost for a cell.

        Args:
            x (int): Grid X coordinate.
            y (int): Grid Y coordinate.

        Returns:
            float: Movement cost. Returns infinity if out of bounds.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[x, y]["cost"]
        return float("inf")
