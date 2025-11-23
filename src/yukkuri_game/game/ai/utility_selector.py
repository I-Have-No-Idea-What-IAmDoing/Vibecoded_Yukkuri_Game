from typing import Optional, Any, TYPE_CHECKING
from py_trees.common import Status

from .utility import UtilityAIEngine
from .base_action import Action

from ..yukkuri_components import AIState, YukkuriStats, Personality
from ..components import Transform

if TYPE_CHECKING:
    from ...engine.ecs import World

class UtilitySelector(Action):
    """
    Evaluates utility scores for available actions and selects the best one.
    Updates AIState.current_action.
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

    def initialise(self) -> None:
        """
        Initializes the selector, attempting to fetch the UtilityAIEngine service.

        Returns:
            None
        """
        # Try to get engine if not set
        if self.world and not self.engine:
            # Assuming UtilityAIEngine is registered as a service or we can access it via GameManager
            # For now, let's assume it's in world.services
            # Or we can lazily instantiate it? Ideally it's a singleton or service.
            # Let's check services.
            self.engine = self.world.services.try_get(UtilityAIEngine)

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

        if not self.engine:
             # Try to get it again
             self.engine = self.world.services.try_get(UtilityAIEngine)
             if not self.engine:
                # Log error?
                return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        stats = self.world.get_component(self.entity_id, YukkuriStats)

        if not ai or not stats:
            return Status.FAILURE

        # Build Context
        # Map stats to context keys expected by actions.toml

        # Calculate social context
        nearby_yukkuris = []
        if self.world:
            nearby_yukkuris = self.world.get_entities_with(YukkuriStats)

        nearby_friends = 0
        nearby_enemies = 0

        # This is a bit expensive to do every tick per entity, but fine for small scale
        my_trans = self.world.get_component(self.entity_id, Transform)

        if my_trans:
            for other_id in nearby_yukkuris:
                if other_id == self.entity_id:
                    continue

                other_trans = self.world.get_component(other_id, Transform)
                other_stats = self.world.get_component(other_id, YukkuriStats)

                if other_trans and other_stats:
                    dist = ((my_trans.x - other_trans.x)**2 + (my_trans.y - other_trans.y)**2)**0.5
                    if dist < 200.0: # Detection range
                        if other_stats.type_id == stats.type_id:
                            nearby_friends += 1
                        else:
                            nearby_enemies += 1

        context = {
            "hunger": stats.hunger,
            "hunger_inv": 100.0 - stats.hunger,
            "energy": stats.energy,
            "energy_inv": 100.0 - stats.energy,
            "happiness": stats.happiness,
            "happiness_inv": 100.0 - stats.happiness,
            "social": getattr(stats, 'social', 50.0),
            "social_inv": 100.0 - getattr(stats, 'social', 50.0),
            "stress": getattr(stats, 'stress', 0.0),
            "cleanliness": stats.cleanliness,
            "nearby_friends": float(nearby_friends),
            "nearby_enemies": float(nearby_enemies),
            "constant_100": 100.0,
            "constant_0": 0.0
        }

        # Flatten Personality into Context
        personality = self.world.get_component(self.entity_id, Personality)
        if personality:
            for trait in personality.traits:
                context[f"trait:{trait}"] = 1.0
            for val_name, val_score in personality.values.items():
                context[f"val:{val_name}"] = val_score
            context[f"mood:{personality.mood}"] = personality.mood_score

            # Pass the personality object itself via a special key if the engine supports it
            # But the plan says "context injection" which usually means flat keys.
            # However, for Curve Overrides, we need to know the entity ID or personality to look up overrides.
            context["__personality__"] = personality

        # Select Action
        best_action = self.engine.select_action(context)

        # Update AI State
        # If action changed, maybe reset target?
        if best_action != ai.current_action:
            ai.current_action = best_action
            # We don't necessarily reset target here, let the specific behavior handle it
            # But usually switching high level goals means resetting low level plans.
            ai.action_progress = 0.0
            # Only reset target if the new action implies a new target search
            # For now let's not reset target blindly, as "Eat" might persist across frames

        # Always return SUCCESS so the tree continues to execution part
        return Status.SUCCESS
