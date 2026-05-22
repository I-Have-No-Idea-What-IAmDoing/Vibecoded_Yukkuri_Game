"""
Game Loader Module.
"""

from typing import TYPE_CHECKING

from loguru import logger
from ..engine.audio import AudioManager
from ..engine.ecs import World
from ..engine.event_bus import EventBus
from ..engine.plugins import CoreSimulationPlugin, CoreRenderingPlugin
from ..game.plugins import GameSystemsPlugin
from .ai.navigation_service import NavigationService
from .ai.utility import UtilityAIEngine
from .entity_factory import EntityFactory
from .services import (
    EconomyService,
    GameService,
    InputService,
)
from ..engine.services.input_buffer_service import InputBufferService
from ..engine.services.time_service import TimeService
from .settings_service import SettingsService
from .skill_service import SkillService
from .trait_service import TraitService
from .utils.evaluator import ConditionEvaluator
from ..config import GameConfig

if TYPE_CHECKING:
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
        event_bus: EventBus,
    ) -> None:
        """
        Registers services to the world.
        """
        from yukkuri_game.engine.protocols import IAudioProvider
        self.world.services.register(audio, IAudioProvider)
        self.world.services.register(event_bus, EventBus)
        self.world.services.register(self.game_config, GameConfig)

        # Inject Global State
        money = context.data.get("money", 1000)
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

        input_buffer_service = InputBufferService()
        self.world.services.register(input_buffer_service, InputBufferService)

        settings_service = SettingsService(self.application.resources)
        self.world.services.register(settings_service, SettingsService)

        trait_service = TraitService(self.world)
        self.world.services.register(trait_service, TraitService)

        skill_service = SkillService(self.world, self.game_config.rules.skills)
        self.world.services.register(skill_service, SkillService)

        evaluator = ConditionEvaluator()
        self.world.services.register(evaluator, ConditionEvaluator)

        self._init_navigation_service()

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

    def register_factories_and_managers(self) -> None:
        """Registers factories and managers."""
        entity_factory = EntityFactory(self.world)
        self.world.services.register(entity_factory, EntityFactory)

        game_service = GameService(self.world)
        self.world.services.register(game_service, GameService)

        ai_engine = UtilityAIEngine(self.application.resources)
        ai_engine.validate_actions()
        self.world.services.register(ai_engine, UtilityAIEngine)

    def register_plugins(self) -> None:
        """Registers core engine and game plugins."""
        logger.debug("Registering CoreSimulationPlugin")
        self.world.register_plugin(CoreSimulationPlugin(gravity=(0, 0), world_settings=self.game_config.world))

        logger.debug("Registering CoreRenderingPlugin")
        pipeline = None
        if not self.application.headless and self.application.screen:
            from .systems.rendering.passes import create_gameplay_pipeline

            pipeline = create_gameplay_pipeline()
        self.world.register_plugin(
            CoreRenderingPlugin(
                screen=self.application.screen,
                settings=self.game_config.world,
                pipeline=pipeline,
            )
        )


        logger.debug("Registering GameSystemsPlugin")
        self.world.register_plugin(GameSystemsPlugin())

    def collect_component_types(self) -> list[type]:
        """Collects all component types for serialization."""
        from ..engine.persistence_registry import PersistenceRegistry
        from ..engine.components import StableIDComponent

        comp_types: list[type] = list(PersistenceRegistry.get_registered_components())
        if StableIDComponent not in comp_types:
            comp_types.append(StableIDComponent)
        return comp_types
