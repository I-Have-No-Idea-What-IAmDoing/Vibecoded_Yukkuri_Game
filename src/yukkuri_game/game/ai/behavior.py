"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors.trees import (
    create_yukkuri_behavior_tree,
    BehaviorRegistry,
    build_eat_behavior,
    build_sleep_behavior,
    build_play_behavior,
    build_wander_behavior,
)

# Re-exporting base Action for convenience if it was used here
from .base_action import Action
from .behaviors.actions.movement import MoveToTarget, Wander, Swoop, FleePredator, FleeFromTarget
from .behaviors.actions.interaction import Interact, EatPrey
from .behaviors.actions.searching import FindItem, FindPrey, FindThreat
