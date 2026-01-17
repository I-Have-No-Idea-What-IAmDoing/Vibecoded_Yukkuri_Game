"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors import (
    BehaviorRegistry,
    create_yukkuri_behavior_tree,
    # Builders (Legacy Support)
    build_eat_behavior,
    build_sleep_behavior,
    build_play_behavior,
    build_wander_behavior,
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

# Legacy alias if needed (though not found in search, adding just in case logic expects it)
Eat = Interact
# Add other re-exports as needed by legacy code/tests

