"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors.trees import (
    create_yukkuri_behavior_tree,
    BehaviorRegistry,
)

# Re-exporting base Action for convenience if it was used here
from .base_action import Action
