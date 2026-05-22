"""
Game-specific Plugins.
"""

from loguru import logger
from ..engine.ecs import Plugin, World
from .input_system import InputSystem
from .systems.command_processor_system import CommandProcessorSystem
from .systems.animation import AnimationSystem
from .systems.behavior import BehaviorSystem
from .systems.construction_system import ConstructionSystem
from .systems.emotion_system import EmotionSystem
from .systems.family_system import FamilySystem
from .systems.feedback_system import FeedbackSystem
from .systems.flight_system import FlightSystem
from .systems.game_rules_system import GameRulesSystem
from .systems.gossip_system import GossipSystem
from .systems.hierarchy_system import HierarchySystem
from .systems.hunger_system import HungerSystem
from .systems.interaction_system import InteractionSystem
from .systems.inventory_system import InventorySystem
from .systems.kinematic_movement_system import KinematicMovementSystem
from .systems.lifecycle import LifecycleSystem
from .systems.mouse_light_system import MouseLightSystem
from .systems.navigation_system import NavigationSystem
from .systems.navigation_update_system import NavigationUpdateSystem
from .systems.perception_system import PerceptionSystem
from .systems.poop_system import PoopSystem
from .systems.social_system import SocialSystem
from .systems.steering_system import SteeringSystem
from .systems.visibility_system import VisibilitySystem
from .systems.visual_movement_system import VisualMovementSystem
from ..engine.camera import Camera


class GameSystemsPlugin(Plugin):
    """
    Plugin that registers all game-specific systems.
    """

    def register(self, world: World) -> None:
        logger.debug("GameSystemsPlugin.register called")
        camera = world.services.try_get(Camera)
        if camera is None:
            logger.warning(
                "Camera service not found. Registering fallback."
            )
            camera = Camera()
            world.services.register(camera, Camera)
        logger.debug(f"GameSystemsPlugin found camera: {camera}")
        
        # Input and Commands
        logger.debug("Adding InputSystem")
        world.add_system(InputSystem(camera))
        logger.debug("Adding CommandProcessorSystem")
        world.add_system(CommandProcessorSystem())

        # Gameplay Systems
        logger.debug("Adding EmotionSystem")
        world.add_system(EmotionSystem())
        logger.debug("Adding LifecycleSystem")
        world.add_system(LifecycleSystem())
        logger.debug("Adding NavigationSystem")
        world.add_system(NavigationSystem())
        logger.debug("Adding NavigationUpdateSystem")
        world.add_system(NavigationUpdateSystem())
        logger.debug("Adding BehaviorSystem")
        world.add_system(BehaviorSystem())
        logger.debug("Adding SteeringSystem")
        world.add_system(SteeringSystem())
        logger.debug("Adding KinematicMovementSystem")
        world.add_system(KinematicMovementSystem())
        logger.debug("Adding FlightSystem")
        world.add_system(FlightSystem())
        logger.debug("Adding HierarchySystem")
        world.add_system(HierarchySystem())
        logger.debug("Adding VisualMovementSystem")
        world.add_system(VisualMovementSystem())
        logger.debug("Adding ConstructionSystem")
        world.add_system(ConstructionSystem())
        logger.debug("Adding AnimationSystem")
        world.add_system(AnimationSystem())
        logger.debug("Adding VisibilitySystem")
        world.add_system(VisibilitySystem())
        logger.debug("Adding PerceptionSystem")
        world.add_system(PerceptionSystem())
        logger.debug("Adding PoopSystem")
        world.add_system(PoopSystem())
        logger.debug("Adding FeedbackSystem")
        world.add_system(FeedbackSystem())

        logger.debug("Adding HungerSystem")
        hunger_system = HungerSystem()
        world.add_system(hunger_system)
        world.services.register(hunger_system, HungerSystem)

        logger.debug("Adding InteractionSystem")
        world.add_system(InteractionSystem())

        logger.debug("Adding SocialSystem")
        social_system = SocialSystem()
        world.add_system(social_system)
        world.services.register(social_system, SocialSystem)

        logger.debug("Adding GossipSystem")
        world.add_system(GossipSystem())
        logger.debug("Adding FamilySystem")
        world.add_system(FamilySystem())
        logger.debug("Adding GameRulesSystem")
        world.add_system(GameRulesSystem())
        logger.debug("Adding InventorySystem")
        world.add_system(InventorySystem())

        logger.debug("Adding MouseLightSystem")
        mouse_light_system = MouseLightSystem()
        world.add_system(mouse_light_system)
        world.services.register(mouse_light_system, MouseLightSystem)
        
        logger.debug("GameSystemsPlugin.register completed successfully")
