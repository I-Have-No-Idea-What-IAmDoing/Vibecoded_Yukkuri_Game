"""
Gameplay Scene.
"""
from loguru import logger
import pygame
import pygame_gui
import os
from datetime import datetime
from ..engine.scene import Scene
from ..engine.application import Application
from ..engine.ecs import World
# GameManager is removed
from ..game.entity_factory import EntityFactory
from ..game.yukkurrium import Yukkurrium, RenderSystem
from ..game.ui.hud import HUD
from ..game.systems.physics import PhysicsSystem
from ..system_registry import SystemRegistry
from ..game.events import TogglePauseRequest, CycleSpeedRequest, ResolutionChangedEvent
from ..game.services import EconomyService, PersistenceService, TimeService, InputService, GameService
from ..game.settings_service import SettingsService
from ..game.trait_service import TraitService
from ..engine.event_bus import EventBus
from ..engine.event_manager import EventManager, GamePhase
from ..engine.input_manager import InputManager, InputContext
from ..engine.audio import AudioManager
import inspect
from ..engine.serializer import WorldSerializer
from ..config import load_config
from ..game import components, yukkuri_components, components_persistence
from ..game.ai.utility import UtilityAIEngine
from ..game.systems.sector_system import SectorMap, SectorSystem
from ..game.ai.navigation_service import NavigationService
from ..game.systems.physics_reconstruction import reconstruct_physics

class GameplayScene(Scene):
    """
    The main gameplay scene.
    Manages the game world, systems, and UI.
    """
    def __init__(self, application: Application):
        super().__init__(application)
        self.is_setup = False
        self.paused = False
        self.time_scale = 1.0
        # Use a local UI manager to prevent state leaks when switching scenes
        self.ui_manager = pygame_gui.UIManager((self.application.width, self.application.height))
        self.dt = 0.0

    def on_enter(self) -> None:
        logger.info("Entered Gameplay Scene")
        if not self.is_setup:
            self.setup()
        self.ui_manager.set_window_resolution((self.application.width, self.application.height))

    def setup(self) -> None:
        """Sets up the game environment."""
        # Load Config
        self.game_config = load_config()

        self.yukkurrium = Yukkurrium(settings=self.game_config.world)
        self.audio = AudioManager()
        self.audio.load_from_config()

        self.physics_system = PhysicsSystem()
        self.event_manager = EventManager()
        self.event_bus = self.event_manager.bus # Use the bus from the manager
        self.input_manager = InputManager()
        self.input_manager.switch_context(InputContext.GAMEPLAY)

        # Collect component types for serializer
        comp_types = []
        for module in [components, yukkuri_components, components_persistence]:
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                     comp_types.append(obj)
        self.serializer = WorldSerializer(self.world, comp_types)

        self._register_services()
        self._register_factories_and_managers()
        self._register_systems()

        self.is_setup = True

    def _register_services(self) -> None:
        """Registers services to the world."""
        # Use application's resource manager
        self.world.services.register(self.application.resources, type(self.application.resources))

        self.world.services.register(self.audio, AudioManager)
        self.world.services.register(self.yukkurrium, Yukkurrium)
        self.world.services.register(self.physics_system, PhysicsSystem)
        self.world.services.register(self.event_manager, EventManager)
        self.world.services.register(self.event_bus, EventBus)
        self.world.services.register(self.input_manager, InputManager)

        self.economy_service = EconomyService()
        self.world.services.register(self.economy_service, EconomyService)

        self.time_service = TimeService()
        self.world.services.register(self.time_service, TimeService)

        self.input_service = InputService()
        self.world.services.register(self.input_service, InputService)

        self.persistence_service = PersistenceService(self.world)
        self.world.services.register(self.persistence_service, PersistenceService)

        self.settings_service = SettingsService()
        self.world.services.register(self.settings_service, SettingsService)

        self.trait_service = TraitService(self.world)
        self.world.services.register(self.trait_service, TraitService)

        self._init_navigation_service()
        self._init_sector_system()

        self._apply_initial_settings()

    def _init_navigation_service(self) -> None:
        """Initializes the Navigation Service."""
        world_width = 3000
        world_height = 3000

        if self.game_config:
            world_width = self.game_config.world.width
            world_height = self.game_config.world.height
            self.world.services.register(
                 NavigationService(
                     world_width=world_width,
                     world_height=world_height,
                     grid_step_size=self.game_config.world.grid_step_size
                 )
             )
        else:
             self.world.services.register(NavigationService(world_width, world_height))

    def _init_sector_system(self) -> None:
        """Initializes and registers the Sector System and Map."""
        world_width = 3000
        world_height = 3000
        sector_size = 500.0

        if self.game_config:
            world_width = self.game_config.world.width
            world_height = self.game_config.world.height
            if hasattr(self.game_config.world, 'sector_size'):
                sector_size = self.game_config.world.sector_size

        sector_system = SectorSystem(width=world_width, height=world_height, sector_size=sector_size)
        self.world.services.register(sector_system.sector_map, SectorMap)
        self.world.add_system(sector_system)

    def _apply_initial_settings(self) -> None:
        audio_settings = self.settings_service.settings.get("audio", {})
        self.audio.set_master_volume(audio_settings.get("master_volume", 0.5))
        self.audio.set_bgm_volume(audio_settings.get("bgm_volume", 0.5))
        self.audio.set_sfx_volume(audio_settings.get("sfx_volume", 0.5))

    def _register_factories_and_managers(self) -> None:
        self.factory = EntityFactory(self.world)
        self.world.services.register(self.factory, EntityFactory)

        self.game_service = GameService(self.world)
        self.world.services.register(self.game_service, GameService)

        self.ai_engine = UtilityAIEngine(self.application.resources)
        self.ai_engine.validate_actions()
        self.world.services.register(self.ai_engine, UtilityAIEngine)

    def _register_systems(self) -> None:
        self.input_system = SystemRegistry.register_systems(
            self.world,
            self.game_config,
            self.yukkurrium,
            self.factory,
            self.event_bus,
            self.physics_system
        )

        if not self.application.headless:
            self.render_system = RenderSystem(self.application.screen, self.world)
            # Use local UI manager
            self.hud = HUD(self.ui_manager, self.world)

            self.event_bus.subscribe(TogglePauseRequest, lambda e: self.toggle_pause())
            self.event_bus.subscribe(CycleSpeedRequest, lambda e: self.cycle_speed())
            self.event_bus.subscribe(ResolutionChangedEvent, self.on_resolution_changed)

        # Initial Population
        if not self.application.headless:
            start_x = float(self.yukkurrium.width) / 2.0
            start_y = float(self.yukkurrium.height) / 2.0
            self.factory.create_yukkuri("reimu", start_x, start_y)
            self.yukkurrium.camera_x = float(start_x)
            self.yukkurrium.camera_y = float(start_y)

    def on_exit(self) -> None:
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def cycle_speed(self) -> None:
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0
        self.time_scale = speeds[next_idx]
        if self.hud.layout.speed_btn:
            self.hud.layout.speed_btn.set_text(f"{self.time_scale}x")

    def on_resolution_changed(self, event: ResolutionChangedEvent) -> None:
        """
        Handles resolution change events.

        Args:
            event (ResolutionChangedEvent): The resolution changed event.
        """
        if self.application.headless:
            return

        self.application.width = event.width
        self.application.height = event.height

        # Handle screen update
        surface = pygame.display.get_surface()
        if surface:
            self.application.screen = surface
            self.render_system.screen = surface

        self.ui_manager.set_window_resolution((event.width, event.height))
        # Notify HUD
        if self.hud:
            self.hud.resize(event.width, event.height)

    def take_screenshot(self) -> None:
        """
        Captures a screenshot and saves it to the 'screenshots' directory.
        """
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def save(self, filepath: str) -> None:
        """Save the game world."""
        self.serializer.save_to_file(filepath)

    def load(self, filepath: str) -> None:
        """Load the game world."""
        self.world.clear_database()
        if hasattr(self, 'physics_system'):
            self.physics_system.clear()
        self.yukkurrium.clear() # Clear spatial partition if needed
        # Re-register singletons or systems? clear_database clears components and entities.
        # Systems are separate in Esper.
        # However, we might need to re-setup some basic state.

        self.serializer.load_from_file(filepath)

        # Reconstruct physics bodies
        reconstruct_physics(self.world)
        logger.info("World loaded. Physics bodies reconstructed.")

    def update(self, dt: float) -> None:
        self.dt = dt
        self.ui_manager.update(dt) # Update local UI
        self.input_manager.update()

        # Process Pre-Update Events
        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        if not self.paused:
            sim_dt = dt * self.time_scale
            # Update time service directly
            if hasattr(self, 'time_service'):
                self.time_service.time_elapsed += sim_dt

            self.event_manager.process_phase(GamePhase.UPDATE)
            self.world.update(sim_dt)
            self.yukkurrium.update(sim_dt)

        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        if not self.application.headless:
            self.hud.fps = self.application.clock.get_fps()
            self.hud.update(dt)

    def render(self) -> None:
        self.render_world()

        if not self.application.headless:
            self.hud.draw(self.application.screen)
            self.ui_manager.draw_ui(self.application.screen)

    def render_world(self) -> None:
        if hasattr(self, 'render_system') and self.render_system:
            self.render_system.update(self.world, self.dt)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui_manager.process_events(event)
        self.input_manager.process_event(event)

        if self.input_manager.is_action_just_pressed("pause"):
            from .main_menu import MainMenuScene
            self.application.scene_manager.replace(MainMenuScene(self.application))
            return

        # Always handle input system events
        # TODO: Refactor legacy input system to use InputManager completely
        if hasattr(self, 'input_system') and self.input_system:
            self.input_system.handle_event(event, self.world, self.application.width, self.application.height, self.ui_manager)

        if not self.application.headless:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.hud.toggle_debug()
                elif event.key == pygame.K_F12:
                    self.take_screenshot()
                elif event.key == pygame.K_F5:
                    self.save("quicksave.json")
                elif event.key == pygame.K_F9:
                    self.load("quicksave.json")

            self.hud.process_event(event)
