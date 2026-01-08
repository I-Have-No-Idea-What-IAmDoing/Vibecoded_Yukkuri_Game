"""
Game Loader Module.
Responsible for initializing and registering game services and systems.
"""

import inspect
from typing import TYPE_CHECKING, Type

from ..engine.ecs import World
from ..engine.event_bus import EventBus
from ..engine.audio import AudioManager
from ..game import components, components_persistence, yukkuri_components
from ..game.services import EconomyService, GameService, InputService, TimeService
from ..game.settings_service import SettingsService
from ..game.systems.physics import PhysicsSystem
from ..game.systems.sector_system import SectorMap, SectorSystem
from ..game.trait_service import TraitService
from ..game.skill_service import SkillService
from ..game.camera import Camera
from ..game.utils.evaluator import ConditionEvaluator
from ..game.entity_factory import EntityFactory
from ..game.ai.utility import UtilityAIEngine
from ..game.ai.navigation_service import NavigationService
from ..system_registry import SystemRegistry

if TYPE_CHECKING:
    from ..config import GameConfig
    from ..engine.application import Application
    from ..engine.scene import SceneContext


class GameLoader:
    """
    Helper class to load and register game components, services and systems.
    """

    def __init__(
        self, world: World, application: "Application", game_config: "GameConfig"
    ):
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
        """Registers services to the world."""
        self.world.services.register(audio, AudioManager)
        self.world.services.register(camera, Camera)
        self.world.services.register(physics_system, PhysicsSystem)
        self.world.services.register(event_bus, EventBus)

        # Inject Global State
        money = context.data.get("money", 1000)
        # Default start time to Morning (08:00) if not specified or 0
        # 08:00 = 8/24 * 600 = 200.0
        time_elapsed = context.data.get("time", 200.0)
        if time_elapsed == 0.0:
            time_elapsed = 200.0

        economy_service = EconomyService(initial_money=money)
        self.world.services.register(economy_service, EconomyService)

        time_service = TimeService(time_elapsed=time_elapsed)
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
        world_width = 3000
        world_height = 3000
        grid_step_size = 25  # Default from NavigationService constructor
        if self.game_config:
            world_width = self.game_config.world.width
            world_height = self.game_config.world.height
            grid_step_size = self.game_config.world.grid_step_size

        self.world.services.register(
            NavigationService(
                world_width=world_width,
                world_height=world_height,
                grid_step_size=grid_step_size,
            ),
            NavigationService,
        )

    def _init_sector_system(self) -> None:
        """Initializes and registers the Sector System and Map."""
        world_width = 3000
        world_height = 3000
        sector_size = 500.0

        if self.game_config:
            world_width = self.game_config.world.width
            world_height = self.game_config.world.height
            if hasattr(self.game_config.world, "sector_size"):
                sector_size = self.game_config.world.sector_size

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
        event_bus: EventBus,
        physics_system: PhysicsSystem,
        ui_manager: "pygame_gui.UIManager",
    ) -> "InputSystem":
        """Registers all game systems."""
        input_system = SystemRegistry.register_systems(
            self.world,
            self.game_config,
            camera,
            event_bus,
            physics_system,
        )
        input_system.set_ui_manager(ui_manager)
        return input_system

    def collect_component_types(self) -> list[Type]:
        """Collects all component types for serialization."""
        comp_types = []
        for module in [components, yukkuri_components, components_persistence]:
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    comp_types.append(obj)
        return comp_types
