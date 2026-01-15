"""
Module defining the UtilitySelector behavior tree node.
"""

from typing import Optional, Any, TYPE_CHECKING
from py_trees.common import Status
from loguru import logger

from .utility import UtilityAIEngine
from .base_action import Action

from ..yukkuri_components import (
    AIState,
    YukkuriStats,
    Needs,
    Personality,
    EmotionalState,
    Skills,
    Predator,
    Predator,
    RelationshipRegistry,
    Blackboard,
)
from ..components import Transform
from ..trait_service import TraitService
from ..services import TimeService

if TYPE_CHECKING:
    from ...engine.ecs import World


class UtilitySelector(Action):
    """
    Evaluates utility scores for available actions and selects the best one.
    Updates AIState.current_action.

    Attributes:
        engine (Optional[UtilityAIEngine]): The utility AI engine.
        trait_service (Optional[TraitService]): The trait service.
    """

    def __init__(
        self,
        name: str = "Utility Selector",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the UtilitySelector node.

        Args:
            name (str): The name of the node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World.
            blackboard (Optional[Any]): The blackboard for data sharing.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.engine: UtilityAIEngine | None = None
        self.trait_service: TraitService | None = None

    def initialise(self) -> None:
        """
        Initializes the selector, attempting to fetch the UtilityAIEngine service.

        Returns:
            None
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

        # Check for manual override
        if getattr(ai, "manual_override", False):
            # If overridden, we skip utility selection and just return SUCCESS
            # preserving the current action set externally.
            return Status.SUCCESS

        if not self.engine:
            self.engine = self.world.services.try_get(UtilityAIEngine)
            if not self.engine:
                logger.error("UtilitySelector: No Engine found")
                return Status.FAILURE

        # Also try to grab trait service again if missing
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
            # Normalize -100..100 to 0..100 for AI consumption
            happiness = (emotional.happiness + 100.0) / 2.0
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

        # Inject Personality Values into Context
        # Allows AI to make decisions based on personality traits (e.g. "Lazy" might value rest more)
        if personality:
            # Inject Axis values (normalized to 0-100?)
            if personality.axis:
                # Map axes to approximate old values for compatibility or new ones
                context["val_kindness"] = (personality.axis.kindness + 100) / 2.0
                context["val_energy"] = (personality.axis.energy + 100) / 2.0
                context["val_bravery"] = (personality.axis.bravery + 100) / 2.0
                context["val_greed"] = (personality.axis.greed + 100) / 2.0

                # Alias for backward compatibility if actions.toml uses 'compassion' etc
                context["val_compassion"] = context["val_kindness"]

            # Inject Traits as binary flags for conditional considerations
            for trait in personality.traits:
                context[f"trait_{trait}"] = 1.0

        # Select Action

        # Optimize: populate cached_overrides if missing
        if personality and self.trait_service and personality.cached_overrides is None:
            personality.cached_overrides = self.trait_service.calculate_overrides(
                personality.traits
            )

        # We pass personality and trait service to support overrides inside the engine
        # The engine will select the best action based on the highest utility score
        best_action = self.engine.select_action(
            context, personality, self.trait_service
        )

        # Update AI State
        if best_action != ai.current_action:
            ai.current_action = best_action
            ai.action_progress = 0.0
            # Clear failed targets when switching actions to give them another chance later
            if hasattr(ai, "failed_targets"):
                ai.failed_targets.clear()

        return Status.SUCCESS
