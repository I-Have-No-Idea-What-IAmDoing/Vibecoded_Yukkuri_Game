"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors import (
    # Trees / Builders
    BehaviorRegistry,
    create_yukkuri_behavior_tree,
    build_flee_behavior,
    build_hunt_behavior,
    build_seek_light_behavior,
    build_standard_interaction_behavior,
    build_wander_behavior,
    build_eat_behavior,
    build_play_behavior,
    build_sleep_behavior,
    # Actions
    Idle,
    Check,
    CheckEmotion,
    MoveToTarget,
    Wander,
    Swoop,
    FleePredator,
    FleeFromTarget,
    FindItem,
    FindLightSource,
    FindPrey,
    FindThreat,
    FindSocialTarget,
    PickFood,
    Interact,
    SocialInteract,
    EatPrey,
    Sleep,
)

__all__ = [
    # Trees / Builders
    "BehaviorRegistry",
    "create_yukkuri_behavior_tree",
    "build_flee_behavior",
    "build_hunt_behavior",
    "build_seek_light_behavior",
    "build_standard_interaction_behavior",
    "build_standard_interaction_behavior",
    "build_wander_behavior",
    "build_eat_behavior",
    "build_play_behavior",
    "build_sleep_behavior",
    # Actions
    "Idle",
    "Check",
    "CheckEmotion",
    "MoveToTarget",
    "Wander",
    "Swoop",
    "FleePredator",
    "FleeFromTarget",
    "FindItem",
    "FindLightSource",
    "FindPrey",
    "FindThreat",
    "FindSocialTarget",
    "PickFood",
    "Interact",
    "SocialInteract",
    "EatPrey",
    "Sleep",
]
