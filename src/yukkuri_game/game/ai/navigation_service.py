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
    LOW = 0  # Blocks WALK
    HIGH = 1  # Blocks WALK | FLY


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
    Manages the unified grid, cluster graph, and a background worker thread for pathfinding.
    """

    def __init__(self, world_width: int, world_height: int, grid_step_size: int = 25):
        self.world_width = world_width
        self.world_height = world_height
        self.grid_step_size = grid_step_size

        # 1. Unified Grid
        self.grid = NavigationGrid(world_width, world_height, grid_step_size)

        # 2. HPA* Cluster Graph
        self.cluster_graph = ClusterGraph(self.grid)
        # Note: We delay building the graph until the first update or explicitly?
        # For now, let's build it immediately assuming empty grid.
        self.cluster_graph.build_graph()

        # 3. Async Logic
        self.request_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()

        # Cache: (start_cluster, end_cluster, capabilities) -> Abstract Path
        # We need to invalidate this when grid changes.
        self._path_cache = {}

        # Dirty flag for graph updates
        self._dirty = False
        self._last_rebuild = 0.0

        # Multiprocessing Support (Stub)
        self.use_multiprocessing = False

        self._running = True
        self._thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="NavWorker"
        )
        self._thread.start()

        logger.info(
            f"NavigationService initialized. Grid: {self.grid.width}x{self.grid.height}"
        )

    def reset(self):
        """Resets the grid and graph."""
        self.grid = NavigationGrid(
            self.world_width, self.world_height, self.grid_step_size
        )
        self.cluster_graph = ClusterGraph(self.grid)
        self.cluster_graph.build_graph()
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
            f"NavigationService shutdown called. Thread alive: {self._thread.is_alive()}"
        )
        self._running = False
        if self._thread.is_alive():
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
    ):
        """Async path request. Puts request into PriorityQueue."""

        # Congestion Control: Drop low priority requests if queue is full
        if self.request_queue.qsize() > 50 and priority > 2:
            return

        # Convert world to grid coords
        gx1 = int(round(start[0] / self.grid_step_size))
        gy1 = int(round(start[1] / self.grid_step_size))
        gx2 = int(round(end[0] / self.grid_step_size))
        gy2 = int(round(end[1] / self.grid_step_size))

        # Clamp
        gx1 = max(0, min(gx1, self.grid.width - 1))
        gy1 = max(0, min(gy1, self.grid.height - 1))
        gx2 = max(0, min(gx2, self.grid.width - 1))
        gy2 = max(0, min(gy2, self.grid.height - 1))

        req = PathRequest(
            priority=priority,
            timestamp=time.time(),
            entity_id=entity_id,
            start=(gx1, gy1),
            end=(gx2, gy2),
            capabilities=capabilities,
        )
        self.request_queue.put(req)

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
        while self._running:
            try:
                # Check dirty flag and rebuild graph if needed
                # Throttle rebuilds to avoid spam (e.g. max once per second)
                if self._dirty and (time.time() - self._last_rebuild > 1.0):
                    try:
                        self.cluster_graph.build_graph()
                        self._dirty = False
                        self._last_rebuild = time.time()
                        self._path_cache.clear()  # Invalidate cache
                    except Exception as e:
                        logger.error(f"Graph rebuild failed: {e}")
                        traceback.print_exc()

                try:
                    # Wait for request (timeout to allow checking self._running)
                    req: PathRequest = self.request_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                try:
                    start_time = time.perf_counter()
                    result = self._process_request(req)
                    duration = time.perf_counter() - start_time

                    # Profiler Hook
                    if duration > 0.01:  # Log slow paths > 10ms
                        pass  # Removed debug log

                    self.result_queue.put(result)
                except Exception as e:
                    logger.error(f"Error in navigation worker: {e}")
                    traceback.print_exc()
                    self.result_queue.put(PathResult(req.entity_id, [], False))

                self.request_queue.task_done()
            except Exception as outer_e:
                print(f"FATAL ERROR in NavWorker: {outer_e}")
                traceback.print_exc()
                # Don't crash the thread, retry?
                time.sleep(1.0)
        logger.info("NavigationService worker loop exited.")
        logger.info("NavigationService worker loop exited.")

    def _process_request(self, req: PathRequest) -> PathResult:
        start_pos = req.start
        end_pos = req.end
        capability = req.capabilities

        # 1. Trivial Case
        if start_pos == end_pos:
            return PathResult(req.entity_id, [self._to_world(start_pos)], True)

        # 2. Check Cache
        start_cluster = self.cluster_graph.get_cluster_for_pos(start_pos)
        end_cluster = self.cluster_graph.get_cluster_for_pos(end_pos)

        if start_cluster and end_cluster:
            cache_key = (
                (start_cluster.cx, start_cluster.cy),
                (end_cluster.cx, end_cluster.cy),
                capability,
            )
            if cache_key in self._path_cache:
                cached_abstract = self._path_cache[cache_key]
                # Refine for this specific start/end
                raw_path = self._refine_cached_path(
                    cached_abstract, start_pos, end_pos, capability
                )
                if raw_path:
                    smoothed = StringPuller.smooth_path(raw_path, self.grid, capability)
                    return PathResult(
                        req.entity_id, [self._to_world(p) for p in smoothed], True
                    )

        # 3. Full HPA* Workflow
        # Check if start and end are in the same cluster (short path)
        if start_cluster and end_cluster and start_cluster == end_cluster:
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
            if raw_path:
                smoothed = StringPuller.smooth_path(raw_path, self.grid, capability)
                return PathResult(
                    req.entity_id, [self._to_world(p) for p in smoothed], True
                )

        # 4. Insert temporary nodes for start and goal
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
                # Fallback to direct grid A*
                raw_path = AStar.search(self.grid, start_pos, end_pos, capability)
            else:
                # 5. Abstract Search (A* on cluster graph)
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
                            self._path_cache[cache_key] = permanent_abstract

                    # 6. Refinement (local A* for each segment)
                    raw_path = self.cluster_graph.refine_abstract_path(
                        abstract_path, capability
                    )

                if not raw_path:
                    # Fallback to direct grid A*
                    raw_path = AStar.search(self.grid, start_pos, end_pos, capability)
        finally:
            # Clean up temporary nodes
            for temp_node in temp_nodes:
                self.cluster_graph.remove_temporary_node(temp_node)

        if not raw_path:
            return PathResult(req.entity_id, [], False)

        # 7. String Pulling (Smoothing)
        smoothed_path = StringPuller.smooth_path(raw_path, self.grid, capability)

        # 8. Convert to World Coords
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

        self.grid.update_obstacle_rect(x, y, width, height, is_blocking, block_mask)
        # Mark dirty to trigger eventual graph rebuild
        self._dirty = True

    # Legacy Compatibility methods
    def find_path(self, start, end, can_fly=False) -> List[Tuple[float, float]]:
        """Blocking synchronous pathfinding for legacy code."""
        # This is dangerous for performance but necessary for transition.
        req = PathRequest(
            priority=0,
            timestamp=time.time(),
            entity_id=-1,  # Dummy ID
            start=self._to_grid(start),
            end=self._to_grid(end),
            capabilities=TraversalCapability.FLY
            if can_fly
            else TraversalCapability.WALK,
        )
        result = self._process_request(req)
        return result.path if result.success else []

    def _to_grid(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        gx = int(round(pos[0] / self.grid_step_size))
        gy = int(round(pos[1] / self.grid_step_size))
        gx = max(0, min(gx, self.grid.width - 1))
        gy = max(0, min(gy, self.grid.height - 1))
        return (gx, gy)
