from typing import List, Dict, Any
import math
from src.engine.ecs import System, Entity
from src.engine.components import AIComponent, Stats, Transform, Identity
from src.utils.loader import game_data

class UtilityCurve:
    """Evaluates a normalized input (0-1) against a curve type."""
    @staticmethod
    def evaluate(input_val: float, curve_type: str, params: Dict[str, float]) -> float:
        m = params.get("m", 1.0)
        k = params.get("k", 0.0)
        b = params.get("b", 0.0)
        c = params.get("c", 1.0)

        if curve_type == "linear":
            return m * (input_val - k) + b
        elif curve_type == "inverse_linear":
            return m * (1.0 - (input_val - k)) + b
        elif curve_type == "logistic":
            # Simple logistic function: 1 / (1 + e^(-m*(x-k)))
            try:
                return c / (1.0 + math.exp(-m * (input_val - k))) + b
            except OverflowError:
                return 0.0 if m < 0 else 1.0
        elif curve_type == "inverse_logistic":
             # 1 - logistic
            try:
                return c * (1.0 - (1.0 / (1.0 + math.exp(-m * (input_val - k))))) + b
            except OverflowError:
                return 0.0 if m > 0 else 1.0
        elif curve_type == "boolean":
            return 1.0 if input_val > 0 else 0.0

        return 0.0

class UtilityAI:
    """Calculates utility scores for actions."""
    def __init__(self):
        self.actions_config = game_data.ai_actions

    def normalize_stat(self, val: float, max_val: float) -> float:
        if max_val == 0: return 0.0
        return max(0.0, min(1.0, val / max_val))

    def get_context_value(self, context_key: str, entity: Entity, entities: List[Entity]) -> float:
        stats = entity.get_component(Stats)
        if not stats: return 0.0

        if context_key == "hunger":
            return self.normalize_stat(stats.hunger, stats.max_hunger)
        elif context_key == "energy":
            return self.normalize_stat(stats.energy, stats.max_energy)
        elif context_key == "happiness":
            return self.normalize_stat(stats.happiness, stats.max_happiness)
        elif context_key == "health":
            return self.normalize_stat(stats.health, stats.max_health)
        elif context_key == "food_available":
            # Check if there is any item with type 'food'
            # In a real system, we would find the closest one and cache it
            # For MVP, just check existence
            from src.engine.components import ItemComponent
            has_food = any(e.get_component(ItemComponent).item_type == "food" for e in entities if e.has_component(ItemComponent))
            return 1.0 if has_food else 0.0
        elif context_key == "toy_available":
             from src.engine.components import ItemComponent
             has_toy = any(e.get_component(ItemComponent).item_type == "toy" for e in entities if e.has_component(ItemComponent))
             return 1.0 if has_toy else 0.0
        elif context_key == "partner_available":
             # Check if another Yukkuri is present
             # For MVP, just check if there are more than 1 Yukkuri entities
             from src.engine.components import Identity
             # We need to exclude self. The entity passed is 'entity'.
             # Note: The 'entities' list includes 'entity' usually.
             yukkuri_count = sum(1 for e in entities if e.has_component(Stats) and e.id != entity.id)
             return 1.0 if yukkuri_count > 0 else 0.0

        return 0.0

    def score_action(self, action_name: str, action_def: Dict, entity: Entity, entities: List[Entity]) -> float:
        score = action_def.get("base_score", 0.0)
        considerations = action_def.get("considerations", [])

        if not considerations:
            return score

        # Utility Calculation: Multiplicative.
        # All considerations must be non-zero for the action to have value.
        # score = base_score + (c1 * c2 * ... * cn)
        # This ensures that if a requirement (like food_available) is 0, the result is 0.

        current_score = 1.0

        for cons in considerations:
            input_key = cons["input"]
            input_val = self.get_context_value(input_key, entity, entities)
            curve_val = UtilityCurve.evaluate(input_val, cons["curve"], cons)

            # Clamp 0-1
            curve_val = max(0.0, min(1.0, curve_val))
            current_score *= curve_val

        return score + current_score

    def select_best_action(self, entity: Entity, entities: List[Entity]) -> str:
        best_score = -1.0
        best_action = "wander" # Default

        for action_name, action_def in self.actions_config.items():
            score = self.score_action(action_name, action_def, entity, entities)
            if score > best_score:
                best_score = score
                best_action = action_name

        return best_action

class AISystem(System):
    def __init__(self):
        self.ai_engine = UtilityAI()
        self.decision_interval = 1.0 # seconds
        self.timer = 0.0

    def update(self, delta_time: float, entities: List[Entity], game_state: Any):
        # Only update AI decisions periodically to save perf
        # But timers on individual entities need to update every frame

        ai_entities = [e for e in entities if e.has_component(AIComponent)]

        for entity in ai_entities:
            ai = entity.get_component(AIComponent)

            # Update cooldowns
            for action, cd in list(ai.action_cooldowns.items()):
                ai.action_cooldowns[action] = max(0, cd - delta_time)
                if ai.action_cooldowns[action] <= 0:
                    del ai.action_cooldowns[action]

            # If currently acting, decrease timer
            if ai.current_action:
                ai.action_timer -= delta_time
                if ai.action_timer <= 0:
                    # Action complete
                    self.finish_action(entity, ai.current_action)
                    ai.current_action = None

            # If no action, decide new one
            if not ai.current_action:
                # Simple periodic check per entity could be better, but for MVP:
                # Just decide immediately
                best_action = self.ai_engine.select_best_action(entity, entities)

                # Check cooldown
                if ai.action_cooldowns.get(best_action, 0) <= 0:
                    self.start_action(entity, best_action)

    def start_action(self, entity: Entity, action_name: str):
        ai = entity.get_component(AIComponent)
        action_def = game_data.ai_actions.get(action_name)

        if not action_def:
            return

        ai.current_action = action_name
        ai.action_timer = action_def.get("duration", 1.0)

        # print(f"{entity.get_component(Identity).name} started {action_name}")

    def finish_action(self, entity: Entity, action_name: str):
        ai = entity.get_component(AIComponent)
        action_def = game_data.ai_actions.get(action_name)

        # Apply cooldown
        if action_def:
            ai.action_cooldowns[action_name] = action_def.get("cooldown", 2.0)

        # NOTE: The actual EFFECTS of the action (eating restores hunger)
        # should probably happen in InteractionSystem or here.
        # For clean separation, let's handle instantaneous effects here or emit an event.
        # For MVP, we can handle simple stat changes here or in a dedicated method.
