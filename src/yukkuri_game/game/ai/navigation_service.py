"""
Asynchronous HPA* (Hierarchical Pathfinding A*) Navigation Service.

This module provides efficient pathfinding for large game worlds by using a
two-level hierarchy: an abstract cluster graph for global routing and
local A* searches within clusters for fine-grained paths.

Key Features:
- Asynchronous path computation via background worker thread
- Path caching to avoid redundant calculations
- Congestion control to prevent request queue overflow
- Thread-safe grid updates with automatic graph rebuilding
- Deterministic mode for testing and replays
"""

import threading
import queue
import time
import traceback
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from loguru import logger

from .navigation_grid import NavigationGrid
from .navigation_constants import TraversalCapability
from .hpa import ClusterGraph, AStar, StringPuller
from enum import IntEnum


class ObstacleType(IntEnum):
    """Obstacle height classifications affecting traversal."""

    LOW = 0  # Blocks ground movement (WALK) only
    HIGH = 1  # Blocks all movement (WALK, FLY, SWIM)


@dataclass(order=True)
class PathRequest:
    priority: int
    timestamp: float
    entity_id: int
    start: Tuple[int, int] = field(compare=False)
    end: Tuple[int, int] = field(compare=False)
    capabilities: int = field(compare=False)


@dataclass
class PathResult:
    entity_id: int
    path: List[Tuple[float, float]]  # World coordinates
    success: bool
    is_partial: bool = False


class NavigationService:
    """
    Asynchronous HPA* Navigation Service.

    Manages the navigation grid, cluster graph, and background worker thread.
    Uses a two-level hierarchy for efficient pathfinding:

    1. Abstract Level: Cluster graph with inter-cluster edges
    2. Local Level: A* within individual clusters

    Thread Safety:
        - Uses _state_lock for all grid/graph modifications
        - Worker thread holds lock during path processing
        - Main thread must acquire lock for obstacle updates

    Path Caching:
        - Caches abstract paths by (start_cluster, end_cluster, capabilities)
        - Cache invalidated on graph rebuild
    """

    def __init__(
        self,
        world_width: int,
        world_height: int,
        grid_step_size: int = 25,
        deterministic_mode: bool = False,
    ):
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size
        self.deterministic_mode = deterministic_mode

        # 1. Unified Grid
        self.grid = NavigationGrid(world_width, world_height, grid_step_size)

        # 2. HPA* Cluster Graph
        self.cluster_graph = ClusterGraph(self.grid)
        self.cluster_graph.build_graph()

        # 3. Async Logic
        self.request_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()

        # Path cache: (start_cluster, end_cluster, capabilities) -> abstract path IDs
        self._path_cache: dict = {}

        # Dirty flag triggers graph rebuild on next worker cycle.
        self._dirty = False
        self._last_rebuild = 0.0

        self._state_lock = threading.RLock()

        self.use_multiprocessing = False  # Stub for future enhancement

        self._running = True
        self._thread: Optional[threading.Thread] = None

        if not self.deterministic_mode:
            self._thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="NavWorker"
            )
            self._thread.start()

        logger.info(
            f"NavigationService initialized. Grid: {self.grid.width}x{self.grid.height}, Deterministic: {self.deterministic_mode}"
        )

    def __enter__(self) -> "NavigationService":
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager support."""
        self.shutdown()

    def reset(self):
        """Resets the grid and graph."""
        self.grid = NavigationGrid(
            self.world_width, self.world_height, self.grid_step_size
        )
        self.cluster_graph = ClusterGraph(self.grid)
        self.cluster_graph.build_graph()
        with self._state_lock:
            self._path_cache.clear()
            self._dirty = False

    def _start_multiprocessing_worker(self):
        """
        Stub for starting a multiprocessing worker.
        TODO: Implement shared memory grid and request/result pipes.
        """
        if self.use_multiprocessing:
            raise NotImplementedError("Multiprocessing not yet implemented.")

    def shutdown(self):
        """Stops the worker thread."""
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
        start: Tuple[float, float],
        end: Tuple[float, float],
        capabilities: int = TraversalCapability.WALK,
        priority: int = 2,
        timestamp: float | None = None,
    ):
        """
        Queues an asynchronous path request.

        Args:
            entity_id: Requesting entity's ID (for result matching).
            start: World coordinates of starting position.
            end: World coordinates of destination.
            capabilities: Bitfield of TraversalCapability flags.
            priority: Lower value = higher priority (0=urgent, 2=normal).
            timestamp: Request time for deterministic ordering.
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

        if self.deterministic_mode:
            self.request_queue.put(req)
        else:
            self.request_queue.put(req)

    def update(self, current_time: float) -> None:
        """
        Manual update for deterministic mode. Processes all pending requests.
        """
        if not self.deterministic_mode:
            return

        # Handle Graph Rebuilds
        if self._dirty:
            with self._state_lock:
                self.cluster_graph.build_graph()
                self._dirty = False
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

    def get_results(self) -> List[PathResult]:
        """Call this from Main Thread to process completed paths."""
        results = []
        try:
            while True:
                results.append(self.result_queue.get_nowait())
        except queue.Empty:
            pass
        return results

    def _worker_loop(self):
        logger.info("NavWorker thread started.")
        while self._running:
            try:
                # Throttle graph rebuilds to max once per second.
                with self._state_lock:
                    should_rebuild = self._dirty and (
                        time.time() - self._last_rebuild > 1.0
                    )

                if should_rebuild:
                    logger.debug("NavWorker: rebuilding graph...")
                    try:
                        with self._state_lock:
                            self.cluster_graph.build_graph()
                            self._dirty = False
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
                        pass

                    self.result_queue.put(result)
                except Exception as e:
                    logger.exception(f"Error in navigation worker: {e}")
                    self.result_queue.put(PathResult(req.entity_id, [], False))

                self.request_queue.task_done()
            except Exception:
                # Fatal error in loop structure
                time.sleep(1.0)
                logger.error("Navigation worker loop fatal error, retrying...")
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

        Returns:
            PathResult with world-coordinate path on success.
        """
        logger.debug(f"_process_request start: {req.start} -> {req.end}")
        start_pos = req.start
        end_pos = req.end
        capability = req.capabilities

        # Stage 1: Trivial case - already at destination
        if start_pos == end_pos:
            logger.debug("Trivial path found.")
            return PathResult(req.entity_id, [self._to_world(start_pos)], True)

        # Stage 2: Identify clusters for cache lookup
        start_cluster = self.cluster_graph.get_cluster_for_pos(start_pos)
        end_cluster = self.cluster_graph.get_cluster_for_pos(end_pos)

        if start_cluster and end_cluster:
            pass  # Cache lookup handled in cross-cluster section below.

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
        start_node = self.cluster_graph.insert_temporary_node(start_pos, capability)
        end_node = self.cluster_graph.insert_temporary_node(end_pos, capability)

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
                abstract_path = self.cluster_graph.abstract_search(start_node, end_node)

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
                    raw_path = self.cluster_graph.refine_abstract_path(
                        abstract_path, capability
                    )

                if not raw_path:
                    raw_path = AStar.search(
                        self.grid, start_pos, end_pos, capability
                    )  # Fallback.
        finally:
            # Clean up temporary nodes
            for temp_node in temp_nodes:
                self.cluster_graph.remove_temporary_node(temp_node)

        if not raw_path:
            return PathResult(req.entity_id, [], False)

        # Stage 7: String pulling for path smoothing.
        smoothed_path = StringPuller.smooth_path(raw_path, self.grid, capability)

        # Stage 8: Convert grid to world coordinates.
        world_path = [self._to_world(p) for p in smoothed_path]

        return PathResult(req.entity_id, world_path, True)

    def _refine_cached_path(
        self,
        cached_abstract: list,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        capability: int,
    ) -> Optional[List[Tuple[int, int]]]:
        """Refines a cached abstract path for specific start/end positions."""
        if not cached_abstract:
            return None

        # Build full abstract path: start -> cached -> end
        full_path = []

        # Connect start to first cached node
        first_node = self.cluster_graph.graph_nodes.get(cached_abstract[0])
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
            middle_path = self.cluster_graph.refine_abstract_path(
                cached_abstract, capability
            )
            if middle_path:
                # Avoid duplicate at junction
                if full_path and middle_path and full_path[-1] == middle_path[0]:
                    full_path.extend(middle_path[1:])
                else:
                    full_path.extend(middle_path)

        # Connect last cached node to end
        last_node = self.cluster_graph.graph_nodes.get(cached_abstract[-1])
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

    def _to_world(self, grid_pos: Tuple[int, int]) -> Tuple[float, float]:
        return (
            float(grid_pos[0] * self.grid_step_size),
            float(grid_pos[1] * self.grid_step_size),
        )

    def update_obstacle_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        walkable: bool,
        obstacle_type: int = 1,  # Legacy type, unused now? Or map to capability?
    ) -> None:
        """
        Updates the grid.
        For now, ObstacleType.HIGH blocks everything.
        ObstacleType.LOW blocks WALK but allows FLY.
        """
        # Mapping legacy obstacle types to capabilities
        # LOW (0) -> Blocks WALK.
        # HIGH (1) -> Blocks WALK | FLY.

        # If 'walkable' is False, we are BLOCKING.
        # If 'walkable' is True, we are CLEARING the block.

        # We want to clear bits if blocking.
        # But the function name is 'update_obstacle_rect' and arg is 'walkable'.
        # Interpretation: walkable=False means ADD OBSTACLE.

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
            self._dirty = True

    def find_path(
        self, start, end, can_fly=False, timestamp: float | None = None
    ) -> List[Tuple[float, float]]:
        """Blocking synchronous pathfinding for legacy code."""
        logger.debug(f"find_path called: {start} -> {end}")
        req = PathRequest(
            priority=0,
            timestamp=timestamp if timestamp is not None else time.time(),
            entity_id=-1,  # Dummy ID
            start=self._to_grid(start),
            end=self._to_grid(end),
            capabilities=TraversalCapability.FLY
            if can_fly
            else TraversalCapability.WALK,
        )
        # Lock to prevent race with graph rebuild
        with self._state_lock:
            result = self._process_request(req)

        logger.debug(f"find_path finished. Success: {result.success}")
        return result.path if result.success else []

    def _to_grid(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        gx = int(round(pos[0] / self.grid_step_size))
        gy = int(round(pos[1] / self.grid_step_size))
        gx = max(0, min(gx, self.grid.width - 1))
        gy = max(0, min(gy, self.grid.height - 1))
        return (gx, gy)
