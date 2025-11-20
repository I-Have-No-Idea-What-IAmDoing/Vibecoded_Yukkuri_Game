import heapq
import math
from typing import List, Tuple, Optional

class Pathfinding:
    """
    Provides static methods for pathfinding operations.
    """

    @staticmethod
    def heuristic(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """
        Calculates the Euclidean distance heuristic between two points.

        Args:
            a: The starting point (x, y).
            b: The target point (x, y).

        Returns:
            float: The distance between points a and b.
        """
        return math.hypot(b[0] - a[0], b[1] - a[1])

    @staticmethod
    def get_neighbors(node: Tuple[float, float], grid_w: float, grid_h: float, step: int = 50) -> List[Tuple[float, float]]:
        """
        Generates valid neighboring points on a grid.

        Args:
            node: The current point (x, y).
            grid_w: The width of the grid boundary.
            grid_h: The height of the grid boundary.
            step: The step size between grid points. Defaults to 50.

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
    def find_path(start: Tuple[float, float], goal: Tuple[float, float], grid_w: float, grid_h: float) -> List[Tuple[float, float]]:
        """
        Finds a path from start to goal using the A* algorithm.

        Since the world is continuous, this method discretizes the space into a grid
        to perform the search.

        Args:
            start: The starting coordinates (x, y).
            goal: The target coordinates (x, y).
            grid_w: The width of the world.
            grid_h: The height of the world.

        Returns:
            List[Tuple[float, float]]: A list of points representing the path.
        """
        step = 50
        # Snap start/goal to grid for A*
        start_node: Tuple[float, float] = (float(round(start[0]/step)*step), float(round(start[1]/step)*step))
        goal_node: Tuple[float, float] = (float(round(goal[0]/step)*step), float(round(goal[1]/step)*step))

        frontier: List[Tuple[float, Tuple[float, float]]] = []
        heapq.heappush(frontier, (0.0, start_node))
        came_from: dict[Tuple[float, float], Optional[Tuple[float, float]]] = {}
        cost_so_far: dict[Tuple[float, float], float] = {}
        came_from[start_node] = None
        cost_so_far[start_node] = 0.0

        while frontier:
            _, current = heapq.heappop(frontier)

            if math.hypot(current[0]-goal_node[0], current[1]-goal_node[1]) < step:
                break

            for next_node in Pathfinding.get_neighbors(current, grid_w, grid_h, step):
                new_cost = cost_so_far[current] + math.hypot(next_node[0]-current[0], next_node[1]-current[1])
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + Pathfinding.heuristic(next_node, goal_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        # Reconstruct path
        path_current: Optional[Tuple[float, float]] = goal_node
        # Find closest node in came_from if goal wasn't reached exactly
        if path_current not in came_from:
             # Fallback to closest visited
             path_current = min(came_from.keys(), key=lambda k: Pathfinding.heuristic(k, goal_node))

        path = []
        while path_current is not None and path_current != start_node:
            path.append(path_current)
            path_current = came_from.get(path_current)

        path.append(start_node)
        path.reverse()

        # Append exact goal if different
        if path[-1] != goal:
            path.append(goal)

        return path
