"""
Gameplay Scene.
"""
from loguru import logger
import pygame
import pygame_gui
import os
from datetime import datetime
from typing import ClassVar, Dict, Type

from ..engine.scene import Scene, SceneContext
from ..engine.application import Application
from ..engine.ecs import World
from ..game.yukkurrium import Yukkurrium, RenderSystem
from ..game.ui.hud import HUD
from ..game.systems.physics import PhysicsSystem
from ..system_registry import SystemRegistry
from ..game.events import TogglePauseRequest, CycleSpeedRequest, ResolutionChangedEvent, SaveGameRequest, LoadGameRequest
from ..game.services import EconomyService, TimeService, InputService, GameService
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
from ..game.prefabs.yukkuri import create_yukkuri

class GameplayScene(Scene):
    """
    The main gameplay scene.
    Manages the game world, systems, and UI.
    """

    INJECTIONS: ClassVar[Dict[str, Type]] = {
        "money": int,
        "time": float
    }

    def __init__(self, application: Application):
        super().__init__(application)
        self.is_setup = False
        self.paused = False
        self.time_scale = 1.0
        self.ui_manager = pygame_gui.UIManager((self.application.width, self.application.height))
        self.dt = 0.0

    def on_enter(self) -> None:
        logger.info("Entered Gameplay Scene")
        # setup is called by SceneManager before on_enter
        self.ui_manager.set_window_resolution((self.application.width, self.application.height))

    def setup(self, context: SceneContext) -> None:
        """Sets up the game environment."""
        # Load Config
        self.game_config = load_config()

        self.yukkurrium = Yukkurrium(settings=self.game_config.world)
        self.audio = AudioManager()
        self.audio.load_from_config()

        self.physics_system = PhysicsSystem()
        self.event_manager = EventManager()
        self.event_bus = self.event_manager.bus
        self.input_manager = InputManager()
        self.input_manager.switch_context(InputContext.GAMEPLAY)

        # Collect component types for serializer
        comp_types = []
        for module in [components, yukkuri_components, components_persistence]:
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                     comp_types.append(obj)
        self.serializer = WorldSerializer(self.world, comp_types)

        self._register_services(context)
        self._register_factories_and_managers()
        self._register_systems()

        self.is_setup = True

    def _register_services(self, context: SceneContext) -> None:
        """Registers services to the world."""
        # ResourceManager is already registered by Scene base class

        self.world.services.register(self.audio, AudioManager)
        self.world.services.register(self.yukkurrium, Yukkurrium)
        self.world.services.register(self.physics_system, PhysicsSystem)
        self.world.services.register(self.event_bus, EventBus)
        # EventManager and InputManager are registered by Scene base class if present in Application

        # Inject Global State
        money = context.data.get("money", 1000)
        time_elapsed = context.data.get("time", 0.0)

        self.economy_service = EconomyService(initial_money=money)
        self.world.services.register(self.economy_service, EconomyService)

        self.time_service = TimeService(time_elapsed=time_elapsed)
        self.world.services.register(self.time_service, TimeService)

        self.input_service = InputService()
        self.world.services.register(self.input_service, InputService)

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
        from ..game.entity_factory import EntityFactory
        self.entity_factory = EntityFactory(self.world)
        self.world.services.register(self.entity_factory, EntityFactory)

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
            self.event_bus,
            self.physics_system
        )
        self.input_system.set_ui_manager(self.ui_manager)

        if not self.application.headless:
            self.render_system = RenderSystem(self.application.screen, self.world)
            self.hud = HUD(self.ui_manager, self.world)

            self.event_bus.subscribe(TogglePauseRequest, lambda e: self.toggle_pause())
            self.event_bus.subscribe(CycleSpeedRequest, lambda e: self.cycle_speed())
            self.event_bus.subscribe(ResolutionChangedEvent, self.on_resolution_changed)
            self.event_bus.subscribe(SaveGameRequest, lambda e: self.save(e.filename))
            self.event_bus.subscribe(LoadGameRequest, lambda e: self.load(e.filename))

        # Initial Population if empty
        # Note: In a real scenario, we might want to check if we loaded data first.
        # Since we use `setup` for new games too, we need a flag or logic.
        # But `load` clears database.

        # If we just started a NEW game (not loaded), we might want initial population.
        # For now, we'll assume if no entities, create defaults.
        if not self.application.headless and len(self.world.get_all_entities()) == 0:
            start_x = float(self.yukkurrium.width) / 2.0
            start_y = float(self.yukkurrium.height) / 2.0
            create_yukkuri(self.world, "reimu", start_x, start_y)
            self.yukkurrium.camera_x = float(start_x)
            self.yukkurrium.camera_y = float(start_y)

    def on_exit(self) -> None:
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()

        # Sync back global state to Application/SceneManager
        if hasattr(self, 'economy_service'):
             self.application.scene_manager.set_global_data("money", self.economy_service.get_money())
        if hasattr(self, 'time_service'):
             self.application.scene_manager.set_global_data("time", self.time_service.time_elapsed)

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
        if self.application.headless:
            return

        self.application.width = event.width
        self.application.height = event.height

        surface = pygame.display.get_surface()
        if surface:
            self.application.screen = surface
            self.render_system.screen = surface

        self.ui_manager.set_window_resolution((event.width, event.height))
        if self.hud:
            self.hud.resize(event.width, event.height)

    def take_screenshot(self) -> None:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def save(self, filepath: str) -> None:
        """
        Save the game state (Level + Global).
        We'll save global state to a sidecar file or handle it via SceneManager.
        To keep it simple per requirements:
        - Save entities using WorldSerializer (msgpack)
        - Save global state (money, time) to json sidecar
        """
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Save Level Data
        self.serializer.save_to_file(level_path)

        # Save Global Data
        import json
        global_data = {
            "money": self.economy_service.get_money(),
            "time": self.time_service.time_elapsed
        }
        with open(global_path, "w") as f:
            json.dump(global_data, f)

        logger.info(f"Game saved to {level_path} and {global_path}")

    def load(self, filepath: str) -> None:
        """Load the game world."""
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Check files
        if not os.path.exists(level_path) or not os.path.exists(global_path):
            logger.error(f"Save files not found: {level_path} or {global_path}")
            return

        # Clear World
        self.world.clear_database()
        if hasattr(self, 'physics_system'):
            self.physics_system.clear()
        self.yukkurrium.clear()

        # Load Global Data
        import json
        with open(global_path, "r") as f:
            global_data = json.load(f)

        self.economy_service.set_money(global_data.get("money", 0))
        self.time_service.time_elapsed = global_data.get("time", 0.0)

        # Load Level Data
        self.serializer.load_from_file(level_path)

        # Reconstruct physics bodies
        reconstruct_physics(self.world)
        logger.info("World loaded.")

    def update(self, dt: float) -> None:
        self.dt = dt
        self.ui_manager.update(dt)

        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        if not self.paused:
            sim_dt = dt * self.time_scale
            if hasattr(self, 'time_service'):
                self.time_service.time_elapsed += sim_dt

            self.event_manager.process_phase(GamePhase.UPDATE)
            self.world.update(sim_dt)
            self.yukkurrium.update(sim_dt)

        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        # Clear input state at the end of the frame, after all systems have processed input.
        self.input_manager.update()

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

        if hasattr(self, 'yukkurrium'):
             self.yukkurrium.handle_input(event, self.application.width, self.application.height)

        if self.input_manager.is_action_just_pressed("pause"):
            # Update global state before leaving
            self.application.scene_manager.set_global_data("money", self.economy_service.get_money())
            self.application.scene_manager.set_global_data("time", self.time_service.time_elapsed)

            from .main_menu import MainMenuScene
            self.application.scene_manager.replace(MainMenuScene(self.application))
            return

        if not self.application.headless:
            if self.input_manager.is_action_just_pressed("debug_toggle"):
                 self.hud.toggle_debug()
            elif self.input_manager.is_action_just_pressed("screenshot"):
                 self.take_screenshot()
            elif self.input_manager.is_action_just_pressed("quicksave"):
                 self.save("quicksave")
            elif self.input_manager.is_action_just_pressed("quickload"):
                 self.load("quicksave")

            self.hud.process_event(event)
