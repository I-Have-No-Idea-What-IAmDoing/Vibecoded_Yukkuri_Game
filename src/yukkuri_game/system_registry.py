"""
Module for registering ECS systems.

This module provides a registry class to handle the initialization and registration
of various Entity-Component-System (ECS) systems into the game world.
"""

from typing import TYPE_CHECKING, Any

from .engine.ecs import World, System
from .game.input_system import InputSystem
from .game.systems.command_processor_system import CommandProcessorSystem
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
from .engine.systems.physics import PhysicsSystem
from .game.systems.poop_system import PoopSystem
from .game.systems.social_system import SocialSystem
from .game.systems.steering_system import SteeringSystem
from .engine.systems.time import TimeSystem
from .game.systems.visibility_system import VisibilitySystem
from .game.systems.visual_movement_system import VisualMovementSystem

if TYPE_CHECKING:
    from .engine.camera import Camera


class SystemRegistry:
    """
    Helper class to register systems to the ECS World.

    This class provides static methods to instantiate and add systems to the
    world instance, ensuring all necessary dependencies are injected.
    """

    @staticmethod
    def register_systems(
        world: World,
        camera: "Camera",
        physics_system: PhysicsSystem,
    ) -> InputSystem:
        """
        Registers all game systems to the provided ECS World.

        All systems now fetch their dependencies (EventBus, GameConfig, etc.)
        from the world's service locator via their initialize() lifecycle hook.

        Args:
            world: The ECS World instance to register systems with.
            camera: The camera object used for input handling.
            physics_system: The pre-initialized physics system.

        Returns:
            The registered input system.
        """

        input_system = InputSystem(camera)
        world.add_system(input_system)

        # CommandProcessorSystem runs first so all commands are resolved
        # before any gameplay system reads the resulting world state.
        world.add_system(CommandProcessorSystem())

        def add_system(system: System, service_type: type[Any] | None = None) -> None:
            world.add_system(system)
            if service_type is not None:
                world.services.register(system, service_type)

        # Systems are processed in the order they are added.
        # 1. Time & Physics (Simulation Core)
        add_system(TimeSystem())
        add_system(physics_system)

        add_system(EmotionSystem())
        add_system(LifecycleSystem())

        # Navigation & AI
        add_system(NavigationSystem())
        add_system(NavigationUpdateSystem())
        add_system(BehaviorSystem())

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
        add_system(FeedbackSystem())

        hunger_system = HungerSystem()
        add_system(hunger_system, HungerSystem)

        add_system(InteractionSystem())

        social_system = SocialSystem()
        add_system(social_system, SocialSystem)

        add_system(GossipSystem())
        add_system(FamilySystem())
        add_system(GameRulesSystem())
        add_system(InventorySystem())

        # Mouse Light System (disabled by default)
        mouse_light_system = MouseLightSystem()
        add_system(mouse_light_system, MouseLightSystem)

        return input_system
