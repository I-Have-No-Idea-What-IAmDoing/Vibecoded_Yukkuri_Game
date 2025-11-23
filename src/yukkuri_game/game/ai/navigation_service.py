import math
from typing import List, Tuple, Optional
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement
from loguru import logger

class NavigationService:
    """
    Service responsible for pathfinding and maintaining the navigation grid.
    """
    def __init__(self, world_width: int, world_height: int, grid_step_size: int = 50):
        """
        Initializes the NavigationService with a persistent grid.

        Args:
            world_width: The width of the world.
            world_height: The height of the world.
            grid_step_size: The size of each grid cell.
        """
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size

        self.matrix_w = int(math.ceil(world_width / grid_step_size)) + 1
        self.matrix_h = int(math.ceil(world_height / grid_step_size)) + 1

        # Create the persistent grid (all walkable by default)
        self.grid = Grid(width=self.matrix_w, height=self.matrix_h)
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.always)

        logger.info(f"NavigationService initialized with grid size {self.matrix_w}x{self.matrix_h}")

    def update_obstacle(self, x: float, y: float, walkable: bool) -> None:
        """
        Updates the walkability of a specific point in the grid.

        Args:
            x (float): World x coordinate.
            y (float): World y coordinate.
            walkable (bool): Whether the cell is walkable.

        Returns:
            None
        """
        gx = int(round(x / self.grid_step_size))
        gy = int(round(y / self.grid_step_size))

        if 0 <= gx < self.matrix_w and 0 <= gy < self.matrix_h:
             self.grid.node(gx, gy).walkable = walkable

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Finds a path from start to goal using the persistent grid.

        Args:
            start: The starting coordinates (x, y).
            goal: The target coordinates (x, y).

        Returns:
            List[Tuple[float, float]]: A list of points (x, y) representing the path.
        """
        # Clean up the grid from previous runs?
        # The pathfinding library modifies the grid nodes (openset, closedset, etc.) during search.
        # We MUST cleanup the grid before each search if we reuse it.
        self.grid.cleanup()

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

        start_node = self.grid.node(start_x_idx, start_y_idx)
        goal_node = self.grid.node(goal_x_idx, goal_y_idx)

        # If start or goal is not walkable, we might have issues.
        # For now, assume start is always valid. If goal is invalid, find nearest walkable?
        # The library handles unreachable goals by returning empty path or partial path.

        path_nodes, _ = self.finder.find_path(start_node, goal_node, self.grid)

        path: List[Tuple[float, float]] = []

        for node in path_nodes:
            wx = float(node.x * self.grid_step_size)
            wy = float(node.y * self.grid_step_size)
            path.append((wx, wy))

        if not path:
            # Fallback: return empty list or just start
            # If path is empty but start != goal, it means no path found.
            return []

        # Optimize: Replace first node with actual start position if close enough
        # path[0] = start # Actually we want to keep the grid center points usually, but let's stick to original logic

        # Ensure the exact start point is the first element
        path[0] = start

        # Ensure the exact goal point is added if the last point is the goal grid center
        # and it's close enough
        if path[-1] != goal:
            # Check if goal is within world bounds
            if 0 <= goal[0] <= self.world_width and 0 <= goal[1] <= self.world_height:
                path.append(goal)
            else:
                # If goal is out of bounds, we should probably clamp it to the path end (grid edge)
                # or just leave it as is (ending at grid center).
                # For now, let's append the clamped goal if we really want to reach "as close as possible"
                clamped_x = max(0, min(goal[0], self.world_width))
                clamped_y = max(0, min(goal[1], self.world_height))
                if (clamped_x, clamped_y) != path[-1]:
                    path.append((clamped_x, clamped_y))

        return path
