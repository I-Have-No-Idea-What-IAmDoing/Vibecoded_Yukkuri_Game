from typing import Dict
import py_trees
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
        # Set dt in Blackboard
        py_trees.blackboard.Blackboard().set("dt", dt)

        # We only need AIState to decide if we should tick a tree,
        # but create_yukkuri_behavior_tree uses entity_id to create nodes that access components.
        # We need to iterate over entities that *should* have behavior.
        # Usually those with AIState.

        for entity, (ai,) in world.get_components_tuple(AIState):
            if entity not in self.trees:
                # Create BT if not exists
                root = create_yukkuri_behavior_tree(entity, world, int(self.world_w), int(self.world_h))
                self.trees[entity] = py_trees.trees.BehaviourTree(root)
                self.trees[entity].setup(timeout=15)

            # Tick Behavior Tree
            self.trees[entity].tick()

        # Optional: Clean up trees for destroyed entities?
        # This would require checking if entity still exists.
        # Since get_components_tuple only returns existing entities, we are safe for ticking.
        # But self.trees might grow with dead entities.
        # Cleanup logic could be here or in a separate cleanup method.
        # For now, let's do a simple cleanup pass or rely on weakrefs if keys allow (ints don't).

        # Robust cleanup
        # We perform cleanup to prevent memory leaks from destroyed entities or entities that lost AIState
        # We iterate over existing trees and check if the entity still has AIState component.
        for entity_id in list(self.trees.keys()):
            if not world.entity_exists(entity_id) or not world.has_component(entity_id, AIState):
                # destroy the tree properly? py_trees might have cleanup
                # For now just remove reference
                del self.trees[entity_id]
