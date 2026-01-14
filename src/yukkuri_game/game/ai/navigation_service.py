"""
Module for handling navigation and pathfinding.
"""

import math
from enum import Enum
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement
from loguru import logger


class ObstacleType(Enum):
    """Type of obstacle for navigation grid updates."""

    LOW = 0  # Blocks ground units only (fences, small rocks)
    HIGH = 1  # Blocks both ground and flying units (walls, buildings)


class NavigationService:
    """
    Service responsible for pathfinding and maintaining dual-layer navigation grids.

    The service maintains two grids:
    - ground_grid: For ground-based pathfinding (blocked by LOW and HIGH obstacles)
    - air_grid: For flying pathfinding (blocked only by HIGH obstacles)

    Attributes:
        world_width (int): Width of the world in pixels.
        world_height (int): Height of the world in pixels.
        grid_step_size (int): Size of each grid cell in pixels.
        matrix_w (int): Width of the grid in cells.
        matrix_h (int): Height of the grid in cells.
        ground_grid (Grid): The pathfinding grid for ground units.
        air_grid (Grid): The pathfinding grid for flying units.
        finder (AStarFinder): The A* pathfinder instance.
    """

    def __init__(self, world_width: int, world_height: int, grid_step_size: int = 25):
        """
        Initializes the NavigationService with dual persistent grids.

        Args:
            world_width (int): The width of the world.
            world_height (int): The height of the world.
            grid_step_size (int): The size of each grid cell.
        """
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size

        self.matrix_w = int(math.ceil(world_width / grid_step_size)) + 1
        self.matrix_h = int(math.ceil(world_height / grid_step_size)) + 1

        # Create dual persistent grids (all walkable by default)
        self.ground_grid = Grid(width=self.matrix_w, height=self.matrix_h)
        self.air_grid = Grid(width=self.matrix_w, height=self.matrix_h)
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.always)

        # Legacy alias for backwards compatibility
        self.grid = self.ground_grid

        logger.info(
            f"NavigationService initialized with dual grids, size {self.matrix_w}x{self.matrix_h}"
        )

    def update_obstacle(
        self,
        x: float,
        y: float,
        walkable: bool,
        obstacle_type: ObstacleType = ObstacleType.HIGH,
    ) -> None:
        """
        Updates the walkability of a specific point in the appropriate grid(s).

        Args:
            x (float): World x coordinate.
            y (float): World y coordinate.
            walkable (bool): Whether the cell is walkable.
            obstacle_type (ObstacleType): Type of obstacle.
                - LOW: Only blocks ground units.
                - HIGH: Blocks both ground and flying units.

        Returns:
            None
        """
        gx = int(round(x / self.grid_step_size))
        gy = int(round(y / self.grid_step_size))

        if 0 <= gx < self.matrix_w and 0 <= gy < self.matrix_h:
            # Ground grid is always updated
            self.ground_grid.node(gx, gy).walkable = walkable

            # Air grid only blocked by HIGH obstacles
            if obstacle_type == ObstacleType.HIGH:
                self.air_grid.node(gx, gy).walkable = walkable

    def update_obstacle_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        walkable: bool,
        obstacle_type: ObstacleType = ObstacleType.HIGH,
    ) -> None:
        """
        Updates the walkability of a rectangular area in the appropriate grid(s).

        Args:
            x (float): World x coordinate of the center.
            y (float): World y coordinate of the center.
            width (float): Width of the obstacle in world units.
            height (float): Height of the obstacle in world units.
            walkable (bool): Whether the cells are walkable.
            obstacle_type (ObstacleType): Type of obstacle.

        Returns:
            None
        """
        half_w = width / 2
        half_h = height / 2
        
        # Calculate grid bounds
        min_gx = int(round((x - half_w) / self.grid_step_size))
        max_gx = int(round((x + half_w) / self.grid_step_size))
        min_gy = int(round((y - half_h) / self.grid_step_size))
        max_gy = int(round((y + half_h) / self.grid_step_size))
        
        for gx in range(min_gx, max_gx + 1):
            for gy in range(min_gy, max_gy + 1):
                if 0 <= gx < self.matrix_w and 0 <= gy < self.matrix_h:
                    self.ground_grid.node(gx, gy).walkable = walkable
                    if obstacle_type == ObstacleType.HIGH:
                        self.air_grid.node(gx, gy).walkable = walkable

    def reset(self) -> None:
        """
        Resets both grids' walkability to default (all walkable).
        """
        for x in range(self.matrix_w):
            for y in range(self.matrix_h):
                self.ground_grid.node(x, y).walkable = True
                self.air_grid.node(x, y).walkable = True

    def find_path(
        self,
        start: tuple[float, float],
        goal: tuple[float, float],
        can_fly: bool = False,
    ) -> list[tuple[float, float]]:
        """
        Finds a path from start to goal using the appropriate grid.

        Args:
            start (tuple[float, float]): The starting coordinates (x, y).
            goal (tuple[float, float]): The target coordinates (x, y).
            can_fly (bool): If True, use the air grid (ignores low obstacles).

        Returns:
            list[tuple[float, float]]: A list of points (x, y) representing the path.
        """
        # Select the appropriate grid
        grid = self.air_grid if can_fly else self.ground_grid

        # Clean up the grid from previous runs
        grid.cleanup()

        # Convert world coordinates to grid indices
        start_x_idx = int(round(start[0] / self.grid_step_size))
        start_y_idx = int(round(start[1] / self.grid_step_size))

        goal_x_idx = int(round(goal[0] / self.grid_step_size))
        goal_y_idx = int(round(goal[1] / self.grid_step_size))

        # Clamp indices
        start_x_idx = max(0, min(start_x_idx, self.matrix_w - 1))
        start_y_idx = max(0, min(start_y_idx, self.matrix_h - 1))

        goal_x_idx = max(0, min(goal_x_idx, self.matrix_w - 1))
        goal_y_idx = max(0, min(goal_y_idx, self.matrix_h - 1))

        start_node = grid.node(start_x_idx, start_y_idx)
        goal_node = grid.node(goal_x_idx, goal_y_idx)

        path_nodes, _ = self.finder.find_path(start_node, goal_node, grid)

        path: list[tuple[float, float]] = []

        for node in path_nodes:
            wx = float(node.x * self.grid_step_size)
            wy = float(node.y * self.grid_step_size)
            path.append((wx, wy))

        if not path:
            return []

        # Ensure the exact start point is the first element
        path[0] = start

        # Ensure the exact goal point is added if needed
        if path[-1] != goal:
            if 0 <= goal[0] <= self.world_width and 0 <= goal[1] <= self.world_height:
                path.append(goal)
            else:
                clamped_x = max(0, min(goal[0], self.world_width))
                clamped_y = max(0, min(goal[1], self.world_height))
                if (clamped_x, clamped_y) != path[-1]:
                    path.append((clamped_x, clamped_y))

        return path

