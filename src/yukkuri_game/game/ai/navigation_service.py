"""
Asynchronous HPA* (Hierarchical Pathfinding A*) Navigation Service.

This module provides efficient pathfinding for large game worlds by using a
two-level hierarchy: an abstract cluster graph for global routing and
local A* searches within clusters for fine-grained paths.

Key Features:
-   Asynchronous path computation via background worker thread.
-   Path caching to avoid redundant calculations.
-   Congestion control to prevent request queue overflow.
-   Thread-safe grid updates with automatic graph rebuilding.
-   Deterministic mode for testing and replays.
"""

import queue
import threading
import time
import traceback
import types
from dataclasses import dataclass, field
from enum import IntEnum
from loguru import logger

from .hpa import AStar, ClusterGraph, StringPuller
from .navigation_constants import TraversalCapability
from .navigation_grid import NavigationGrid


class ObstacleType(IntEnum):
    """
    Obstacle height classifications affecting traversal.

    Attributes:
        LOW: Blocks ground movement (WALK) only.
        HIGH: Blocks all movement (WALK, FLY, SWIM).
    """

    LOW = 0
    HIGH = 1


@dataclass(order=True)
class PathRequest:
    """
    State for a pending path request.

    Ordered by priority for processing. Comparers ignore non-priority fields to
    maintain stable sort order for equal priorities (FIFO for same priority).
    """

    priority: int
    timestamp: float
    entity_id: int
    start: tuple[int, int] = field(compare=False)
    end: tuple[int, int] = field(compare=False)
    capabilities: int = field(compare=False)


@dataclass
class PathResult:
    """Result of a pathfinding request."""

    entity_id: int
    path: list[tuple[float, float]]  # World coordinates
    success: bool
    is_partial: bool = False


class NavigationService:
    """
    Asynchronous HPA* Navigation Service.

    Manages the navigation grid, cluster graph, and background worker thread.
    Uses a two-level hierarchy for efficient pathfinding:
    1.  Abstract Level: Cluster graph with inter-cluster edges.
    2.  Local Level: A* within individual clusters.

    Thread Safety:
        - Uses `_state_lock` for all grid/graph modifications.
        - Worker thread holds lock during path processing and graph rebuilding.
        - Main thread must acquire lock for obstacle updates.

    Attributes:
        world_width (int): Width of the world in pixels.
        world_height (int): Height of the world in pixels.
        grid_step_size (int): Size of each grid cell in pixels.
        deterministic_mode (bool): If True, runs logic synchronously for determinism.
        grid (NavigationGrid): The underlying navigation grid.
        cluster_graphs (dict[int, ClusterGraph]): The hierarchical HPA* graphs.
        request_queue (queue.PriorityQueue): queue for pending PathRequests.
        result_queue (queue.Queue): queue for completed PathResults.
    """

    def __init__(
        self,
        world_width: int,
        world_height: int,
        grid_step_size: int = 25,
        deterministic_mode: bool = False,
    ):
        """
        Initializes the NavigationService.

        Args:
            world_width (int): Width of the world in pixels.
            world_height (int): Height of the world in pixels.
            grid_step_size (int): Size of each grid cell in pixels.
            deterministic_mode (bool): If True, disables worker thread for deterministic execution.
        """
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size
        self.deterministic_mode = deterministic_mode

        # Unified Grid
        self.grid = NavigationGrid(world_width, world_height, grid_step_size)

        # HPA* Cluster Graphs - one per traversal capability
        self.cluster_graphs: dict[int, ClusterGraph] = {}
        for cap in [TraversalCapability.WALK, TraversalCapability.FLY]:
            self.cluster_graphs[cap] = ClusterGraph(self.grid)
            self.cluster_graphs[cap].build_graph(capability=cap)

        # Async Logic
        self.request_queue: queue.PriorityQueue[PathRequest] = queue.PriorityQueue()
        self.result_queue: queue.Queue[PathResult] = queue.Queue()

        # Path cache: (start_cluster, end_cluster, capabilities) -> abstract path IDs
        self._path_cache: dict[
            tuple[tuple[int, int], tuple[int, int], int], list[str]
        ] = {}

        # Dirty flag triggers graph rebuild on next worker cycle.
        # _dirty_clusters tracks which clusters need incremental rebuilds.
        self._dirty = False
        self._dirty_clusters: dict[int, set[tuple[int, int]]] = {
            cap: set() for cap in [TraversalCapability.WALK, TraversalCapability.FLY]
        }
        self._last_rebuild = 0.0

        self._state_lock = threading.RLock()

        self.use_multiprocessing = False  # Reserved for future enhancement

        self._running = True
        self._thread: threading.Thread | None = None

        if not self.deterministic_mode:
            self._thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="NavWorker"
            )
            self._thread.start()

        logger.info(
            f"NavigationService initialized. Grid: {self.grid.width}x{self.grid.height}, Deterministic: {self.deterministic_mode}"
        )

    def __enter__(self) -> "NavigationService":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit; handles shutdown."""
        self.shutdown()

    def reset(self) -> None:
        """Resets the grid and graph to their initial state."""
        self.grid = NavigationGrid(
            self.world_width, self.world_height, self.grid_step_size
        )
        self.cluster_graphs.clear()
        for cap in [TraversalCapability.WALK, TraversalCapability.FLY]:
            self.cluster_graphs[cap] = ClusterGraph(self.grid)
            self.cluster_graphs[cap].build_graph(capability=cap)
        with self._state_lock:
            self._path_cache.clear()
            self._dirty = False
            self._dirty_clusters = {
                cap: set() for cap in [TraversalCapability.WALK, TraversalCapability.FLY]
            }

    def get_graph(self, capability: int) -> ClusterGraph:
        """
        Returns the appropriate cluster graph for the given capability.

        Args:
            capability (int): Bitfield of TraversalCapability flags.

        Returns:
            ClusterGraph: The graph for the requested capability.
        """
        if capability & TraversalCapability.FLY:
            return self.cluster_graphs[TraversalCapability.FLY]
        return self.cluster_graphs[TraversalCapability.WALK]

    def shutdown(self) -> None:
        """Stops the background worker thread."""
        logger.info(
            f"NavigationService shutdown called. Thread alive: {self._thread.is_alive() if self._thread else False}"
        )
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            logger.info("NavigationService thread joined.")
        else:
            logger.info("NavigationService thread was already dead.")

    def request_path(
        self,
        entity_id: int,
        start: tuple[float, float],
        end: tuple[float, float],
        capabilities: int = TraversalCapability.WALK,
        priority: int = 2,
        timestamp: float | None = None,
    ) -> None:
        """
        Queues an asynchronous path request.

        Args:
            entity_id (int): Requesting entity's ID (for result matching).
            start (tuple[float, float]): World coordinates of starting position.
            end (tuple[float, float]): World coordinates of destination.
            capabilities (int): Bitfield of TraversalCapability flags.
            priority (int): Lower value = higher priority (0=urgent, 2=normal).
            timestamp (float | None): Request time for deterministic ordering.
        """
        # Drop low-priority requests when queue is congested.
        if self.request_queue.qsize() > 50 and priority > 2:
            return

        # Convert world to grid coords
        gx1 = int(round(start[0] / self.grid_step_size))
        gy1 = int(round(start[1] / self.grid_step_size))
        gx2 = int(round(end[0] / self.grid_step_size))
        gy2 = int(round(end[1] / self.grid_step_size))

        # Clamp to grid bounds.
        gx1 = max(0, min(gx1, self.grid.width - 1))
        gy1 = max(0, min(gy1, self.grid.height - 1))
        gx2 = max(0, min(gx2, self.grid.width - 1))
        gy2 = max(0, min(gy2, self.grid.height - 1))

        # Use provided timestamp or current time (non-deterministic fallback)
        req_time = timestamp if timestamp is not None else time.time()

        req = PathRequest(
            priority=priority,
            timestamp=req_time,
            entity_id=entity_id,
            start=(gx1, gy1),
            end=(gx2, gy2),
            capabilities=capabilities,
        )

        self.request_queue.put(req)

    def update(self, current_time: float) -> None:
        """
        Manual update for deterministic mode. Processes all pending requests synchronously.

        Args:
            current_time (float): Current game time.
        """
        if not self.deterministic_mode:
            return

        # Handle Graph Rebuilds (incremental where possible)
        if self._dirty:
            with self._state_lock:
                for cap, graph in self.cluster_graphs.items():
                    dirty_for_cap = self._dirty_clusters.get(cap, set())
                    if dirty_for_cap:
                        graph.rebuild_clusters(dirty_for_cap, capability=cap)
                    else:
                        # Fallback: full rebuild if no cluster info available
                        graph.build_graph(capability=cap)
                self._dirty = False
                for cap in self._dirty_clusters:
                    self._dirty_clusters[cap].clear()
                self._last_rebuild = current_time
                self._path_cache.clear()

        # Process all Pending Requests
        while not self.request_queue.empty():
            try:
                req: PathRequest = self.request_queue.get_nowait()
                result = self._process_request(req)
                self.result_queue.put(result)
                self.request_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error in navigation update: {e}")
                traceback.print_exc()

    def get_results(self) -> list[PathResult]:
        """
        Retrieves all completed path results from the queue.

        This method should be called from the Main Thread.

        Returns:
            list[PathResult]: A list of completed path results.
        """
        results = []
        try:
            while True:
                results.append(self.result_queue.get_nowait())
        except queue.Empty:
            pass
        return results

    def _worker_loop(self) -> None:
        """Main loop for the background worker thread."""
        logger.info("NavWorker thread started.")
        while self._running:
            try:
                # Throttle graph rebuilds to max once per second.
                with self._state_lock:
                    should_rebuild = self._dirty and (
                        time.time() - self._last_rebuild > 1.0
                    )
                    # Snapshot and clear dirty clusters while holding the lock
                    if should_rebuild:
                        dirty_snapshot: dict[int, set[tuple[int, int]]] = {
                            cap: set(clusters)
                            for cap, clusters in self._dirty_clusters.items()
                        }
                        for cap in self._dirty_clusters:
                            self._dirty_clusters[cap].clear()
                        self._dirty = False

                if should_rebuild:
                    logger.debug("NavWorker: rebuilding graph (incremental)...")
                    try:
                        with self._state_lock:
                            for cap, graph in self.cluster_graphs.items():
                                dirty_for_cap = dirty_snapshot.get(cap, set())
                                if dirty_for_cap:
                                    graph.rebuild_clusters(
                                        dirty_for_cap, capability=cap
                                    )
                                else:
                                    # Fallback: full rebuild (e.g. after reset)
                                    graph.build_graph(capability=cap)
                            self._last_rebuild = time.time()
                            self._path_cache.clear()  # Invalidate cache
                        logger.debug("NavWorker: graph rebuild complete.")
                    except Exception as e:
                        logger.error(f"Graph rebuild failed: {e}")
                        traceback.print_exc()

                try:
                    # Wait for request (timeout to allow checking self._running)
                    req: PathRequest = self.request_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                try:
                    logger.debug(f"NavWorker: Processing request {req.entity_id}")
                    start_time = time.perf_counter()
                    # Hold lock during A* to prevent grid modification mid-search.
                    with self._state_lock:
                        result = self._process_request(req)
                    duration = time.perf_counter() - start_time
                    logger.debug(
                        f"NavWorker: Request {req.entity_id} processed in {duration:.4f}s"
                    )

                    if duration > 0.01:  # Log slow paths > 10ms.
                        logger.warning(
                            f"NavWorker: Slow path for entity {req.entity_id}: "
                            f"{duration * 1000:.1f}ms"
                        )

                    self.result_queue.put(result)
                except Exception as e:
                    logger.exception(f"Error in navigation worker: {e}")
                    self.result_queue.put(PathResult(req.entity_id, [], False))

                self.request_queue.task_done()
            except Exception:
                # Fatal error in loop structure
                logger.exception("Navigation worker loop fatal error, retrying...")
                time.sleep(1.0)
        logger.info("NavigationService worker loop exited.")

    def _process_request(self, req: PathRequest) -> PathResult:
        """
        Processes a single path request through the HPA* pipeline.

        Pipeline stages:
        1. Trivial path check (start == end)
        2. Cache lookup for previously computed abstract paths
        3. Same-cluster optimization (local A* only)
        4. Cross-cluster search (abstract A* + refinement)
        5. String pulling for path smoothing
        6. World coordinate conversion

        Args:
            req (PathRequest): The request to process.

        Returns:
            PathResult: The result containing the calculated path (world coordinates)
            and success status.
        """
        logger.debug(f"_process_request start: {req.start} -> {req.end}")
        start_pos = req.start
        end_pos = req.end
        capability = req.capabilities

        # Select appropriate graph for this capability
        graph = self.get_graph(capability)

        # Stage 1: Trivial case - already at destination
        if start_pos == end_pos:
            logger.debug("Trivial path found.")
            return PathResult(req.entity_id, [self._to_world(start_pos)], True)

        # Stage 2: Identify clusters for cache lookup
        start_cluster = graph.get_cluster_for_pos(start_pos)
        end_cluster = graph.get_cluster_for_pos(end_pos)

        # Stage 2.5: Check path cache for cross-cluster paths
        if start_cluster and end_cluster and start_cluster != end_cluster:
            cache_key = (
                (start_cluster.cx, start_cluster.cy),
                (end_cluster.cx, end_cluster.cy),
                capability,
            )
            with self._state_lock:
                cached_abstract = self._path_cache.get(cache_key)

            if cached_abstract:
                logger.debug(f"Cache hit for {cache_key}")
                raw_path = self._refine_cached_path(
                    cached_abstract, start_pos, end_pos, capability
                )
                if raw_path:
                    smoothed = StringPuller.smooth_path(raw_path, self.grid, capability)
                    return PathResult(
                        req.entity_id, [self._to_world(p) for p in smoothed], True
                    )
                else:
                    logger.debug("Cached path refinement failed, falling through.")

        # Stage 3: Same-cluster optimization (local A* only).
        if start_cluster and end_cluster and start_cluster == end_cluster:
            logger.debug(f"Same cluster search: {start_cluster.cx},{start_cluster.cy}")
            # Local A* within cluster
            raw_path = AStar.search(
                self.grid,
                start_pos,
                end_pos,
                capability,
                bounds=(
                    start_cluster.min_x,
                    start_cluster.min_y,
                    start_cluster.max_x,
                    start_cluster.max_y,
                ),
            )
            logger.debug(f"Local A* result: {raw_path}")
            if raw_path:
                smoothed = StringPuller.smooth_path(raw_path, self.grid, capability)
                logger.debug(f"Smoothed path: {smoothed}")
                return PathResult(
                    req.entity_id, [self._to_world(p) for p in smoothed], True
                )

        logger.debug("Cross-cluster search needed (or local failed).")

        # Stage 4: Insert temporary nodes for start/goal positions.
        start_node = graph.insert_temporary_node(start_pos, capability)
        end_node = graph.insert_temporary_node(end_pos, capability)

        temp_nodes = []
        if start_node and start_node.id.startswith("temp_"):
            temp_nodes.append(start_node)
        if end_node and end_node.id.startswith("temp_"):
            temp_nodes.append(end_node)

        raw_path = None

        try:
            if not start_node or not end_node:
                raw_path = AStar.search(
                    self.grid, start_pos, end_pos, capability
                )  # Direct fallback.
            else:
                # Stage 5: Abstract A* on cluster graph.
                abstract_path = graph.abstract_search(start_node, end_node)

                if abstract_path:
                    # Cache the abstract path (without temp nodes)
                    if start_cluster and end_cluster:
                        cache_key = (
                            (start_cluster.cx, start_cluster.cy),
                            (end_cluster.cx, end_cluster.cy),
                            capability,
                        )
                        # Store only permanent node IDs
                        permanent_abstract = [
                            nid for nid in abstract_path if not nid.startswith("temp_")
                        ]
                        if len(permanent_abstract) >= 2:
                            with self._state_lock:
                                self._path_cache[cache_key] = permanent_abstract

                    # Stage 6: Refine abstract path with local A* segments.
                    raw_path = graph.refine_abstract_path(abstract_path, capability)

                if not raw_path:
                    raw_path = AStar.search(
                        self.grid, start_pos, end_pos, capability
                    )  # Fallback.
        finally:
            # Clean up temporary nodes
            for temp_node in temp_nodes:
                graph.remove_temporary_node(temp_node)

        if not raw_path:
            return PathResult(req.entity_id, [], False)

        # Stage 7: String pulling for path smoothing.
        smoothed_path = StringPuller.smooth_path(raw_path, self.grid, capability)

        # Stage 8: Convert grid to world coordinates.
        world_path = [self._to_world(p) for p in smoothed_path]

        return PathResult(req.entity_id, world_path, True)

    def _refine_cached_path(
        self,
        cached_abstract: list[str],
        start_pos: tuple[int, int],
        end_pos: tuple[int, int],
        capability: int,
    ) -> list[tuple[int, int]] | None:
        """
        Refines a cached abstract path for specific start/end positions.

        Connects the start position to the first cached node, and the last
        cached node to the end position, reusing the cached middle section.

        Args:
            cached_abstract (list[str]): The abstract path from cache.
            start_pos (tuple[int, int]): Start position.
            end_pos (tuple[int, int]): End position.
            capability (int): Traversal capability.

        Returns:
            list[tuple[int, int]] | None: The refined path or None.
        """
        if not cached_abstract:
            return None

        # Select appropriate graph for this capability
        graph = self.get_graph(capability)

        # Build full abstract path: start -> cached -> end
        full_path: list[tuple[int, int]] = []

        # Connect start to first cached node
        first_node = graph.graph_nodes.get(cached_abstract[0])
        if not first_node:
            return None

        start_segment = AStar.search(
            self.grid, start_pos, first_node.position, capability
        )
        if not start_segment:
            return None
        full_path.extend(start_segment)

        # Refine the cached abstract path
        if len(cached_abstract) > 1:
            middle_path = graph.refine_abstract_path(cached_abstract, capability)
            if middle_path:
                # Avoid duplicate at junction
                if full_path and middle_path and full_path[-1] == middle_path[0]:
                    full_path.extend(middle_path[1:])
                else:
                    full_path.extend(middle_path)

        # Connect last cached node to end
        last_node = graph.graph_nodes.get(cached_abstract[-1])
        if not last_node:
            return None

        end_segment = AStar.search(self.grid, last_node.position, end_pos, capability)
        if not end_segment:
            return None

        if full_path and end_segment and full_path[-1] == end_segment[0]:
            full_path.extend(end_segment[1:])
        else:
            full_path.extend(end_segment)

        return full_path

    def _to_world(self, grid_pos: tuple[int, int]) -> tuple[float, float]:
        """
        Converts grid coordinates to world coordinates.

        Args:
            grid_pos (tuple[int, int]): Grid coordinates.

        Returns:
            tuple[float, float]: World coordinates.
        """
        res = (
            float(grid_pos[0] * self.grid_step_size),
            float(grid_pos[1] * self.grid_step_size),
        )
        return res

    def update_obstacle_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        walkable: bool,
        obstacle_type: int = 1,
    ) -> None:
        """
        Updates the grid map with an obstacle or clearance.

        Args:
            x (float): X position in world coords.
            y (float): Y position in world coords.
            width (float): Width in world coords.
            height (float): Height in world coords.
            walkable (bool): If True, area becomes walkable. If False, it becomes blocked.
            obstacle_type (int): ObstacleType enum value (LOW=blocks walk, HIGH=blocks all).
        """
        block_mask = 0
        if obstacle_type == 0:  # LOW
            block_mask = TraversalCapability.WALK
        else:  # HIGH
            block_mask = (
                TraversalCapability.WALK
                | TraversalCapability.FLY
                | TraversalCapability.SWIM
            )

        # grid.update_obstacle_rect expects 'is_blocking' and 'block_mask'
        is_blocking = not walkable

        with self._state_lock:  # Lock to protect grid from worker thread.
            self.grid.update_obstacle_rect(x, y, width, height, is_blocking, block_mask)

            # Compute which clusters are affected so we can rebuild only those.
            half_w = width / 2
            half_h = height / 2
            min_gx = int((x - half_w) / self.grid_step_size)
            max_gx = int((x + half_w) / self.grid_step_size) + 1
            min_gy = int((y - half_h) / self.grid_step_size)
            max_gy = int((y + half_h) / self.grid_step_size) + 1

            from .hpa import CLUSTER_SIZE

            min_cx = min_gx // CLUSTER_SIZE
            max_cx = max_gx // CLUSTER_SIZE
            min_cy = min_gy // CLUSTER_SIZE
            max_cy = max_gy // CLUSTER_SIZE

            affected: set[tuple[int, int]] = set()
            for cx in range(min_cx, max_cx + 1):
                for cy in range(min_cy, max_cy + 1):
                    affected.add((cx, cy))

            # If the obstacle blocks WALK, mark WALK graph dirty.
            # If it blocks FLY as well, mark FLY graph dirty.
            for cap in [TraversalCapability.WALK, TraversalCapability.FLY]:
                if block_mask & cap:
                    self._dirty_clusters[cap].update(affected)

            self._dirty = True

    def _to_grid(self, pos: tuple[float, float]) -> tuple[int, int]:
        """
        Converts world coordinates to grid coordinates.

        Args:
            pos (tuple[float, float]): World coordinates.

        Returns:
            tuple[int, int]: Grid coordinates.
        """
        gx = int(round(pos[0] / self.grid_step_size))
        gy = int(round(pos[1] / self.grid_step_size))
        gx = max(0, min(gx, self.grid.width - 1))
        gy = max(0, min(gy, self.grid.height - 1))
        return (gx, gy)
