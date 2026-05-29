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

        now: float = self.world.time
        exclude_set: set[str] = set()
        cooldowns: dict[str, float] | None = getattr(
            ai, "action_cooldowns", None
        )
        if cooldowns:
            exclude_set = {
                act for act, expire_time in cooldowns.items()
                if now < expire_time
            }

        best_action = self.engine.select_action(
            context,
            personality,
            self.trait_service,
            exclude_set,
        )

        # Populate breakdown if inspected
        if ai.is_inspected:
            breakdown: dict[str, Any] = {
                "active_action": best_action,
                "actions": {}
            }
            for action_name in self.engine.actions:
                res = self.engine.debug_score(
                    context, action_name, personality, self.trait_service
                )
                breakdown["actions"][action_name] = res

            # Sort actions by score descending
            sorted_actions = sorted(
                breakdown["actions"].items(),
                key=lambda x: x[1].get("final_score", 0.0),
                reverse=True,
            )
            breakdown["sorted_actions"] = sorted_actions
            ai.last_utility_breakdown = breakdown
        else:
            ai.last_utility_breakdown = None

        # Update AI State
        if best_action != ai.current_action:
            from ..components import YukkuriStats
            from ..events import LogMessageEvent
            from ...engine.event_bus import EventBus

            name = f"Yukkuri #{self.entity_id}"
            stats = self.world.try_get_component(self.entity_id, YukkuriStats)
            if stats:
                name = stats.name

            eb = self.world.services.try_get(EventBus)
            if eb:
                eb.publish(
                    LogMessageEvent(
                        message=f"{name} decided to: {best_action}.",
                        color=(0, 200, 255),
                        channel="AI",
                    )
                )

            # Record transition in decision history (max 10 entries).
            best_score = 0.0
            if ai.last_utility_breakdown:
                actions = ai.last_utility_breakdown.get("actions", {})
                best_score = actions.get(best_action, {}).get(
                    "final_score", 0.0
                )

            logger.debug(
                "Entity {} ({}) transitioned: {} -> {} (score: {:.3f})",
                self.entity_id,
                name,
                ai.current_action,
                best_action,
                best_score,
            )

            ai.current_action = best_action
            ai.action_progress = 0.0
            if hasattr(ai, "failed_targets"):
                ai.failed_targets.clear()  # Reset failed targets on action change.

            history = getattr(ai, "decision_history", None)
            if history is not None:
                history.append((best_action, best_score, now))
                while len(history) > 10:
                    history.popleft()


        return Status.SUCCESS
