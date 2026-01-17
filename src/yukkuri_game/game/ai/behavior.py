"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors import (
    Interact,
    BehaviorRegistry,
    create_yukkuri_behavior_tree,
)

__all__ = [
    "Interact",
    "Eat",
    "BehaviorRegistry",
    "create_yukkuri_behavior_tree",
]
