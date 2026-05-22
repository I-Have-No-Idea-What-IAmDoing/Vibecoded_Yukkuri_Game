"""
Gameplay Scene.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
import pygame_gui
from loguru import logger

from ..config import load_config
from ..engine.application import Application
from ..engine.audio import AudioManager
from ..engine.event_manager import EventManager, GamePhase
from ..engine.input_manager import InputContext, InputManager
from ..engine.scene import Scene, SceneContext
from ..game.save_manager import SaveManager
from ..game.ai.navigation_service import NavigationService
from ..game.loader import GameLoader
from ..game.prefabs.yukkuri import create_yukkuri
from ..game.services import EconomyService, GameService
from ..engine.services.time_service import TimeService
from ..game.settings_service import SettingsService
from ..engine.camera import Camera
from ..engine.systems.physics import PhysicsSystem
from ..game.input_system import InputSystem
from .managers.game_session import GameSessionManager
from .managers.input_handler import GameplayInputHandler
from .managers.renderer import GameplayRenderer

if TYPE_CHECKING:
    from ..engine.rendering.system import RenderingSystem
    from ..game.systems.day_night import DayNightSystem
    from ..game.ui.hud import HUD


class GameplayScene(Scene):
    """
    The main gameplay scene.
    """

    INJECTIONS: ClassVar[dict[str, type]] = {"money": int, "time": float}
    INJECTION_DEFAULTS: ClassVar[dict[str, Any]] = {
        "money": 1000,
        "time": 600.0,
    }

    def __init__(self, application: Application) -> None:
        super().__init__(application)
        self.is_setup = False
        
        _theme_path = (
            Path(__file__).parent.parent.parent.parent / "data" / "ui_theme.json"
        )
        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height),
            theme_path=str(_theme_path) if _theme_path.exists() else None,
        )
        self.dt = 0.0

        self.render_system: "RenderingSystem | None" = None
        self.day_night_system: "DayNightSystem | None" = None
        self.hud: "HUD | None" = None
        self.hud_surface: pygame.Surface | None = None
        self.hud_texture: Any = None

        self.game_config: Any = None
        self.camera: Camera
        self.audio: AudioManager
        self.physics_system: PhysicsSystem
        self.event_manager: EventManager
        self.event_bus: Any
        self.input_manager: InputManager
        self.loader: GameLoader
        self.economy_service: EconomyService
        self.time_service: TimeService
        self.settings_service: SettingsService
        self.game_service: GameService
        self.save_manager: SaveManager
        self.input_system: InputSystem
        
        self.session_manager: GameSessionManager
        self.input_handler: GameplayInputHandler
        self.renderer_manager: GameplayRenderer

    def on_enter(self) -> None:
        logger.info("Entered Gameplay Scene")
        self.ui_manager.set_window_resolution(
            (self.application.width, self.application.height)
        )

    def setup(self, context: SceneContext) -> None:
        """
        Sets up the game environment using the plugin architecture.
        """
        self.game_config = load_config()
        self.audio = AudioManager()
        self.audio.load_from_config()
        self.event_manager = EventManager()
        self.event_bus = self.event_manager.bus
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.GAMEPLAY)

        # Initialize Loader
        self.loader = GameLoader(self.world, self.application, self.game_config)

        # Register services
        self.loader.register_services(context, self.audio, self.event_bus)

        # Register Plugins (Core Simulation, Rendering, and Game Systems)
        self.loader.register_plugins()

        # Cache service and system references
        self.economy_service = self.world.services.get(EconomyService)
        self.time_service = self.world.services.get(TimeService)
        self.settings_service = self.world.services.get(SettingsService)
        logger.debug("Attempting to get Camera from services in GameplayScene.setup")
        self.camera = self.world.services.get(Camera)
        logger.debug(f"GameplayScene.setup found camera: {self.camera}")
        self.physics_system = self.world.get_system(PhysicsSystem)
        self.input_system = self.world.get_system(InputSystem)
        self.input_system.set_ui_manager(self.ui_manager)

        self._apply_initial_settings()

        # Factories
        self.loader.register_factories_and_managers()
        self.game_service = self.world.services.get(GameService)

        # Save Manager
        self.save_manager = SaveManager(
            self.world, self.loader.collect_component_types()
        )
        self.world.services.register(self.save_manager, SaveManager)

        # Initialize Managers
        self.session_manager = GameSessionManager(self, self.event_bus)
        self.input_handler = GameplayInputHandler(self, self.session_manager, self.input_manager)
        self.renderer_manager = GameplayRenderer(self, self.event_bus)
        
        self.renderer_manager.setup()
        
        self.is_setup = True

        # Initial population if empty.
        if not self.application.headless and len(self.world.get_all_entities()) == 0:
            start_x = float(self.camera.width) / 2.0
            start_y = float(self.camera.height) / 2.0
            create_yukkuri(self.world, "reimu", start_x, start_y)
            self.camera.camera_x = float(start_x)
            self.camera.camera_y = float(start_y)

    def _apply_initial_settings(self) -> None:
        audio_settings = self.settings_service.settings.audio
        self.audio.set_master_volume(audio_settings.master_volume)
        self.audio.set_bgm_volume(audio_settings.bgm_volume)
        self.audio.set_sfx_volume(audio_settings.sfx_volume)

    def on_exit(self) -> None:
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()
        if hasattr(self, "session_manager"):
            self.session_manager.cleanup()
        if hasattr(self, "renderer_manager"):
            self.renderer_manager.cleanup()
        if hasattr(self, "economy_service") and self.economy_service:
            self.application.scene_manager.set_global_data("money", self.economy_service.money)
        if hasattr(self, "time_service") and self.time_service:
            self.application.scene_manager.set_global_data("time", self.time_service.time_elapsed)
        nav_service = self.world.services.try_get(NavigationService)
        if nav_service:
            nav_service.shutdown()
        if hasattr(self, "audio") and self.audio:
            self.audio.clear()
        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.clear()

    def update(self, dt: float) -> None:
        self.dt = dt
        self.ui_manager.update(dt)
        self.event_manager.process_phase(GamePhase.PRE_UPDATE)
        if not self.session_manager.paused:
            sim_dt = dt * self.session_manager.time_scale
            self.event_manager.process_phase(GamePhase.UPDATE)
        else:
            sim_dt = 0.0
        self.world.update(sim_dt)
        self.camera.update(dt)
        self.event_manager.process_phase(GamePhase.POST_UPDATE)
        self.renderer_manager.update(dt)

    def render(self, alpha: float) -> None:
        self.renderer_manager.render(alpha)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.input_handler.handle_event(event)

    def take_screenshot(self) -> None:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if self.application.screen:
            pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def init_render_system_headless(self) -> None:
        """Initialises the render system if not already set up.

        Used as a safety net when the scene is created outside the
        normal plugin registration flow (e.g. during headless tests).
        """
        if (
            not hasattr(self.renderer_manager, "render_system")
            or self.renderer_manager.render_system is None
        ) and self.application.screen:
            from ..engine.rendering.system import RenderingSystem
            from ..game.systems.rendering.passes import (
                create_gameplay_pipeline,
            )

            render_system = RenderingSystem(
                self.application.screen,
                self.world,
                pipeline=create_gameplay_pipeline(),
                lights_engine=getattr(
                    self.application, "lights_engine", None
                ),
            )
            self.world.services.register(
                render_system, RenderingSystem, replace=True
            )
            self.render_system = render_system
            self.renderer_manager.render_system = render_system

