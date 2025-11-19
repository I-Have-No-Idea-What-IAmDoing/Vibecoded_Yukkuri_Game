"""
Resolves the actions chosen by the AI and applies their effects.
"""
import math
import random
from game.core.ecs.components import Needs, Blackboard, Position, ItemInfo
from game.core.ecs.entity import Entity
from game.core.state.game_state import GameState


def find_closest_item_with_tag(entity: Entity, game_state: GameState, tag: str):
    """Finds the closest item with a given tag."""
    if not entity.has_component(Position):
        return None, float('inf')

    my_pos = entity.get_component(Position)
    min_dist = float('inf')
    closest_item = None

    for item_entity in game_state.entities:
        if item_entity.has_component(ItemInfo) and item_entity.has_component(Position):
            item_info = item_entity.get_component(ItemInfo)
            if tag in item_info.tags:
                item_pos = item_entity.get_component(Position)
                dist = math.sqrt((my_pos.x - item_pos.x)**2 + (my_pos.y - item_pos.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_item = item_entity
    return closest_item, min_dist


def resolve_actions(entity: Entity, game_state: GameState, dt: float):
    """Applies the effects of the entity's current action."""
    if not all(entity.has_component(c) for c in [Blackboard, Needs, Position]):
        return

    blackboard = entity.get_component(Blackboard)
    current_action = blackboard.data.get("current_action")
    needs = entity.get_component(Needs)
    interaction_distance = 30  # pixels

    if current_action == "eat_snack":
        closest_food, dist = find_closest_item_with_tag(entity, game_state, "food")
        if closest_food:
            if dist < interaction_distance:
                # Close enough, apply effect
                item_info = closest_food.get_component(ItemInfo)
                for need, effect in item_info.effects.items():
                    rate = effect.get("rate", 0)
                    current_need = needs.values.get(need, 0)
                    needs.values[need] = max(0.0, min(1.0, current_need + rate * dt))
                if "target_position" in blackboard.data:
                    del blackboard.data["target_position"]
            else:
                # Not close enough, move towards it
                food_pos = closest_food.get_component(Position)
                blackboard.data["target_position"] = (food_pos.x, food_pos.y)
        else:
            if "target_position" in blackboard.data:
                del blackboard.data["target_position"]

    elif current_action == "rest":
        # A simplified version of the above for resting spots
        closest_bed, dist = find_closest_item_with_tag(entity, game_state, "resting_spot")
        if closest_bed:
            if dist < interaction_distance:
                item_info = closest_bed.get_component(ItemInfo)
                for need, effect in item_info.effects.items():
                    rate = effect.get("rate", 0)
                    current_need = needs.values.get(need, 0)
                    needs.values[need] = max(0.0, min(1.0, current_need + rate * dt))
                if "target_position" in blackboard.data:
                    del blackboard.data["target_position"]
            else:
                bed_pos = closest_bed.get_component(Position)
                blackboard.data["target_position"] = (bed_pos.x, bed_pos.y)
        else:
            if "target_position" in blackboard.data:
                del blackboard.data["target_position"]


    elif current_action == "wander":
        if "target_position" not in blackboard.data:
            target_x = random.randint(50, 750)
            target_y = random.randint(50, 550)
            blackboard.data["target_position"] = (target_x, target_y)

    else: # idle or other non-moving action
        if "target_position" in blackboard.data:
            del blackboard.data["target_position"]
