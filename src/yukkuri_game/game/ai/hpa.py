"""
Hierarchical Pathfinding A* (HPA*) Implementation.

This module implements a two-level hierarchical pathfinding system:

1.  **Abstract Level**: A cluster graph where the game world is divided into
    fixed-size clusters. Entrance nodes are created at traversable boundaries
    between adjacent clusters, connected by inter-cluster and intra-cluster edges.

2.  **Local Level**: Standard A* is used within clusters for fine-grained pathfinding.

The HPA* algorithm workflow:
1.  Divide grid into CLUSTER_SIZE x CLUSTER_SIZE clusters.
2.  Find entrances (walkable transitions) between adjacent clusters.
3.  Create abstract graph nodes at entrance midpoints.
4.  Connect intra-cluster nodes via local A* paths.
5.  For pathfinding: insert temp nodes, search abstract graph, refine to grid path.
6.  Apply string pulling (funnel algorithm) to smooth the final path.

References:
-   "Near Optimal Hierarchical Path-Finding" by Botea, Müller, Schaeffer (2004)
"""

import heapq
import math
from dataclasses import dataclass, field

from .navigation_grid import NavigationGrid


# Cluster size in grid cells. Smaller = more nodes, faster abstract search.
# Larger = fewer nodes, more local A* work. 8 is a balanced default.
CLUSTER_SIZE = 8


@dataclass
class GraphEdge:
    """
    Represents a weighted edge in the abstract cluster graph.

    Attributes:
        target_node_id (str): The ID of the target node this edge connects to.
        weight (float): The cost of traversing this edge (distance * terrain cost).
    """

    target_node_id: str
    weight: float


@dataclass
class GraphNode:
    """
    A node in the abstract cluster graph.

    Nodes are placed at cluster boundary entrances and connected to other
    nodes within the same cluster (intra-cluster) and adjacent clusters
    (inter-cluster).

    Attributes:
        id (str): Unique identifier. Format: "x_y" for permanent, "temp_x_y" for temporary.
        position (tuple[int, int]): Grid coordinates (x, y).
        edges (list[GraphEdge]): List of edges connecting to other nodes.
        cluster_coords (tuple[int, int]): Grid coordinates of the cluster this node belongs to.
    """

    id: str
    position: tuple[int, int]
    edges: list[GraphEdge] = field(default_factory=list)
    cluster_coords: tuple[int, int] = (0, 0)


class AStar:
    """
    Static A* pathfinding utilities.

    Uses octile distance heuristic for 8-directional grid movement.
    """

    @staticmethod
    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
        """
        Computes octile distance heuristic for 8-directional movement.

        Octile distance accounts for diagonal movement being sqrt(2) cost
        while cardinal movements are cost 1.

        Args:
            a (tuple[int, int]): Start position (x, y).
            b (tuple[int, int]): End position (x, y).

        Returns:
            float: Estimated cost.
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    @staticmethod
    def search(
        grid: NavigationGrid,
        start: tuple[int, int],
        goal: tuple[int, int],
        capability: int,
        bounds: tuple[int, int, int, int] | None = None,
    ) -> list[tuple[int, int]] | None:
        """
        Runs A* search.

        Args:
            grid (NavigationGrid): The search grid.
            start (tuple[int, int]): Start position (x, y).
            goal (tuple[int, int]): Goal position (x, y).
            capability (int): Traversal capability mask.
            bounds (tuple[int, int, int, int] | None): Optional search bounds (min_x, min_y, max_x, max_y).

        Returns:
            list[tuple[int, int]] | None: The path from start to goal (inclusive), or None if not found.
        """
        frontier: list[tuple[float, tuple[int, int]]] = []
        heapq.heappush(frontier, (0, start))
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far: dict[tuple[int, int], float] = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == goal:
                break

            x, y = current
            neighbors = [
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
                (x + 1, y + 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x - 1, y - 1),
            ]

            for next_pos in neighbors:
                nx, ny = next_pos

                # Check Bounds
                if bounds:
                    min_x, min_y, max_x, max_y = bounds
                    if not (min_x <= nx <= max_x and min_y <= ny <= max_y):
                        continue

                # Check Grid Walkability
                if not grid.is_walkable(nx, ny, capability):
                    continue

                # Diagonal cost is sqrt(2); straight is 1.
                dist = math.sqrt((nx - x) ** 2 + (ny - y) ** 2)
                base_cost = grid.get_cost(nx, ny)
                new_cost = cost_so_far[current] + (base_cost * dist)

                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + AStar.heuristic(next_pos, goal)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current

        if goal not in came_from:
            return None

        # Reconstruct path
        path = []
        curr: tuple[int, int] | None = goal
        while curr is not None:
            path.append(curr)
            curr = came_from[curr]
        path.reverse()
        return path


class Cluster:
    """
    Represents a rectangular region of the navigation grid.

    Clusters partition the world into CLUSTER_SIZE x CLUSTER_SIZE regions.
    Each cluster tracks entrance nodes at its boundaries that enable
    connections to adjacent clusters.

    Attributes:
        cx (int): Cluster grid X coordinate.
        cy (int): Cluster grid Y coordinate.
        min_x (int): World grid min X (inclusive).
        min_y (int): World grid min Y (inclusive).
        max_x (int): World grid max X (inclusive).
        max_y (int): World grid max Y (inclusive).
        nodes (dict[tuple[int, int], str]): Map of entrance position to node ID.
    """

    def __init__(self, cx: int, cy: int, grid: NavigationGrid):
        """
        Initialize cluster with grid coordinates (cx, cy).

        Args:
            cx (int): Cluster X index.
            cy (int): Cluster Y index.
            grid (NavigationGrid): Reference to the navigation grid.
        """
        self.cx = cx
        self.cy = cy
        self.grid = grid

        # Calculate pixel/grid bounds (clamped to grid dimensions)
        self.min_x = cx * CLUSTER_SIZE
        self.min_y = cy * CLUSTER_SIZE
        self.max_x = min((cx + 1) * CLUSTER_SIZE - 1, grid.width - 1)
        self.max_y = min((cy + 1) * CLUSTER_SIZE - 1, grid.height - 1)

        # Maps grid position -> node ID for entrance nodes in this cluster
        self.nodes: dict[tuple[int, int], str] = {}

    def add_node(self, pos: tuple[int, int], node_id: str) -> None:
        """
        Registers an entrance node within this cluster.

        Args:
            pos (tuple[int, int]): The grid position of the node.
            node_id (str): The unique ID of the node.
        """
        if self.contains(pos):
            self.nodes[pos] = node_id

    def contains(self, pos: tuple[int, int]) -> bool:
        """
        Returns True if the position falls within this cluster's bounds.

        Args:
            pos (tuple[int, int]): The grid position to check.

        Returns:
            bool: True if inside bounds.
        """
        x, y = pos
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


class ClusterGraph:
    """
    Manages the abstract pathfinding graph built from clusters.

    The graph consists of:
    -   Nodes at cluster boundary entrances.
    -   Inter-cluster edges connecting adjacent cluster entrances (weight ~1).
    -   Intra-cluster edges connecting entrances within the same cluster
        (weight = actual A* path cost).
    """

    def __init__(self, grid: NavigationGrid):
        """
        Initialize the cluster graph for the given navigation grid.

        Args:
            grid (NavigationGrid): The navigation grid.
        """
        self.grid = grid
        self.cluster_w = int(math.ceil(grid.width / CLUSTER_SIZE))
        self.cluster_h = int(math.ceil(grid.height / CLUSTER_SIZE))

        # Cluster storage: (cx, cy) -> Cluster
        self.clusters: dict[tuple[int, int], Cluster] = {}

        # Global abstract graph: node ID -> GraphNode
        self.graph_nodes: dict[str, GraphNode] = {}

        self._init_clusters()

    def _init_clusters(self) -> None:
        """Initializes the cluster grid."""
        for cy in range(self.cluster_h):
            for cx in range(self.cluster_w):
                self.clusters[(cx, cy)] = Cluster(cx, cy, self.grid)

    def build_graph(self, capability: int = 1) -> None:
        """
        Full graph build/rebuild. Expensive; prefer incremental updates.

        Args:
            capability (int): Traversal capability mask (default: WALK=1).
        """
        self.graph_nodes.clear()
        for cluster in self.clusters.values():
            cluster.nodes.clear()

        # 1. Create Entrances between adjacent clusters
        for cy in range(self.cluster_h):
            for cx in range(self.cluster_w - 1):
                c1 = self.clusters[(cx, cy)]
                c2 = self.clusters[(cx + 1, cy)]
                border_x = c1.max_x

                self._find_entrances(
                    c1, c2, border_x, is_horizontal=True, capability=capability
                )

        # Vertical edges (North <-> South)
        for cx in range(self.cluster_w):
            for cy in range(self.cluster_h - 1):
                c1 = self.clusters[(cx, cy)]
                c2 = self.clusters[(cx, cy + 1)]
                border_y = c1.max_y

                self._find_entrances(
                    c1, c2, border_y, is_horizontal=False, capability=capability
                )

        # 2. Intra-Cluster Edges (connect nodes within same cluster)
        for cluster in self.clusters.values():
            self._connect_internal_nodes(cluster, capability)

    def _find_entrances(
        self,
        c1: Cluster,
        c2: Cluster,
        border_idx: int,
        is_horizontal: bool,
        capability: int,
    ) -> None:
        """
        Finds and creates entrance nodes along the shared border of two clusters.

        Scans the boundary for contiguous walkable segments (gaps) and places a node
        at the center of each gap.

        Args:
            c1 (Cluster): First cluster.
            c2 (Cluster): Second cluster.
            border_idx (int): The index of the border (x or y coordinate).
            is_horizontal (bool): True if scanning a vertical border (moving along y), False otherwise.
            capability (int): Traversal capability mask.
        """
        # Scan along the common border
        if is_horizontal:
            shared_len = min(c1.max_y, c2.max_y) - max(c1.min_y, c2.min_y) + 1
            start_k = max(c1.min_y, c2.min_y)
        else:
            shared_len = min(c1.max_x, c2.max_x) - max(c1.min_x, c2.min_x) + 1
            start_k = max(c1.min_x, c2.min_x)

        current_gap_start = -1

        for k in range(start_k, start_k + shared_len):
            if is_horizontal:
                pos1 = (border_idx, k)
                pos2 = (border_idx + 1, k)
            else:
                pos1 = (k, border_idx)
                pos2 = (k, border_idx + 1)

            walkable = self.grid.is_walkable(
                pos1[0], pos1[1], capability
            ) and self.grid.is_walkable(pos2[0], pos2[1], capability)

            if walkable:
                if current_gap_start == -1:
                    current_gap_start = k
            else:
                if current_gap_start != -1:
                    self._create_inter_cluster_edge(
                        c1, c2, border_idx, current_gap_start, k - 1, is_horizontal
                    )
                    current_gap_start = -1

        # Final gap
        if current_gap_start != -1:
            self._create_inter_cluster_edge(
                c1,
                c2,
                border_idx,
                current_gap_start,
                start_k + shared_len - 1,
                is_horizontal,
            )

    def _create_inter_cluster_edge(
        self,
        c1: Cluster,
        c2: Cluster,
        border_val: int,
        start_k: int,
        end_k: int,
        is_horizontal: bool,
    ) -> None:
        """
        Creates nodes and an edge connecting two clusters through a specific gap.

        Args:
            c1 (Cluster): First cluster.
            c2 (Cluster): Second cluster.
            border_val (int): The coordinate of the border line.
            start_k (int): Start index of the gap.
            end_k (int): End index of the gap.
            is_horizontal (bool): Orientation of the border scan.
        """
        # Place one node at the midpoint of the gap.
        mid_k = (start_k + end_k) // 2

        if is_horizontal:
            pos1 = (border_val, mid_k)
            pos2 = (border_val + 1, mid_k)
        else:
            pos1 = (mid_k, border_val)
            pos2 = (mid_k, border_val + 1)

        node1 = self._get_or_create_node(c1, pos1)
        node2 = self._get_or_create_node(c2, pos2)

        cost = 1.0  # Adjacent cells.
        node1.edges.append(GraphEdge(node2.id, cost))
        node2.edges.append(GraphEdge(node1.id, cost))

    def _get_or_create_node(self, cluster: Cluster, pos: tuple[int, int]) -> GraphNode:
        """
        Retrieves an existing node at the given position or creates a new one.

        Args:
            cluster (Cluster): The cluster the node belongs to.
            pos (tuple[int, int]): Grid position.

        Returns:
            GraphNode: The requested node.
        """
        if pos in cluster.nodes:
            return self.graph_nodes[cluster.nodes[pos]]

        node_id = f"{pos[0]}_{pos[1]}"
        node = GraphNode(node_id, pos, cluster_coords=(cluster.cx, cluster.cy))
        self.graph_nodes[node_id] = node
        cluster.add_node(pos, node_id)
        return node

    def _connect_internal_nodes(self, cluster: Cluster, capability: int) -> None:
        """
        Connect all node pairs within a cluster via local A*.

        This builds the "intra-cluster" edges, representing traversability across the cluster.

        Args:
            cluster (Cluster): The cluster to process.
            capability (int): Traversal capability mask.
        """
        nodes_in_cluster = list(cluster.nodes.values())

        for i in range(len(nodes_in_cluster)):
            for j in range(i + 1, len(nodes_in_cluster)):
                id1 = nodes_in_cluster[i]
                id2 = nodes_in_cluster[j]
                n1 = self.graph_nodes[id1]
                n2 = self.graph_nodes[id2]

                # Run local A*
                path = AStar.search(
                    self.grid,
                    n1.position,
                    n2.position,
                    capability,
                    bounds=(cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y),
                )

                if path:
                    cost = 0.0
                    for k in range(len(path) - 1):
                        p_a = path[k]
                        p_b = path[k + 1]
                        dist = math.sqrt(
                            (p_a[0] - p_b[0]) ** 2 + (p_a[1] - p_b[1]) ** 2
                        )
                        cost += self.grid.get_cost(p_b[0], p_b[1]) * dist

                    n1.edges.append(GraphEdge(n2.id, cost))
                    n2.edges.append(GraphEdge(n1.id, cost))

    def get_cluster_for_pos(self, pos: tuple[int, int]) -> Cluster | None:
        """
        Returns the cluster containing the given grid position.

        Args:
            pos (tuple[int, int]): Grid coordinates.

        Returns:
            Cluster | None: The cluster instance or None if out of bounds.
        """
        cx = pos[0] // CLUSTER_SIZE
        cy = pos[1] // CLUSTER_SIZE
        return self.clusters.get((cx, cy))

    def insert_temporary_node(
        self, pos: tuple[int, int], capability: int
    ) -> GraphNode | None:
        """
        Temporarily inserts a node (start or goal) into the graph.
        Connects it to all entrances in its cluster via local A*.
        Returns the created node, or None if position is blocked.

        Args:
            pos (tuple[int, int]): Grid position.
            capability (int): Traversal capability mask.

        Returns:
            GraphNode | None: The temporary node or None.
        """
        if not self.grid.is_walkable(pos[0], pos[1], capability):
            return None

        cluster = self.get_cluster_for_pos(pos)
        if not cluster:
            return None

        # Check if node already exists at this position
        if pos in cluster.nodes:
            return self.graph_nodes[cluster.nodes[pos]]

        node_id = f"temp_{pos[0]}_{pos[1]}"
        node = GraphNode(node_id, pos, cluster_coords=(cluster.cx, cluster.cy))

        # Connect to all existing nodes in the cluster
        for existing_node_id in cluster.nodes.values():
            existing_node = self.graph_nodes[existing_node_id]
            path = AStar.search(
                self.grid,
                pos,
                existing_node.position,
                capability,
                bounds=(cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y),
            )
            if path:
                cost = self._calculate_path_cost(path)
                node.edges.append(GraphEdge(existing_node.id, cost))
                existing_node.edges.append(GraphEdge(node.id, cost))

        self.graph_nodes[node_id] = node
        return node

    def remove_temporary_node(self, node: GraphNode) -> None:
        """
        Removes a temporary node and its edges from the graph.

        Args:
            node (GraphNode): The node to remove.
        """
        if node.id not in self.graph_nodes:
            return

        # Remove edges pointing TO this node from other nodes
        for other_node in self.graph_nodes.values():
            other_node.edges = [
                e for e in other_node.edges if e.target_node_id != node.id
            ]

        del self.graph_nodes[node.id]

    def _calculate_path_cost(self, path: list[tuple[int, int]]) -> float:
        """
        Calculate the cost of a path.

        Args:
            path (list[tuple[int, int]]): The path to calculate cost for.

        Returns:
            float: Total path cost.
        """
        cost = 0.0
        for i in range(len(path) - 1):
            p_a = path[i]
            p_b = path[i + 1]
            dist = math.sqrt((p_a[0] - p_b[0]) ** 2 + (p_a[1] - p_b[1]) ** 2)
            cost += self.grid.get_cost(p_b[0], p_b[1]) * dist
        return cost

    def abstract_search(
        self, start_node: GraphNode, goal_node: GraphNode
    ) -> list[str] | None:
        """
        A* search on the abstract graph (cluster entrances).
        Returns a list of node IDs representing the abstract path.

        Args:
            start_node (GraphNode): Starting node.
            goal_node (GraphNode): Goal node.

        Returns:
            list[str] | None: List of node IDs in the path, or None if no path found.
        """
        if start_node.id == goal_node.id:
            return [start_node.id]

        frontier: list[tuple[float, str]] = []
        heapq.heappush(frontier, (0.0, start_node.id))
        came_from: dict[str, str | None] = {start_node.id: None}
        cost_so_far: dict[str, float] = {start_node.id: 0.0}

        while frontier:
            _, current_id = heapq.heappop(frontier)

            if current_id == goal_node.id:
                break

            current_node = self.graph_nodes.get(current_id)
            if not current_node:
                continue

            for edge in current_node.edges:
                next_id = edge.target_node_id
                next_node = self.graph_nodes.get(next_id)
                if not next_node:
                    continue

                new_cost = cost_so_far[current_id] + edge.weight

                if next_id not in cost_so_far or new_cost < cost_so_far[next_id]:
                    cost_so_far[next_id] = new_cost
                    # Heuristic: Euclidean distance between node positions
                    h = AStar.heuristic(next_node.position, goal_node.position)
                    priority = new_cost + h
                    heapq.heappush(frontier, (priority, next_id))
                    came_from[next_id] = current_id

        if goal_node.id not in came_from:
            return None

        # Reconstruct path
        path = []
        curr_id: str | None = goal_node.id
        while curr_id is not None:
            path.append(curr_id)
            curr_id = came_from[curr_id]
        path.reverse()
        return path

    def refine_abstract_path(
        self, abstract_path: list[str], capability: int
    ) -> list[tuple[int, int]] | None:
        """
        Converts abstract path (node IDs) to a detailed grid path.
        For each pair of consecutive nodes, runs local A* to get the detailed segment.

        Args:
            abstract_path (list[str]): List of node IDs.
            capability (int): Traversal capability mask.

        Returns:
            list[tuple[int, int]] | None: Detailed grid path or None.
        """
        if not abstract_path:
            return None

        if len(abstract_path) == 1:
            node = self.graph_nodes.get(abstract_path[0])
            return [node.position] if node else None

        detailed_path: list[tuple[int, int]] = []

        for i in range(len(abstract_path) - 1):
            node_a = self.graph_nodes.get(abstract_path[i])
            node_b = self.graph_nodes.get(abstract_path[i + 1])

            if not node_a or not node_b:
                return None

            # Determine bounds: If same cluster, use cluster bounds. Otherwise, use full grid.
            if node_a.cluster_coords == node_b.cluster_coords:
                cluster = self.clusters.get(node_a.cluster_coords)
                if cluster:
                    bounds = (
                        cluster.min_x,
                        cluster.min_y,
                        cluster.max_x,
                        cluster.max_y,
                    )
                else:
                    bounds = None
            else:
                # Cross-cluster edge: nodes are adjacent, direct connection
                bounds = None

            segment = AStar.search(
                self.grid, node_a.position, node_b.position, capability, bounds=bounds
            )

            if not segment:
                segment = AStar.search(
                    self.grid, node_a.position, node_b.position, capability
                )  # Fallback: unbounded A*.

            if not segment:
                return None

            # Append segment, avoiding duplicates at connection points
            if detailed_path and segment and detailed_path[-1] == segment[0]:
                detailed_path.extend(segment[1:])
            else:
                detailed_path.extend(segment)

        return detailed_path


class StringPuller:
    """Helper for smoothing paths using the Funnel Algorithm / String Pulling."""

    @staticmethod
    def smooth_path(
        path: list[tuple[int, int]], grid: NavigationGrid, capability: int
    ) -> list[tuple[int, int]]:
        """
        Smooths a jagged grid path into a straighter path by 'pulling' the string tight.

        Args:
            path (list[tuple[int, int]]): Input path as list of (x, y) tuples.
            grid (NavigationGrid): Navigation grid.
            capability (int): Traversal capability mask.

        Returns:
            list[tuple[int, int]]: Smoothed path.
        """
        if len(path) <= 2:
            return path

        smoothed_path = [path[0]]
        current_idx = 0

        while current_idx < len(path) - 1:
            # Check backwards from end for longest direct line.
            found_shortcut = False
            for lookahead_idx in range(len(path) - 1, current_idx + 1, -1):
                if StringPuller.has_line_of_sight(
                    grid, path[current_idx], path[lookahead_idx], capability
                ):
                    smoothed_path.append(path[lookahead_idx])
                    current_idx = lookahead_idx
                    found_shortcut = True
                    break

            if not found_shortcut:
                # Should not happen in a valid path, but fallback to next node
                current_idx += 1
                smoothed_path.append(path[current_idx])

        return smoothed_path

    @staticmethod
    def has_line_of_sight(
        grid: NavigationGrid,
        start: tuple[int, int],
        end: tuple[int, int],
        capability: int,
    ) -> bool:
        """
        Checks if a direct line exists between start and end using Bresenham's algorithm.

        Args:
            grid (NavigationGrid): The navigation grid.
            start (tuple[int, int]): Start point.
            end (tuple[int, int]): End point.
            capability (int): Traversal capability mask.

        Returns:
            bool: True if line of sight is clear.
        """
        x0, y0 = start
        x1, y1 = end

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x = int(x0)
        y = int(y0)
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        for _ in range(n):
            if not grid.is_walkable(x, y, capability):
                return False

            if x == x1 and y == y1:
                break

            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx

        return True
