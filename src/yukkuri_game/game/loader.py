"""
Game Loader Module.
Responsible for initializing and registering game services and systems.
"""

import inspect
from typing import TYPE_CHECKING

import pygame_gui

from ..engine.audio import AudioManager
from ..engine.ecs import World
from ..engine.event_bus import EventBus
from ..game import (
    components,
    components_persistence,
    inventory_component,
    yukkuri_components,
)
from ..game.ai.navigation_service import NavigationService
from ..game.ai.utility import UtilityAIEngine
from ..game.camera import Camera
from ..game.entity_factory import EntityFactory
from ..game.services import EconomyService, GameService, InputService, TimeService
from ..game.settings_service import SettingsService
from ..game.skill_service import SkillService
from ..game.systems.lod_system import LODSystem
from ..game.systems.physics import PhysicsSystem
from ..game.systems.sector_system import SectorMap, SectorSystem
from ..game.trait_service import TraitService
from ..game.utils.evaluator import ConditionEvaluator
from ..config import GameConfig
from ..system_registry import SystemRegistry

if TYPE_CHECKING:
    from ..engine.application import Application
    from ..engine.scene import SceneContext
    from ..game.input_system import InputSystem


class GameLoader:
    """
    Helper class to load and register game components, services and systems.
    """

    def __init__(
        self, world: World, application: "Application", game_config: "GameConfig"
    ):
        """
        Initializes the GameLoader.

        Args:
            world (World): The ECS world.
            application (Application): The application instance.
            game_config (GameConfig): The game configuration.
        """
        self.world = world
        self.application = application
        self.game_config = game_config

    def register_services(
        self,
        context: "SceneContext",
        audio: AudioManager,
        camera: Camera,
        physics_system: PhysicsSystem,
        event_bus: EventBus,
    ) -> None:
        """
        Registers services to the world.

        Args:
            context (SceneContext): The scene context.
            audio (AudioManager): The audio manager.
            camera (Camera): The camera.
            physics_system (PhysicsSystem): The physics system.
            event_bus (EventBus): The event bus.
        """
        self.world.services.register(audio, AudioManager)
        self.world.services.register(camera, Camera)
        self.world.services.register(physics_system, PhysicsSystem)
        self.world.services.register(event_bus, EventBus)
        self.world.services.register(self.game_config, GameConfig)

        # Inject Global State
        money = context.data.get("money", 1000)
        # Default start time to Morning (08:00) if not specified or 0
        # 08:00 = 8/24 * 600 = 200.0
        time_elapsed = context.data.get("time", 600.0)
        if time_elapsed == 0.0:
            time_elapsed = 600.0

        economy_service = EconomyService(initial_money=money)
        self.world.services.register(economy_service, EconomyService)

        time_service = TimeService(
            time_elapsed=time_elapsed,
            scale=self.game_config.time.scale,
            day_start_hour=self.game_config.time.day_start_hour,
            night_start_hour=self.game_config.time.night_start_hour,
        )
        self.world.services.register(time_service, TimeService)

        input_service = InputService()
        self.world.services.register(input_service, InputService)

        settings_service = SettingsService(self.application.resources)
        self.world.services.register(settings_service, SettingsService)

        trait_service = TraitService(self.world)
        self.world.services.register(trait_service, TraitService)

        skill_service = SkillService(self.world, self.game_config.rules.skills)
        self.world.services.register(skill_service, SkillService)

        evaluator = ConditionEvaluator()
        self.world.services.register(evaluator, ConditionEvaluator)

        self._init_navigation_service()
        self._init_sector_system()

    def _init_navigation_service(self) -> None:
        """Initializes the Navigation Service."""
        world_width = self.game_config.world.width
        world_height = self.game_config.world.height
        grid_step_size = getattr(self.game_config.world, "grid_step_size", 25)

        self.world.services.register(
            NavigationService(
                world_width=world_width,
                world_height=world_height,
                grid_step_size=grid_step_size,
                deterministic_mode=self.application.deterministic,
            ),
            NavigationService,
        )

    def _init_sector_system(self) -> None:
        """Initializes and registers the Sector System and Map."""
        world_width = self.game_config.world.width
        world_height = self.game_config.world.height
        sector_size = getattr(self.game_config.world, "sector_size", 500.0)

        sector_system = SectorSystem(
            width=world_width, height=world_height, sector_size=sector_size
        )
        self.world.services.register(sector_system.sector_map, SectorMap)
        self.world.add_system(sector_system)

    def register_factories_and_managers(self) -> None:
        """Registers factories and managers."""
        entity_factory = EntityFactory(self.world)
        self.world.services.register(entity_factory, EntityFactory)

        game_service = GameService(self.world)
        self.world.services.register(game_service, GameService)

        ai_engine = UtilityAIEngine(self.application.resources)
        ai_engine.validate_actions()
        self.world.services.register(ai_engine, UtilityAIEngine)

    def register_systems(
        self,
        camera: Camera,
        physics_system: PhysicsSystem,
        ui_manager: "pygame_gui.UIManager",
    ) -> "InputSystem":
        """Registers all game systems."""
        input_system = SystemRegistry.register_systems(
            self.world,
            camera,
            physics_system,
        )

        # LOD System is not part of SystemRegistry, register it here.
        lod_system = LODSystem()
        self.world.add_system(lod_system)

        input_system.set_ui_manager(ui_manager)
        return input_system

    def collect_component_types(self) -> list[type]:
        """Collects all component types defined in component modules for serialization."""
        comp_types = []
        for module in [
            components,
            yukkuri_components,
            components_persistence,
            inventory_component,
        ]:
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    comp_types.append(obj)
        return comp_types
