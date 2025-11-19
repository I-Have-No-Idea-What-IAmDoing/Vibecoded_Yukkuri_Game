"""
The core Utility AI system.
"""
import math
from typing import List, Dict

from game.core.ai.curves import CURVE_FUNCTIONS
from game.core.data.schemas import ActionSchema, ConsiderationSchema
from game.core.ecs.components import Needs, Position, ItemInfo
from game.core.ecs.entity import Entity
from game.core.state.game_state import GameState # This is a bit of a hack


class Consideration:
    """A single factor that contributes to an action's score."""

    def __init__(self, schema: ConsiderationSchema):
        self.schema = schema
        self.curve = CURVE_FUNCTIONS.get(schema.get("curve", "linear"))

    def score(self, entity: Entity, game_state: GameState) -> float:
        """Calculates the score for this consideration."""
        if self.schema["type"] == "need_inverse":
            needs = entity.get_component(Needs)
            need_value = needs.values.get(self.schema["need"], 0.0)
            return self.curve(1.0 - need_value)
        elif self.schema["type"] == "need_level":
            needs = entity.get_component(Needs)
            need_value = needs.values.get(self.schema["need"], 0.0)
            return self.curve(need_value)
        elif self.schema["type"] == "constant":
            return self.schema["value"]
        elif self.schema["type"] == "proximity_to_item_with_tag":
            if not entity.has_component(Position):
                return 0.0

            my_pos = entity.get_component(Position)
            tag_to_find = self.schema["tag"]
            min_dist = float('inf')

            for other_entity in game_state.entities:
                if other_entity.has_component(ItemInfo) and other_entity.has_component(Position):
                    item_info = other_entity.get_component(ItemInfo)
                    if tag_to_find in item_info.tags:
                        other_pos = other_entity.get_component(Position)
                        dist = math.sqrt((my_pos.x - other_pos.x)**2 + (my_pos.y - other_pos.y)**2)
                        if dist < min_dist:
                            min_dist = dist

            # Score is higher the closer the item is. Max score at 0 distance.
            # This curve makes it so the score is high only when very close.
            return self.curve(1.0 - (min_dist / 800.0)) # 800 is screen width, a rough normalization

        return 0.0


class Action:
    """An action that a yukkuri can perform."""

    def __init__(self, schema: ActionSchema):
        self.schema = schema
        self.considerations = [Consideration(c) for c in schema["considerations"]]

    def score(self, entity: Entity, game_state: GameState) -> float:
        """Calculates the total score for this action."""
        total_score = 0.0
        total_weight = 0.0

        for consideration in self.considerations:
            weight = consideration.schema["weight"]
            score = consideration.score(entity, game_state)
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


class AIController:
    """Manages the AI for a single yukkuri."""

    def __init__(self, actions: List[ActionSchema], game_state: GameState):
        self.actions = [Action(a) for a in actions]
        self.game_state = game_state

    def decide(self, entity: Entity) -> Action:
        """Chooses the best action for the yukkuri to perform."""
        best_action = None
        highest_score = -1.0

        for action in self.actions:
            score = action.score(entity, self.game_state)
            if score > highest_score:
                highest_score = score
                best_action = action

        return best_action
