from typing import Optional, Any, TYPE_CHECKING
from py_trees.common import Status

from .utility import UtilityAIEngine
from .base_action import Action

from ..yukkuri_components import AIState, YukkuriStats

if TYPE_CHECKING:
    from ...engine.ecs import World

class UtilitySelector(Action):
    """
    Evaluates utility scores for available actions and selects the best one.
    Updates AIState.current_action.
    """
    def __init__(self, name: str = "Utility Selector", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None):
        super().__init__(name, entity_id, world, blackboard)
        self.engine: Optional[UtilityAIEngine] = None

    def initialise(self) -> None:
        # Try to get engine if not set
        if self.world and not self.engine:
            # Assuming UtilityAIEngine is registered as a service or we can access it via GameManager
            # For now, let's assume it's in world.services
            # Or we can lazily instantiate it? Ideally it's a singleton or service.
            # Let's check services.
            self.engine = self.world.services.try_get(UtilityAIEngine)

    def update(self) -> Status:
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
        context = {
            "hunger": stats.hunger,
            "hunger_inv": 100.0 - stats.hunger,
            "energy": stats.energy,
            "energy_inv": 100.0 - stats.energy,
            "happiness": stats.happiness,
            "happiness_inv": 100.0 - stats.happiness,
            "cleanliness": stats.cleanliness,
            "constant_100": 100.0,
            "constant_0": 0.0
        }

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
