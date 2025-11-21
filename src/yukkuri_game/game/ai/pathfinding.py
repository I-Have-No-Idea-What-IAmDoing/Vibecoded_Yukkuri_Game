import math
from typing import List, Tuple
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

class Pathfinding:
    """
    Provides static methods for pathfinding operations using the 'pathfinding' library.
    """

    @staticmethod
    def heuristic(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """
        Calculates the Euclidean distance heuristic between two points.

        Kept for backward compatibility/testing, though not used internally by the library wrapper.

        Args:
            a: The first point (x, y).
            b: The second point (x, y).

        Returns:
            float: The Euclidean distance between points a and b.
        """
        return math.hypot(b[0] - a[0], b[1] - a[1])

    @staticmethod
    def get_neighbors(node: Tuple[float, float], grid_w: float, grid_h: float, step: int = 50) -> List[Tuple[float, float]]:
        """
        Generates valid neighboring points on a grid.

        Deprecated: Internal logic is handled by the pathfinding library.
        Kept for backward compatibility/testing.

        Args:
            node: The current point (x, y).
            grid_w: The width of the grid/world.
            grid_h: The height of the grid/world.
            step: The grid step size. Defaults to 50.

        Returns:
            List[Tuple[float, float]]: A list of valid neighbor coordinates.
        """
        x, y = node
        neighbors = [
            (x + step, y), (x - step, y),
            (x, y + step), (x, y - step),
            (x + step, y + step), (x - step, y - step),
            (x + step, y - step), (x - step, y + step)
        ]
        valid = []
        for nx, ny in neighbors:
            if 0 <= nx <= grid_w and 0 <= ny <= grid_h:
                valid.append((nx, ny))
        return valid

    @staticmethod
    def find_path(start: Tuple[float, float], goal: Tuple[float, float], grid_w: float, grid_h: float, step: int = 50) -> List[Tuple[float, float]]:
        """
        Finds a path from start to goal using the A* algorithm from the pathfinding library.

        Args:
            start: The starting coordinates (x, y).
            goal: The target coordinates (x, y).
            grid_w: The width of the world.
            grid_h: The height of the world.
            step: The grid step size. Defaults to 50.

        Returns:
            List[Tuple[float, float]]: A list of points (x, y) representing the path.
        """
        # Determine grid dimensions
        # Adding step to width/height to ensure coverage for edge cases
        matrix_w = int(math.ceil(grid_w / step)) + 1
        matrix_h = int(math.ceil(grid_h / step)) + 1

        # Create a grid (all walkable by default)
        grid = Grid(width=matrix_w, height=matrix_h)

        # Convert world coordinates to grid indices
        start_x_idx = int(round(start[0] / step))
        start_y_idx = int(round(start[1] / step))

        goal_x_idx = int(round(goal[0] / step))
        goal_y_idx = int(round(goal[1] / step))

        # Clamp indices to be within grid bounds
        start_x_idx = max(0, min(start_x_idx, matrix_w - 1))
        start_y_idx = max(0, min(start_y_idx, matrix_h - 1))

        goal_x_idx = max(0, min(goal_x_idx, matrix_w - 1))
        goal_y_idx = max(0, min(goal_y_idx, matrix_h - 1))

        start_node = grid.node(start_x_idx, start_y_idx)
        goal_node = grid.node(goal_x_idx, goal_y_idx)

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)

        # find_path returns path (list of nodes) and runs (number of steps)
        path_nodes, _ = finder.find_path(start_node, goal_node, grid)

        # Convert grid nodes back to world coordinates
        path: List[Tuple[float, float]] = []

        for node in path_nodes:
            wx = float(node.x * step)
            wy = float(node.y * step)
            path.append((wx, wy))

        if not path:
            # Fallback: ensure we return at least start
            path.append(start)

        # Ensure the exact start point is the first element
        path[0] = start

        clamped_goal_x = max(0.0, min(goal[0], grid_w))
        clamped_goal_y = max(0.0, min(goal[1], grid_h))
        clamped_goal = (clamped_goal_x, clamped_goal_y)

        if path[-1] != goal:
             if clamped_goal != path[-1]:
                 path.append(clamped_goal)

        return path
