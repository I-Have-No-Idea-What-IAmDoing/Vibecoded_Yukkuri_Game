"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors.trees import (
    BehaviorRegistry,
    create_yukkuri_behavior_tree,
    build_eat_behavior,
    build_sleep_behavior,
    build_play_behavior,
    build_wander_behavior,
    build_seek_light_behavior,
    build_hunt_behavior,
    build_flee_behavior,
    build_standard_interaction_behavior,
)
from .behaviors.actions.basic import (
    Idle,
    Check,
    CheckEmotion,
)
from .behaviors.actions.movement import (
    MoveToTarget,
    Wander,
    Swoop,
    FleePredator,
    FleeFromTarget,
)
from .behaviors.actions.searching import (
    FindItem,
    FindLightSource,
    FindPrey,
    FindThreat,
    FindSocialTarget,
    PickFood,
)
from .behaviors.actions.interaction import (
    Interact,
    SocialInteract,
    EatPrey,
)
from .behaviors.actions.survival import (
    Sleep,
)

# Re-exporting base Action for convenience if it was used here (it was imported from .base_action)
from .base_action import Action
