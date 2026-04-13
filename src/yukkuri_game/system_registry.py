"""
Module for registering ECS systems.

This module provides a registry class to handle the initialization and registration
of various Entity-Component-System (ECS) systems into the game world.
"""

from typing import TYPE_CHECKING, Any

from .engine.ecs import World, System
from .engine.event_bus import EventBus
from .game.input_system import InputSystem
from .game.systems.animation import AnimationSystem
from .game.systems.behavior import BehaviorSystem
from .game.systems.construction_system import ConstructionSystem
from .game.systems.emotion_system import EmotionSystem
from .game.systems.family_system import FamilySystem
from .game.systems.feedback_system import FeedbackSystem
from .game.systems.flight_system import FlightSystem
from .game.systems.game_rules_system import GameRulesSystem
from .game.systems.gossip_system import GossipSystem
from .game.systems.hierarchy_system import HierarchySystem
from .game.systems.hunger_system import HungerSystem
from .game.systems.interaction_system import InteractionSystem
from .game.systems.inventory_system import InventorySystem
from .game.systems.kinematic_movement_system import KinematicMovementSystem
from .game.systems.lifecycle import LifecycleSystem
from .game.systems.mouse_light_system import MouseLightSystem
from .game.systems.navigation_system import NavigationSystem
from .game.systems.navigation_update_system import NavigationUpdateSystem
from .game.systems.perception_system import PerceptionSystem
from .game.systems.physics import PhysicsSystem
from .game.systems.poop_system import PoopSystem
from .game.systems.social_system import SocialSystem
from .game.systems.steering_system import SteeringSystem
from .game.systems.time_system import TimeSystem
from .game.systems.visibility_system import VisibilitySystem
from .game.systems.visual_movement_system import VisualMovementSystem

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
            world: The ECS World instance to register systems with.
            game_config: The game configuration object containing rules and settings.
            camera: The camera object used for view-dependent systems and input.
            event_bus: The event bus for inter-system communication.
            physics_system: The pre-initialized physics system.

        Returns:
            The registered input system, which is returned so it can be accessed
            for event handling in the main loop.
        """

        input_system = InputSystem(camera)
        world.add_system(input_system)

        def add_system(system: System, service_type: type[Any] | None = None) -> None:
            if service_type is not None:
                world.services.register(system, service_type)
            world.add_system(system)

        # Systems are processed in the order they are added.
        # 1. Time & Physics (Simulation Core)
        add_system(TimeSystem())
        add_system(physics_system)

        add_system(EmotionSystem(settings=game_config.rules.stat_decay))
        add_system(LifecycleSystem(settings=game_config.rules.lifecycle))

        # Navigation & AI
        add_system(NavigationSystem())
        add_system(NavigationUpdateSystem())
        add_system(BehaviorSystem(float(camera.width), float(camera.height)))

        # Movement Pipeline
        add_system(SteeringSystem())
        add_system(KinematicMovementSystem())
        add_system(FlightSystem())  # Handles flight stamina/altitude logic
        add_system(HierarchySystem())
        add_system(VisualMovementSystem())
        add_system(ConstructionSystem())
        add_system(AnimationSystem())
        add_system(VisibilitySystem())
        add_system(
            PerceptionSystem()
        )  # Proposal 4: Populates Blackboard from visibility
        add_system(PoopSystem())
        add_system(FeedbackSystem(world))

        hunger_system = HungerSystem()
        add_system(hunger_system, HungerSystem)

        add_system(InteractionSystem())

        social_system = SocialSystem(event_bus)
        add_system(social_system, SocialSystem)

        add_system(GossipSystem(event_bus))
        add_system(FamilySystem())
        add_system(GameRulesSystem(event_bus))
        add_system(InventorySystem())

        # Mouse Light System (disabled by default)
        mouse_light_system = MouseLightSystem(world, camera)
        add_system(mouse_light_system, MouseLightSystem)

        return input_system
