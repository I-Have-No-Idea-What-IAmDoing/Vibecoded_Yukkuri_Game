"""
Module defining the BehaviorSystem logic.
"""

import py_trees
from py_trees.common import Status
from ...engine.ecs import System, World
from ..components import LODComponent
from ..yukkuri_components import AIState
from ..ai.behavior import create_yukkuri_behavior_tree


class BehaviorSystem(System):
    """
    System responsible for ticking Behavior Trees.

    Attributes:
        world_w (float): The width of the world boundary.
        world_h (float): The height of the world boundary.
        trees (Dict[int, py_trees.trees.BehaviourTree]): A dictionary mapping entity IDs to their behavior trees.
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
        # Round-robin queue for updates
        from collections import deque

        self.update_queue: deque[int] = deque()
        self.max_updates_per_frame = 10  # Tune this based on performance

        self.last_update_times: dict[int, float] = {}
        self.total_time: float = 0.0

        # --- Performance Optimization: Tick Throttling ---
        # Minimum time (seconds) between ticks for the same entity.
        # Reduces CPU load by preventing excessively frequent AI updates.
        self.min_tick_interval: float = 0.1  # 100ms = 10 ticks/sec max per entity

        # Entities in stable states (SUCCESS) are ticked less frequently.
        self.stable_tick_multiplier: float = 3.0  # 3x slower for stable entities
        self.stable_entities: set[int] = set()  # Track entities in stable states

    def update(self, world: World, dt: float) -> None:
        """
        Ticks behavior trees using round-robin scheduling.
        Caps updates to max_updates_per_frame.
        """
        self.total_time += dt

        # 1. Detect new entities and add to system
        # Optimization: Instead of full iteration, we could use events,
        # but get_components_tuple is fast enough for checking existence if we optimized elsewhere.
        # To avoid iterating ALL entities every frame just to find new ones,
        # we can assume the queue covers existing ones.
        # But we need to find *new* ones.
        # Let's rely on a set difference for correctness, or events.
        # For now, let's keep it simple: Iterate all AIState, if not in trees, add.
        # This iteration cost is small compared to ticking.

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
        # Check if any entities in trees are no longer in current_ai_entities
        # This handles both death and component removal
        dead_entities = []
        for entity in self.trees:
            if entity not in current_ai_entities:
                dead_entities.append(entity)

        for entity in dead_entities:
            del self.trees[entity]
            if entity in self.last_update_times:
                del self.last_update_times[entity]
            # Also clean up stable entities tracking
            self.stable_entities.discard(entity)
            # Removing from deque is O(N), so we just skip them during update loop if encountered
            # Or we can rebuild deque if many die. Lazy removal is better usually.

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

            # If entity is dead (removed from trees), skip and don't re-queue
            if entity not in self.trees:
                continue

            # --- Tick Throttling ---
            # Calculate time since last tick for this entity
            last_time = self.last_update_times.get(entity, self.total_time - 0.1)
            time_since_last_tick = self.total_time - last_time

            # Determine required interval based on stability and LOD
            required_interval = self.min_tick_interval
            
            # LOD Throttling
            lod = world.try_get_component(entity, LODComponent)
            if lod:
                if lod.level == 1: # Medium
                    required_interval *= 2.0
                elif lod.level == 2: # Low
                    required_interval *= 5.0
                elif lod.level >= 3: # Culled
                    required_interval *= 10.0

            if entity in self.stable_entities:
                # Stable entities tick less frequently
                required_interval *= self.stable_tick_multiplier

            # Skip if not enough time has passed
            if time_since_last_tick < required_interval:
                # Re-queue immediately without counting as an update
                self.update_queue.append(entity)
                skipped_count += 1
                # Prevent infinite loop if all entities are throttled
                if skipped_count >= max_queue_checks:
                    break
                continue

            # Calculate dt for this entity (actual time since last tick)
            entity_dt = time_since_last_tick
            if entity_dt <= 0:
                entity_dt = 0.1

            # Tick the behavior tree
            py_trees.blackboard.Blackboard().set("dt", entity_dt)
            tree = self.trees[entity]
            tree.tick()

            # Post-tick logic and stable state tracking
            ai = world.try_get_component(entity, AIState)
            root_status = tree.root.status

            if root_status == Status.SUCCESS:
                # Mark as stable - will tick less frequently
                self.stable_entities.add(entity)
            elif root_status == Status.RUNNING:
                # Active behavior - remove from stable set
                self.stable_entities.discard(entity)
            # FAILURE stays at normal rate to retry quickly

            if ai and (root_status == Status.SUCCESS or root_status == Status.FAILURE):
                if getattr(ai, "manual_override", False):
                    ai.manual_override = False

            # Update time and re-queue
            self.last_update_times[entity] = self.total_time
            self.update_queue.append(entity)
            updates_count += 1
