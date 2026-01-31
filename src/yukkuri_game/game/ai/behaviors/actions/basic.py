from typing import TYPE_CHECKING, Any, Callable
import pymunk

from py_trees.common import Status

from ....components import MovementController, MoveCommand
from ....yukkuri_components import EmotionalState, AIState
from ...base_action import Action

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


class Idle(Action):
    """
    Makes the entity idle (stop moving).
    """

    def __init__(
        self,
        name: str = "Idle",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the Idle action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int | None): The entity ID.
            world (World | None): The ECS World.
            blackboard (Any | None): The blackboard for data sharing.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        """
        Stops the entity's physics velocity.

        Returns:
            Status: Always returns SUCCESS.
        """
        if self.world is None or self.entity_id is None:
            return Status.SUCCESS

        # Ensure MovementController targets zero
        controller = self.world.try_get_component(self.entity_id, MovementController)
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            # Optional: Hard stop physics to prevent sliding if desired
            # phys = self.world.try_get_component(self.entity_id, PhysicsBody)
            # if phys:
            #     phys.body.velocity = (0, 0)

        # Remove any lingering MoveCommands that would override our stop
        if self.world.has_component(self.entity_id, MoveCommand):
            self.world.remove_component(self.entity_id, MoveCommand)

        # Also clear path to prevent resumption of path following
        ai = self.world.try_get_component(self.entity_id, AIState)
        if ai and ai.path:
            ai.path = None

        return Status.SUCCESS


class Check(Action):
    """
    A behavior node that checks a condition function.

    Attributes:
        check_fn (Callable[[], bool]): The function to check.
    """

    def __init__(self, name: str, check_fn: Callable[[], bool]):
        """
        Initializes the Check behavior.

        Args:
            name (str): The name of the behavior node.
            check_fn (Callable[[], bool]): The function to call. Should return True for success.
        """
        super().__init__(name)
        self.check_fn = check_fn

    def update(self) -> Status:
        """
        Evaluates the check function.

        Returns:
            Status: SUCCESS if check_fn returns True, else FAILURE.
        """
        if self.check_fn():
            return Status.SUCCESS
        return Status.FAILURE


class CheckEmotion(Action):
    """
    Checks the emotional state of the entity.

    Attributes:
        check_fn (Callable[[EmotionalState], bool]): The function to evaluate the emotion.
    """

    def __init__(
        self,
        name: str,
        entity_id: int,
        world: "World",
        check_fn: Callable[[EmotionalState], bool],
    ):
        """
        Initializes the CheckEmotion action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
            check_fn (Callable[[EmotionalState], bool]): Predicate function.
        """
        super().__init__(name, entity_id, world)
        self.check_fn = check_fn

    def update(self) -> Status:
        """
        Evaluates the emotional state check.

        Returns:
            Status: SUCCESS if check_fn returns True, else FAILURE.
        """
        if not self.world or not self.entity_id:
            return Status.FAILURE
        emotion = self.world.get_component(self.entity_id, EmotionalState)
        if emotion and self.check_fn(emotion):
            return Status.SUCCESS
        return Status.FAILURE
