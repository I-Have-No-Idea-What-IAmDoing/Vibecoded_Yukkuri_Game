from typing import TYPE_CHECKING, Any

import pymunk
from py_trees.common import Status

from ....components import AIState, EmotionalState, MoveCommand, MovementController, Needs
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
            self.world.remove_component(self.entity_id, MoveCommand)

        ai = self.world.try_get_component(self.entity_id, AIState)
        if ai and ai.path:
            ai.path = None

        # Get delta time from TimeService (World doesn't have a dt property)
        from ....services import TimeService

        time_service = self.world.services.try_get(TimeService)
        dt = time_service.game_delta_multiplier if time_service else 0.016

        needs = self.world.try_get_component(self.entity_id, Needs)
        if needs:
            needs.energy += 10.0 * dt
            if needs.energy >= 100.0:
                return Status.SUCCESS
            state = self.world.try_get_component(self.entity_id, EmotionalState)
            if state:
                state.happiness += 5.0 * dt

        return Status.RUNNING
