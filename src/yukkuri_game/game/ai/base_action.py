"""
Module defining the base Action class for AI behaviors.
"""

from typing import TYPE_CHECKING, Any

from py_trees.behaviour import Behaviour
from py_trees.common import Status

if TYPE_CHECKING:
    from ...engine.ecs import World as RealWorld
    from ..systems.behavior_ffi import BevyWorldAdapter

    World = RealWorld | BevyWorldAdapter


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

    def publish_command(
        self, command_type: Any, payload: dict[str, Any]
    ) -> bool:
        """Publishes a high-level command request to the central CommandQueue.

        Args:
            command_type: The CommandType category.
            payload: Dictionary of arguments tailored for the command type.

        Returns:
            bool: True if successfully published, False otherwise.
        """
        if self.world and self.entity_id is not None:
            from .commands import Command, CommandQueue

            queue = self.world.services.try_get(CommandQueue)
            if queue and hasattr(queue, "push"):
                queue.push(Command(command_type, self.entity_id, payload))
                return True
        return False

    def get_blackboard(self) -> Any | None:
        """Retrieves the Blackboard perception component for this entity.

        Returns:
            Any | None: The blackboard component if found.
        """
        if self.world and self.entity_id is not None:
            from ..components import Blackboard as ECSBlackboard

            return self.world.try_get_component(self.entity_id, ECSBlackboard)
        return None

    def terminate(self, new_status: Status) -> None:
        """
        Cleans up resources when the action finishes or is aborted.

        Args:
            new_status (Status): The new execution status of the behavior.
        """
        if new_status in (Status.SUCCESS, Status.FAILURE, Status.INVALID):
            self.on_cleanup()

    def on_cleanup(self) -> None:
        """
        Custom lifecycle cleanup hook.

        Subclasses should override this method to perform cleanups of physical
        forces, ECS commands, and transient state data.
        """
        pass

