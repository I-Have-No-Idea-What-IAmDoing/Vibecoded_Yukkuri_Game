"""
Behavior System Module.

This system manages the lifecycle and execution of Behavior Trees for entities.
It handles tree creation, destruction, and periodic updates (ticking).

Key features:
    - Round-robin scheduling to distribute AI updates across frames.
    - Tick throttling for distant or stable entities to improve performance.
    - Automatic cleanup of trees for destroyed entities.
"""

from collections import deque

import py_trees
from py_trees.common import Status

from ...engine.ecs import System, World
from ..ai.behavior import create_yukkuri_behavior_tree
from ..components import LODComponent
from ..yukkuri_components import AIState


class BehaviorSystem(System):
    """
    System responsible for ticking Behavior Trees.

    Manages a collection of behavior trees, executing them based on a
    scheduling policy that prioritizes close, active entities and throttles
    distant or stable ones.

    Attributes:
        world_w (float): The width of the world boundary.
        world_h (float): The height of the world boundary.
        trees (dict[int, py_trees.trees.BehaviourTree]): Map of entity IDs to behavior trees.
        update_queue (deque[int]): Queue for round-robin scheduling.
        last_update_times (dict[int, float]): Map of entity IDs to last tick timestamp.
        total_time (float): Accumulated simulation time.
        stable_entities (set[int]): Set of entities currently in a stable state (SUCCESS).
    """

    def __init__(self, world_width: float, world_height: float):
        """
        Initializes the BehaviorSystem.

        Args:
            world_width (float): The width of the world.
            world_height (float): The height of the world.
        """
        self.world_w = world_width
        self.world_h = world_height
        self.trees: dict[int, py_trees.trees.BehaviourTree] = {}

        self.update_queue: deque[int] = deque()
        self.max_updates_per_frame = 10  # Configurable performance definition

        self.last_update_times: dict[int, float] = {}
        self.total_time: float = 0.0

        # Performance Optimization: Tick Throttling
        # Minimum seconds between ticks. 0.1s = 10Hz max per entity.
        self.min_tick_interval: float = 0.1

        # Throttling multiplier for entities in specific states (e.g. Sleeping)
        self.stable_tick_multiplier: float = 3.0
        self.stable_entities: set[int] = set()

    def update(self, world: World, dt: float) -> None:
        """
        Ticks behavior trees using round-robin scheduling and throttling.

        Caps the number of updates per frame to maintain steady frame rates.

        Args:
            world (World): The ECS world instance.
            dt (float): Time delta since last frame.
        """
        self.total_time += dt

        # 1. Detect new entities and add to system
        current_ai_entities = set()
        for entity, (ai,) in world.get_components_tuple(AIState):
            current_ai_entities.add(entity)
            if entity not in self.trees:
                root = create_yukkuri_behavior_tree(
                    entity, world, int(self.world_w), int(self.world_h)
                )
                self.trees[entity] = py_trees.trees.BehaviourTree(root)
                self.trees[entity].setup(timeout=15)
                self.update_queue.append(entity)
                self.last_update_times[entity] = self.total_time

        # 2. Cleanup dead entities
        dead_entities = [e for e in self.trees if e not in current_ai_entities]

        for entity in dead_entities:
            del self.trees[entity]
            if entity in self.last_update_times:
                del self.last_update_times[entity]
            self.stable_entities.discard(entity)
            # Safe to leave in deque; will be skipped in main loop

        # 3. Process Batch with Tick Throttling
        updates_count = 0
        iterations = 0
        skipped_count = 0
        max_queue_checks = len(self.update_queue)

        while (
            updates_count < self.max_updates_per_frame and iterations < max_queue_checks
        ):
            iterations += 1
            if not self.update_queue:
                break

            entity = self.update_queue.popleft()

            # Skip dead entities
            if entity not in self.trees:
                continue

            # --- Tick Throttling Logic ---
            last_time = self.last_update_times.get(entity, self.total_time - 0.1)
            time_since_last_tick = self.total_time - last_time
            required_interval = self.min_tick_interval

            # LOD Scaling
            lod = world.try_get_component(entity, LODComponent)
            if lod:
                if lod.level == 1:  # Medium
                    required_interval *= 2.0
                elif lod.level == 2:  # Low
                    required_interval *= 5.0
                elif lod.level >= 3:  # Culled
                    required_interval *= 10.0

            # State Scaling
            if entity in self.stable_entities:
                required_interval *= self.stable_tick_multiplier

            # Skip if interval not met
            if time_since_last_tick < required_interval:
                self.update_queue.append(entity)
                skipped_count += 1
                if skipped_count >= max_queue_checks:
                    break
                continue

            # Calculate actual AI dt
            entity_dt = time_since_last_tick
            if entity_dt <= 0:
                entity_dt = 0.1

            # Execute Tick
            py_trees.blackboard.Blackboard().set("dt", entity_dt)
            tree = self.trees[entity]
            tree.tick()

            # Post-tick logic
            ai = world.try_get_component(entity, AIState)
            root_status = tree.root.status

            if root_status == Status.SUCCESS:
                self.stable_entities.add(entity)
            elif root_status == Status.RUNNING:
                self.stable_entities.discard(entity)
            # FAILURE implies re-planning needed, do not throttle extra.

            # Reset manual overrides on competition
            if ai and (root_status == Status.SUCCESS or root_status == Status.FAILURE):
                if getattr(ai, "manual_override", False):
                    ai.manual_override = False

            # Update Metadata
            self.last_update_times[entity] = self.total_time
            self.update_queue.append(entity)
            updates_count += 1
