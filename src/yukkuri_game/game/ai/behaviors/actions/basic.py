from typing import Any, Callable, Optional, TYPE_CHECKING
from py_trees.common import Status
from ...base_action import Action
from ....yukkuri_components import EmotionalState
from ....components import PhysicsBody

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
        world: Optional["World"] = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the Idle action.
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

        phys = self.world.get_component(self.entity_id, PhysicsBody)
        if phys:
            phys.body.velocity = (0, 0)
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
            name: The name of the behavior node.
            check_fn: The function to call. Should return True for success.
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
