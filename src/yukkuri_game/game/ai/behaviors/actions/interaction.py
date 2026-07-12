import math
from typing import TYPE_CHECKING, Any, cast

import pymunk
from py_trees.common import Status

from ...base_action import Action
from ....components import (
    AIState,
    InteractionRequest,
    Needs,
    Predator,
)
from .....engine.components import (
    MovementController,
    Transform,
)
from .....engine.types import EntityID

if TYPE_CHECKING:
    from ...base_action import World


class Interact(Action):
    """
    Handles interaction with a target entity (e.g., eating food).

    Attributes:
        consume (bool): Whether the interaction should consume the target.
    """

    def __init__(
        self,
        name: str = "Interact",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
        consume: bool = True,
    ):
        """
        Initializes the Interact action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
            consume (bool): Whether to consume the target.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.consume = consume

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.try_get_component(self.entity_id, AIState)
        trans = self.world.try_get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.try_get_component(ai.current_target_id, Transform)
        if target_trans is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)

        if dist <= 110.0:
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.commands.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id, consume=self.consume
                    ),
                )

            if ai.manual_override:
                ai.manual_override = False
            return Status.SUCCESS

        return Status.RUNNING


class SocialInteract(Action):
    """
    Handles social interaction with another Yukkuri.

    Attributes:
        interaction_type (str): The type of interaction (e.g., "Talk", "Fight", "Dance").
    """

    def __init__(
        self, name: str, entity_id: int, world: "World", interaction_type: str
    ):
        """
        Initializes the SocialInteract action.

        Args:
            name (str): Behavior name.
            entity_id (int): Entity ID.
            world (World): ECS World.
            interaction_type (str): Interaction type.
        """
        super().__init__(name, entity_id, world)
        self.interaction_type = interaction_type

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.try_get_component(self.entity_id, AIState)
        trans = self.world.try_get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.try_get_component(ai.current_target_id, Transform)
        if target_trans is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist <= 75.0:
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.commands.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id,
                        consume=False,
                        action=self.interaction_type,
                    ),
                )
            if ai.manual_override:
                ai.manual_override = False
            return Status.SUCCESS

        return Status.RUNNING


class EatPrey(Action):
    """
    Channeling action that locks both predator and prey, dealing damage over time.
    """

    def __init__(
        self,
        name: str = "Eat Prey",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the EatPrey action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)
        self._eating_progress: float = 0.0
        self.spatial_service: Any = None
        self.last_update_time: float = 0.0
        self.time_service: Any = None

    def initialise(self) -> None:
        self._eating_progress = 0.0
        if self.world:
            self.last_update_time = self.world.time
            # Get TimeService
            from .....engine.services.time_service import TimeService

            self.time_service = self.world.services.try_get(TimeService)

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        # Lazy load ISpatialService
        if self.spatial_service is None:
            from .....engine.protocols import ISpatialService

            self.spatial_service = self.world.services.try_get(ISpatialService)

        ai = self.world.try_get_component(self.entity_id, AIState)
        predator = self.world.try_get_component(self.entity_id, Predator)
        trans = self.world.try_get_component(self.entity_id, Transform)
        controller = self.world.try_get_component(self.entity_id, MovementController)

        if ai is None or predator is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.try_get_component(ai.current_target_id, Transform)
        target_needs = self.world.try_get_component(ai.current_target_id, Needs)
        target_controller = self.world.try_get_component(
            ai.current_target_id, MovementController
        )

        if target_trans is None or target_needs is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist > 40.0:
            # Prey escaped melee range. Return FAILURE so the parent Hunt Sequence
            # resets and MoveToTarget can resume the chase. RUNNING would freeze
            # the predator in place forever (sequence memory=True trap).
            return Status.FAILURE


        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)
        if target_controller:
            target_controller.target_velocity = pymunk.Vec2d(0, 0)

        # Use Blackboard for dt
        import py_trees
        blackboard = py_trees.blackboard.Blackboard()
        dt = blackboard.get("dt") if blackboard.exists("dt") else 0.016

        # Scale dt by game_speed so damage stays proportional at any simulation
        # speed. Without this, predators effectively deal less damage per real-
        # time second at high game speeds, causing them to starve mid-meal.
        game_speed = (
            self.time_service.game_speed if self.time_service else 1.0
        )
        dt_scaled = dt * game_speed

        self.last_update_time = self.world.time

        damage = predator.dps * dt_scaled
        target_needs.health -= damage

        if target_needs.health <= 0:
            try:
                self.world.commands.destroy_entity(ai.current_target_id)
            except KeyError:
                # Entity already destroyed (e.g. by another predator)
                pass

            my_needs = self.world.try_get_component(self.entity_id, Needs)
            if my_needs:
                my_needs.hunger = max(0.0, my_needs.hunger - 50.0)

            ai.current_target_id = cast(EntityID, -1)
            if ai.manual_override:
                ai.manual_override = False
            return Status.SUCCESS

        return Status.RUNNING
