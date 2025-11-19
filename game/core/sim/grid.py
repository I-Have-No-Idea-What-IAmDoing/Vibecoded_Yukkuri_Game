"""
Grid-based placement system for items.
"""
from typing import Optional

from game.core.ecs.entity import Entity


class Grid:
    """Represents the placement grid for the tank."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._grid: list[list[Optional[int]]] = [[None for _ in range(width)] for _ in range(height)]

    def can_place(self, x: int, y: int, w: int, h: int) -> bool:
        """Checks if an item of a given size can be placed at the specified location."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        if not (0 <= x + w <= self.width and 0 <= y + h <= self.height):
            return False

        for i in range(y, y + h):
            for j in range(x, x + w):
                if self._grid[i][j] is not None:
                    return False  # Collision
        return True

    def place(self, entity: Entity, x: int, y: int, w: int, h: int):
        """Places an item on the grid."""
        if not self.can_place(x, y, w, h):
            raise ValueError("Cannot place item at the specified location.")

        for i in range(y, y + h):
            for j in range(x, x + w):
                self._grid[i][j] = entity.entity_id

    def remove(self, entity_id: int):
        """Removes an item from the grid."""
        for i in range(self.height):
            for j in range(self.width):
                if self._grid[i][j] == entity_id:
                    self._grid[i][j] = None
