"""
Module defining the base Action class for AI behaviors.
"""

from typing import TYPE_CHECKING, Any

from py_trees.behaviour import Behaviour
from py_trees.common import Status

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


class Action(Behaviour):
    """
    Base class for AI actions in the Behavior Tree.

    Attributes:
        entity_id (int | None): The ID of the entity performing the action.
        world (World | None): The ECS World instance.
        blackboard (Any | None): The Behavior Tree blackboard.
    """

    def __init__(
        self,
        name: str = "Action",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the Action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int | None): The ID of the entity.
            world (World | None): The ECS World instance.
            blackboard (Any | None): The Behavior Tree blackboard.
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
