import pymunk
from typing import TYPE_CHECKING
from py_trees.common import Status
from ...base_action import Action
from ....components import MovementController
from ....yukkuri_components import Needs, EmotionalState

if TYPE_CHECKING:
    pass


class Sleep(Action):
    def __init__(self, name="Sleep", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        controller = self.world.try_get_component(self.entity_id, MovementController)
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)

        dt = 0.016
        needs = self.world.try_get_component(self.entity_id, Needs)
        if needs:
            needs.energy += 10.0 * dt
            if needs.energy >= 100.0:
                return Status.SUCCESS
            state = self.world.try_get_component(self.entity_id, EmotionalState)
            if state:
                state.happiness += 5.0 * dt

        return Status.RUNNING
