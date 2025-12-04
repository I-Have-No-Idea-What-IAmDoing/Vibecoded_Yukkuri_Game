"""
Module for registering ECS systems.
"""

from typing import TYPE_CHECKING
from .engine.ecs import World
from .engine.event_bus import EventBus
from .game.systems.emotion_system import EmotionSystem
from .game.systems.lifecycle import LifecycleSystem
from .game.systems.behavior import BehaviorSystem
from .game.systems.physics import PhysicsSystem
from .game.systems.movement_system import MovementSystem
from .game.systems.kinematic_movement_system import KinematicMovementSystem
from .game.systems.hierarchy_system import HierarchySystem
from .game.systems.dismount_system import DismountSystem
from .game.systems.construction_system import ConstructionSystem
from .game.systems.animation import AnimationSystem
from .game.systems.poop_system import PoopSystem
from .game.systems.feedback_system import FeedbackSystem
from .game.systems.hunger_system import HungerSystem
from .game.systems.interaction_system import InteractionSystem
from .game.systems.social_system import SocialSystem
from .game.systems.gossip_system import GossipSystem
from .game.systems.family_system import FamilySystem
from .game.systems.game_rules_system import GameRulesSystem
from .game.input_system import InputSystem
from .game.systems.time_system import TimeSystem

if TYPE_CHECKING:
    from .config import GameConfig
    from .game.yukkurrium import Yukkurrium


class SystemRegistry:
    """
    Helper class to register systems to the ECS World.
    """

    @staticmethod
    def register_systems(
        world: World,
        game_config: "GameConfig",
        yukkurrium: "Yukkurrium",
        event_bus: EventBus,
        physics_system: PhysicsSystem,
    ) -> InputSystem:
        """
        Registers all game systems.

        Args:
            world (World): The ECS World.
            game_config (GameConfig): The game configuration.
            yukkurrium (Yukkurrium): The game world view.
            event_bus (EventBus): The event bus.
            physics_system (PhysicsSystem): The physics system (pre-initialized).

        Returns:
            InputSystem: The registered input system (needed for event handling).
        """

        input_system = InputSystem(yukkurrium)
        world.add_system(input_system)

        world.add_system(TimeSystem())
        world.add_system(physics_system)

        world.add_system(EmotionSystem(settings=game_config.rules.stat_decay))
        world.add_system(LifecycleSystem(settings=game_config.rules.lifecycle))
        world.add_system(
            BehaviorSystem(float(yukkurrium.width), float(yukkurrium.height))
        )
        # world.add_system(MovementSystem())
        world.add_system(KinematicMovementSystem())
        world.add_system(HierarchySystem())
        world.add_system(DismountSystem())
        world.add_system(ConstructionSystem())
        world.add_system(AnimationSystem())
        world.add_system(PoopSystem())
        world.add_system(FeedbackSystem(world))
        world.add_system(HungerSystem())
        world.add_system(InteractionSystem())
        world.add_system(SocialSystem(event_bus))
        world.add_system(GossipSystem(event_bus))
        world.add_system(FamilySystem())
        world.add_system(GameRulesSystem(event_bus))

        return input_system
