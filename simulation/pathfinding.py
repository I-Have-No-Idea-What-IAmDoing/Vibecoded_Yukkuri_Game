import heapq
from typing import List, Tuple, Optional, Any

class Node:
    """A node in the A* pathfinding grid."""
    def __init__(self, parent: Optional['Node'] = None, position: Optional[Tuple[int, int]] = None) -> None:
        self.parent: Optional['Node'] = parent
        self.position: Optional[Tuple[int, int]] = position

        self.g: float = 0  # Cost from start to current node
        self.h: float = 0  # Heuristic cost from current node to end
        self.f: float = 0  # Total cost (g + h)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.position == other.position

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.f < other.f

    def __repr__(self) -> str:
        return f"Node({self.position})"

def astar_pathfind(grid: List[List[Any]], start: Tuple[int, int], end: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    Returns a list of tuples as a path from the given start to the given end in the given grid.
    """
    start_node = Node(None, start)
    end_node = Node(None, end)

    open_list: List[Node] = []
    closed_list: set[Tuple[int, int]] = set()

    heapq.heappush(open_list, start_node)

    while len(open_list) > 0:
        current_node: Node = heapq.heappop(open_list)
        if current_node.position is None: continue
        closed_list.add(current_node.position)

        if current_node == end_node:
            path: List[Tuple[int, int]] = []
            current: Optional[Node] = current_node
            while current is not None:
                if current.position:
                    path.append(current.position)
                current = current.parent
            return path[::-1]  # Return reversed path

        (x, y) = current_node.position
        neighbors: List[Tuple[int, int]] = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]

        for next_pos in neighbors:
            if not (0 <= next_pos[0] < len(grid[0]) and 0 <= next_pos[1] < len(grid)):
                continue

            if grid[next_pos[1]][next_pos[0]] and grid[next_pos[1]][next_pos[0]]['def']['walk_blocking']:
                 continue

            if next_pos in closed_list:
                continue

            new_node = Node(current_node, next_pos)
            new_node.g = current_node.g + 1
            if new_node.position and end_node.position:
                new_node.h = ((new_node.position[0] - end_node.position[0]) ** 2) + \
                             ((new_node.position[1] - end_node.position[1]) ** 2)
            new_node.f = new_node.g + new_node.h

            if any(open_node for open_node in open_list if new_node == open_node and new_node.g > open_node.g):
                continue

            heapq.heappush(open_list, new_node)

    return None # Path not found
