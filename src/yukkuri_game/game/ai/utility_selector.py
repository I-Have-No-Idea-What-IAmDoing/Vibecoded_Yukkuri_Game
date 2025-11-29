"""
Module defining the UtilitySelector behavior tree node.
"""
from typing import Optional, Any, TYPE_CHECKING
from py_trees.common import Status

from .utility import UtilityAIEngine
from .base_action import Action

from ..yukkuri_components import AIState, YukkuriStats, Personality
from ..components import Transform
from ..trait_service import TraitService

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
    def __init__(self, name: str = "Utility Selector", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None):
        """
        Initializes the UtilitySelector node.

        Args:
            name (str): The name of the node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World.
            blackboard (Optional[Any]): The blackboard for data sharing.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.engine: Optional[UtilityAIEngine] = None
        self.trait_service: Optional[TraitService] = None

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
            print("UtilitySelector: Missing AIState component")
            return Status.FAILURE

        # Check for manual override
        if getattr(ai, "manual_override", False):
            # If overridden, we skip utility selection and just return SUCCESS
            # preserving the current action set externally.
            return Status.SUCCESS

        if not self.engine:
             self.engine = self.world.services.try_get(UtilityAIEngine)
             if not self.engine:
                print("UtilitySelector: No Engine found")
                return Status.FAILURE

        # Also try to grab trait service again if missing
        if not self.trait_service:
            self.trait_service = self.world.services.try_get(TraitService)

        stats = self.world.get_component(self.entity_id, YukkuriStats)
        personality = self.world.get_component(self.entity_id, Personality)

        if not stats:
            print("UtilitySelector: Missing YukkuriStats component")
            return Status.FAILURE

        # Build Context for Utility Evaluation
        # The context contains all variables available for considerations to check against.
        # This includes basic stats, social environment data, and personality values.

        # Calculate social context (nearby friends/enemies)
        nearby_yukkuris = []
        if self.world:
            nearby_yukkuris = self.world.get_entities_with(YukkuriStats)

        nearby_friends = 0
        nearby_enemies = 0

        my_trans = self.world.get_component(self.entity_id, Transform)

        if my_trans:
            for other_id in nearby_yukkuris:
                if other_id == self.entity_id:
                    continue

                other_trans = self.world.get_component(other_id, Transform)
                other_stats = self.world.get_component(other_id, YukkuriStats)

                if other_trans and other_stats:
                    # Calculate Euclidean distance
                    dist = ((my_trans.x - other_trans.x)**2 + (my_trans.y - other_trans.y)**2)**0.5
                    if dist < 200.0: # Detection range
                        if other_stats.type_id == stats.type_id:
                            nearby_friends += 1
                        else:
                            nearby_enemies += 1

        context = {
            "hunger": stats.hunger,
            "hunger_inv": 100.0 - stats.hunger, # Inverse hunger (Satiety)
            "energy": stats.energy,
            "energy_inv": 100.0 - stats.energy, # Inverse energy (Tiredness)
            "happiness": stats.happiness,
            "happiness_inv": 100.0 - stats.happiness, # Sadness
            "social": getattr(stats, 'social', 50.0),
            "social_inv": 100.0 - getattr(stats, 'social', 50.0),
            "stress": getattr(stats, 'stress', 0.0),
            "cleanliness": stats.cleanliness,
            "nearby_friends": float(nearby_friends),
            "nearby_enemies": float(nearby_enemies),
            "constant_100": 100.0,
            "constant_0": 0.0
        }

        # Inject Personality Values into Context
        # Allows AI to make decisions based on personality traits (e.g. "Lazy" might value rest more)
        if personality:
            for key, val in personality.values.items():
                context[f"val_{key}"] = val

            # Inject Traits as binary flags for conditional considerations
            for trait in personality.traits:
                context[f"trait_{trait}"] = 1.0

        # Select Action

        # Optimize: populate cached_overrides if missing
        if personality and self.trait_service and personality.cached_overrides is None:
            personality.cached_overrides = self.trait_service.calculate_overrides(personality.traits)

        # We pass personality and trait service to support overrides inside the engine
        # The engine will select the best action based on the highest utility score
        best_action = self.engine.select_action(context, personality, self.trait_service)

        # print(f"DEBUG: UtilitySelector selected {best_action}")

        # Update AI State
        if best_action != ai.current_action:
            ai.current_action = best_action
            ai.action_progress = 0.0
            # Clear failed targets when switching actions to give them another chance later
            if hasattr(ai, 'failed_targets'):
                ai.failed_targets.clear()

        return Status.SUCCESS
