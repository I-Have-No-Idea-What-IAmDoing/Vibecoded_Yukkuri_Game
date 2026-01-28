"""
Module defining the UtilitySelector behavior tree node.
"""

from typing import TYPE_CHECKING, Any

from loguru import logger
from py_trees.common import Status

from ..services import TimeService
from ..trait_service import TraitService
from ..yukkuri_components import (
    AIState,
    Blackboard,
    EmotionalState,
    Needs,
    Personality,
    Predator,
    Skills,
    YukkuriStats,
)
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

        Evaluates utility scores for all available actions based on the current context (stats)
        and updates the entity's AIState with the best action.

        Returns:
            Status: Status.SUCCESS if an action was selected, Status.FAILURE otherwise.
        """
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)

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

        time_service = self.world.services.try_get(TimeService)

        stats = self.world.get_component(self.entity_id, YukkuriStats)
        needs = self.world.get_component(self.entity_id, Needs)
        personality = self.world.get_component(self.entity_id, Personality)
        emotional = self.world.get_component(self.entity_id, EmotionalState)
        skills = self.world.get_component(self.entity_id, Skills)

        if not stats or not needs:
            logger.warning(
                f"UtilitySelector: Entity {self.entity_id} Missing YukkuriStats or Needs component"
            )
            return Status.FAILURE

        # Build Context for Utility Evaluation
        blackboard_comp = self.world.try_get_component(self.entity_id, Blackboard)

        nearby_friends = 0.0
        nearby_enemies = 0.0
        nearby_prey = 0.0

        if blackboard_comp:
            nearby_friends = float(blackboard_comp.nearby_friends)
            nearby_enemies = float(blackboard_comp.nearby_enemies)
            nearby_prey = float(blackboard_comp.nearby_prey)
        else:
            # Fallback if no Blackboard (shouldn't happen with full system)
            # We could keep the old logic as fallback, but for now we assume Blackboard exists
            # to enforce the new architecture.
            pass

        # Extract emotional state
        happiness = 50.0
        stress = 0.0
        if emotional:
            happiness = (
                emotional.happiness + 100.0
            ) / 2.0  # Normalize -100..100 to 0..100.
            stress = emotional.stress

        # Time of Day (0.0 to 24.0)
        time_of_day = 12.0
        is_night = 0.0
        if time_service:
            time_of_day = time_service.time_of_day
            if time_service.is_night:
                is_night = 1.0

        context = {
            "hunger": needs.hunger,
            "hunger_inv": 100.0 - needs.hunger,  # Inverse hunger (Satiety)
            "energy": needs.energy,
            "energy_inv": 100.0 - needs.energy,  # Inverse energy (Tiredness)
            "happiness": happiness,
            "happiness_inv": 100.0 - happiness,  # Sadness
            "social": needs.social,
            "social_inv": 100.0 - needs.social,
            "stress": stress,
            "cleanliness": needs.cleanliness,
            "bladder": needs.bladder,  # Added Bladder
            "easiness": needs.easiness,  # Added Easiness
            "nearby_friends": float(nearby_friends),
            "nearby_enemies": float(nearby_enemies),
            "nearby_prey": float(nearby_prey),
            "time_of_day": time_of_day,
            "is_night": is_night,
            "constant_100": 100.0,
            "constant_0": 0.0,
            "is_predator": 1.0
            if self.world.has_component(self.entity_id, Predator)
            else 0.0,
        }

        # Inject Skills into Context
        if skills:
            for skill_id, state in skills.states.items():
                context[f"skill_{skill_id}"] = float(state.level)

        if personality:
            if personality.axis:
                context["val_kindness"] = (personality.axis.kindness + 100) / 2.0
                context["val_energy"] = (personality.axis.energy + 100) / 2.0
                context["val_bravery"] = (personality.axis.bravery + 100) / 2.0
                context["val_greed"] = (personality.axis.greed + 100) / 2.0
                context["val_compassion"] = context[
                    "val_kindness"
                ]  # Alias for compatibility.

            # Inject Traits as binary flags for conditional considerations
            for trait in personality.traits:
                context[f"trait_{trait}"] = 1.0

        # Populate cached_overrides if missing.
        if personality and self.trait_service and personality.cached_overrides is None:
            personality.cached_overrides = self.trait_service.calculate_overrides(
                personality.traits
            )

        best_action = self.engine.select_action(
            context, personality, self.trait_service
        )

        if best_action != ai.current_action:
            ai.current_action = best_action
            ai.action_progress = 0.0
            if hasattr(ai, "failed_targets"):
                ai.failed_targets.clear()  # Reset failed targets on action change.

        return Status.SUCCESS
