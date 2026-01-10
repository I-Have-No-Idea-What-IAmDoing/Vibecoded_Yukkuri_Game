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
        # Map entity_id -> next update time (seconds)
        self.next_update_times: dict[int, float] = {}
        # Map entity_id -> last update time (seconds) to calculate correct dt
        self.last_update_times: dict[int, float] = {}
        self.total_time: float = 0.0

    def update(self, world: World, dt: float) -> None:
        """
        Ticks behavior trees for all entities with AIState.
        Updates are throttled to run at ~10Hz (every 0.1s) per entity.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        self.total_time += dt

        for entity, (ai,) in world.get_components_tuple(AIState):
            if entity not in self.trees:
                root = create_yukkuri_behavior_tree(
                    entity, world, int(self.world_w), int(self.world_h)
                )
                self.trees[entity] = py_trees.trees.BehaviourTree(root)
                self.trees[entity].setup(timeout=15)
                # Stagger initial update to prevent spikes
                # Offset by a small random amount or based on ID
                stagger = (entity % 10) * 0.01
                self.next_update_times[entity] = self.total_time + stagger
                self.last_update_times[entity] = self.total_time  # Initialize last time

            # Check if it's time to update this entity
            if self.total_time >= self.next_update_times.get(entity, 0.0):
                # Calculate actual delta time since last update for this entity
                last_time = self.last_update_times.get(entity, self.total_time - 0.1)
                entity_dt = self.total_time - last_time
                if entity_dt <= 0:
                    entity_dt = 0.1  # Fallback

                # Set dt specifically for this tick
                py_trees.blackboard.Blackboard().set("dt", entity_dt)

                tree = self.trees[entity]
                tree.tick()

                # Update timing tracking
                self.last_update_times[entity] = self.total_time
                # Schedule next update in 0.1s (10Hz)
                self.next_update_times[entity] = self.total_time + 0.1

                # Check if the tree execution finished (SUCCESS or FAILURE)
                # The root is a Selector(StressBreak, Sequence(UtilitySelector, ExecutionSelector)).
                # If the tree completes a full tick cycle with a definitive status,
                # we check if we need to reset any flags.
                # Specifically, if Manual Override was active and the tree finished, it means
                # the manual action completed or failed, so we return control to the AI.
                if (
                    tree.root.status == Status.SUCCESS
                    or tree.root.status == Status.FAILURE
                ):
                    if getattr(ai, "manual_override", False):
                        ai.manual_override = False
                        # Optionally reset action to Idle to force re-evaluation next frame
                        # ai.current_action = "Idle"

        # Cleanup destroyed entities
        for entity_id in list(self.trees.keys()):
            if not world.entity_exists(entity_id) or not world.has_component(
                entity_id, AIState
            ):
                del self.trees[entity_id]
                if entity_id in self.next_update_times:
                    del self.next_update_times[entity_id]
                if entity_id in self.last_update_times:
                    del self.last_update_times[entity_id]
