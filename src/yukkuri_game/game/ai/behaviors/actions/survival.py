from typing import TYPE_CHECKING, Any

import pymunk
from py_trees.common import Status

from ....components import AIState, EmotionalState, MoveCommand, Needs
from yukkuri_game.engine.components import MovementController
from ...base_action import Action

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


class Sleep(Action):
    """
    Action to sleep and recover energy.
    """

    def __init__(
        self,
        name: str = "Sleep",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the Sleep action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        controller = self.world.try_get_component(self.entity_id, MovementController)
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)

        # Clear active MoveCommands and existing paths
        if self.world.has_component(self.entity_id, MoveCommand):
            self.world.commands.remove_component(self.entity_id, MoveCommand)

        ai = self.world.try_get_component(self.entity_id, AIState)
        if ai and ai.path:
            ai.path = None

        # Get physics_dt from Blackboard with a fallback to 0.016
        import py_trees
        blackboard = py_trees.blackboard.Blackboard()
        physics_dt = blackboard.get("dt") if blackboard.exists("dt") else 0.016

        # Rely solely on blackboard dt since it already accounts for game speed
        dt_scaled = physics_dt

        needs = self.world.try_get_component(self.entity_id, Needs)
        if needs:
            needs.energy += 10.0 * dt_scaled
            if needs.energy >= 100.0:
                return Status.SUCCESS
            emo = self.world.try_get_component(
                self.entity_id, EmotionalState
            )
            if emo:
                emo.happiness += 5.0 * dt_scaled

        return Status.RUNNING
