"""
Module defining the UtilitySelector behavior tree node.
"""

from typing import TYPE_CHECKING, Any

from loguru import logger
from py_trees.common import Status

from ..trait_service import TraitService
from ..components import AIState, Personality
from .base_action import Action
from .utility import UtilityAIEngine

if TYPE_CHECKING:
    from ...engine.ecs import World


class UtilitySelector(Action):
    """
    Evaluates utility scores for available actions and selects the best one.
    Updates AIState.current_action.

    Attributes:
        engine (UtilityAIEngine | None): The utility AI engine.
        trait_service (TraitService | None): The trait service.
    """

    def __init__(
        self,
        name: str = "Utility Selector",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the UtilitySelector node.

        Args:
            name (str): The name of the node.
            entity_id (int | None): The ID of the entity.
            world (World | None): The ECS World.
            blackboard (Any | None): The blackboard for data sharing.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.engine: UtilityAIEngine | None = None
        self.trait_service: TraitService | None = None

    def initialise(self) -> None:
        """
        Initializes the selector, attempting to fetch the UtilityAIEngine service.
        """
        # Try to get engine if not set
        if self.world and not self.engine:
            self.engine = self.world.services.try_get(UtilityAIEngine)

        if self.world and not self.trait_service:
            self.trait_service = self.world.services.try_get(TraitService)

    def update(self) -> Status:
        """
        Updates the selector.

        Evaluates utility scores for available actions based on the current context (stats)
        and updates the entity's AIState with the best action.

        Returns:
            Status: Status.SUCCESS if an action was selected, Status.FAILURE otherwise.
        """
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.try_get_component(self.entity_id, AIState)
        if not ai:
            logger.warning(
                f"UtilitySelector: Entity {self.entity_id} Missing AIState component"
            )
            return Status.FAILURE

        if getattr(ai, "manual_override", False):
            return Status.SUCCESS  # Skip utility selection if overridden.

        if not self.engine:
            self.engine = self.world.services.try_get(UtilityAIEngine)
            if not self.engine:
                logger.error("UtilitySelector: No Engine found")
                return Status.FAILURE

        if not self.trait_service:
            self.trait_service = self.world.services.try_get(TraitService)

        # Build Context using Helper
        from .context_builder import UtilityContextBuilder

        context = UtilityContextBuilder.build_context(
            self.entity_id, self.world, self.trait_service
        )

        if not context:
            logger.warning(
                f"UtilitySelector: Entity {self.entity_id} failed to build context (missing components)"
            )
            return Status.FAILURE

        # Select Best Action
        personality = self.world.try_get_component(self.entity_id, Personality)
        best_action = self.engine.select_action(
            context, personality, self.trait_service
        )

        # Update AI State
        if best_action != ai.current_action:
            ai.current_action = best_action
            ai.action_progress = 0.0
            if hasattr(ai, "failed_targets"):
                ai.failed_targets.clear()  # Reset failed targets on action change.

        return Status.SUCCESS
