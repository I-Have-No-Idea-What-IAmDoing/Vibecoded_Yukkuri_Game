"""
Module for registering ECS systems.

This module provides a registry class to handle the initialization and registration
of various Entity-Component-System (ECS) systems into the game world.
"""

from typing import TYPE_CHECKING
from .engine.ecs import World
from .engine.event_bus import EventBus
from .game.systems.emotion_system import EmotionSystem
from .game.systems.lifecycle import LifecycleSystem
from .game.systems.behavior import BehaviorSystem
from .game.systems.physics import PhysicsSystem
from .game.systems.visual_movement_system import VisualMovementSystem
from .game.systems.kinematic_movement_system import KinematicMovementSystem
from .game.systems.hierarchy_system import HierarchySystem
from .game.systems.visibility_system import VisibilitySystem
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
    from .game.camera import Camera


class SystemRegistry:
    """
    Helper class to register systems to the ECS World.

    This class provides static methods to instantiate and add systems to the
    world instance, ensuring all necessary dependencies are injected.
    """

    @staticmethod
    def register_systems(
        world: World,
        game_config: "GameConfig",
        camera: "Camera",
        event_bus: EventBus,
        physics_system: PhysicsSystem,
    ) -> InputSystem:
        """
        Registers all game systems to the provided ECS World.

        This method initializes various systems (Time, Physics, Emotion, etc.) with
        necessary configurations and adds them to the world. It also registers
        certain systems as services within the world's service locator.

        Args:
            world (World): The ECS World instance to register systems with.
            game_config (GameConfig): The game configuration object containing rules and settings.
            camera (Camera): The camera object used for view-dependent systems and input.
            event_bus (EventBus): The event bus for inter-system communication.
            physics_system (PhysicsSystem): The pre-initialized physics system.

        Returns:
            InputSystem: The registered input system, which is returned so it can be accessed
                         for event handling in the main loop.
        """

        input_system = InputSystem(camera)
        world.add_system(input_system)

        world.add_system(TimeSystem())
        world.add_system(physics_system)

        world.add_system(EmotionSystem(settings=game_config.rules.stat_decay))
        world.add_system(LifecycleSystem(settings=game_config.rules.lifecycle))
        world.add_system(BehaviorSystem(float(camera.width), float(camera.height)))
        world.add_system(KinematicMovementSystem())
        world.add_system(HierarchySystem())
        world.add_system(VisualMovementSystem())
        world.add_system(ConstructionSystem())
        world.add_system(AnimationSystem())
        world.add_system(VisibilitySystem())
        world.add_system(PoopSystem())
        world.add_system(FeedbackSystem(world))

        hunger_system = HungerSystem()
        world.services.register(hunger_system, HungerSystem)
        world.add_system(hunger_system)

        world.add_system(InteractionSystem())

        social_system = SocialSystem(event_bus)
        world.services.register(social_system, SocialSystem)
        world.add_system(social_system)

        world.add_system(GossipSystem(event_bus))
        world.add_system(FamilySystem())
        world.add_system(GameRulesSystem(event_bus))

        return input_system
