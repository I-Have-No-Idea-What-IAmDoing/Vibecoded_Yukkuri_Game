"""
Module defining the BehaviorSystem logic.
"""

import py_trees
from py_trees.common import Status
from ...engine.ecs import System, World
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
            # Removing from deque is O(N), so we just skip them during update loop if encountered
            # Or we can rebuild deque if many die. Lazy removal is better usually.

        # 3. Process Batch
        updates_count = 0
        iterations = 0
        max_queue_checks = len(self.update_queue)

        while updates_count < self.max_updates_per_frame and iterations < max_queue_checks:
            iterations += 1
            if not self.update_queue:
                break
                
            entity = self.update_queue.popleft()
            
            # If entity is dead (removed from trees), skip and don't re-queue
            if entity not in self.trees:
                continue

            # Calculate dt for this entity
            last_time = self.last_update_times.get(entity, self.total_time - 0.1)
            entity_dt = self.total_time - last_time
            if entity_dt <= 0:
                entity_dt = 0.1

            # Tick
            py_trees.blackboard.Blackboard().set("dt", entity_dt)
            tree = self.trees[entity]
            tree.tick()

            # Post-tick logic
            ai = world.try_get_component(entity, AIState)
            if ai and (tree.root.status == Status.SUCCESS or tree.root.status == Status.FAILURE):
                if getattr(ai, "manual_override", False):
                    ai.manual_override = False

            # Update time and re-queue
            self.last_update_times[entity] = self.total_time
            self.update_queue.append(entity)
            updates_count += 1
