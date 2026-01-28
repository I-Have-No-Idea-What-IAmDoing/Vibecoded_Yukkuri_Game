import math
from typing import TYPE_CHECKING, Any, cast

import pymunk
from py_trees.common import Status

from ...base_action import Action
from ....components import (
    Transform,
    MovementController,
    InteractionRequest,
)
from ....yukkuri_components import (
    AIState,
    Needs,
    Predator,
    YukkuriStats,
)
from yukkuri_game.engine.types import EntityID

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


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

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if target_trans is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist <= 75.0:
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id, consume=self.consume
                    ),
                )
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

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if target_trans is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist <= 75.0:
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id,
                        consume=False,
                        action=self.interaction_type,
                    ),
                )
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
        self.sector_map: Any = None
        self.last_update_time: float = 0.0

    def initialise(self) -> None:
        self._eating_progress = 0.0
        if self.world:
            self.last_update_time = self.world.time

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        # Lazy load SectorMap
        if self.sector_map is None:
            from ....systems.sector_system import SectorMap

            self.sector_map = self.world.services.try_get(SectorMap)

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        trans = self.world.get_component(self.entity_id, Transform)
        controller = self.world.get_component(self.entity_id, MovementController)

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
            return Status.RUNNING

        # Social Defense (Rescue) Check
        rescue_radius = 60.0

        # Use SectorMap if available for optimization
        potential_defenders = []
        if self.sector_map:
            potential_defenders = self.sector_map.get_entities_in_radius(
                target_trans.x, target_trans.y, rescue_radius
            )
        else:
            potential_defenders = self.world.get_all_entities()

        for defender_id in potential_defenders:
            if defender_id == self.entity_id:
                continue
            if defender_id == ai.current_target_id:
                continue

            # Fetch components required for check
            d_stats = self.world.try_get_component(defender_id, YukkuriStats)
            d_trans = self.world.try_get_component(defender_id, Transform)

            if not d_stats or not d_trans:
                continue

            if self.world.has_component(defender_id, Predator):
                continue

            defender_dist = math.hypot(
                d_trans.x - target_trans.x, d_trans.y - target_trans.y
            )
            if defender_dist <= rescue_radius:
                ai.current_target_id = cast(EntityID, -1)
                return Status.FAILURE

        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)
        if target_controller:
            target_controller.target_velocity = pymunk.Vec2d(0, 0)

        # Use consistent world delta time
        dt = self.world.dt
        self.last_update_time = self.world.time

        damage = predator.dps * dt
        target_needs.health -= damage

        if target_needs.health <= 0:
            self.world.destroy_entity(ai.current_target_id)
            my_needs = self.world.get_component(self.entity_id, Needs)
            if my_needs:
                my_needs.hunger = max(0.0, my_needs.hunger - 50.0)

            ai.current_target_id = cast(EntityID, -1)
            return Status.SUCCESS

        return Status.RUNNING
