"""
Module defining the base Action class for AI behaviors.
"""
import py_trees
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World

class Action(Behaviour):
    """
    Base class for AI actions in the Behavior Tree.

    Attributes:
        entity_id (Optional[int]): The ID of the entity performing the action.
        world (Optional[World]): The ECS World instance.
        blackboard (Optional[Any]): The Behavior Tree blackboard.
    """
    def __init__(self, name: str = "Action", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None):
        """
        Initializes the Action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
        """
        super().__init__(name)
        self.entity_id = entity_id
        self.world = world
        self.blackboard = blackboard

    def update(self) -> Status:
        """
        Updates the behavior.

        Returns:
            Status: The status of the behavior (SUCCESS, FAILURE, RUNNING).
        """
        if not self.world or self.entity_id is None:
             return Status.FAILURE
        return Status.RUNNING
