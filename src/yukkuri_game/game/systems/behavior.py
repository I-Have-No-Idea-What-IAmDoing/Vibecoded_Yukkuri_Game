"""
Module defining the BehaviorSystem logic.
"""

from typing import Dict
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
        self.trees: Dict[int, py_trees.trees.BehaviourTree] = {}

    def update(self, world: World, dt: float) -> None:
        """
        Ticks behavior trees for all entities with AIState.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        py_trees.blackboard.Blackboard().set("dt", dt)

        for entity, (ai,) in world.get_components_tuple(AIState):
            if entity not in self.trees:
                root = create_yukkuri_behavior_tree(
                    entity, world, int(self.world_w), int(self.world_h)
                )
                self.trees[entity] = py_trees.trees.BehaviourTree(root)
                self.trees[entity].setup(timeout=15)

            tree = self.trees[entity]
            tree.tick()

            # Check if the tree execution finished (SUCCESS or FAILURE)
            # The root is a Sequence(UtilitySelector, ExecutionSelector).
            # If ExecutionSelector finishes, the root finishes.
            # If so, we clear the manual override to allow Utility AI to take over again.
            if tree.root.status == Status.SUCCESS or tree.root.status == Status.FAILURE:
                if getattr(ai, "manual_override", False):
                    ai.manual_override = False
                    # Optionally reset action to Idle to force re-evaluation next frame
                    # ai.current_action = "Idle"

        for entity_id in list(self.trees.keys()):
            if not world.entity_exists(entity_id) or not world.has_component(
                entity_id, AIState
            ):
                del self.trees[entity_id]
