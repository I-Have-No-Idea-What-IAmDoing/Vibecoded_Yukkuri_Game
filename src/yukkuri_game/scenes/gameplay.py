"""
Gameplay Scene.

This module defines the `GameplayScene`, which is the primary interactive scene
where the game simulation occurs. It manages the lifecycle of game systems, UI,
and world state.
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
from ..game.camera import Camera
from ..game.loader import GameLoader
from ..game.prefabs.yukkuri import create_yukkuri
from ..game.services import EconomyService, GameService, TimeService
from ..game.settings_service import SettingsService
from ..game.systems.physics import PhysicsSystem
from .managers.game_session import GameSessionManager
from .managers.input_handler import GameplayInputHandler
from .managers.renderer import GameplayRenderer

if TYPE_CHECKING:
    from ..game.systems.rendering.system import RenderingSystem
    from ..game.systems.day_night import DayNightSystem
    from ..game.ui.hud import HUD


class GameplayScene(Scene):
    """
    The main gameplay scene.

    Manages the game world, systems, and UI.

    Attributes:
        is_setup (bool): Whether the scene has been initialized.
        ui_manager (pygame_gui.UIManager): The UI manager for this scene.
        dt (float): The delta time for the current frame.
        game_config (Any): The loaded game configuration.
        camera (Camera): The game camera.
        audio (AudioManager): The audio manager.
        physics_system (PhysicsSystem): The physics system.
        event_manager (EventManager): The event manager.
        event_bus (Any): The event bus.
        input_manager (InputManager): The input manager.
        loader (GameLoader): The game loader.
        economy_service (EconomyService): The economy service.
        time_service (TimeService): The time service.
        settings_service (SettingsService): The settings service.
        game_service (GameService): The game service.
        save_manager (SaveManager): The unified save manager.
        input_system (Any): The input system.
        
        session_manager (GameSessionManager): Handles pause, speed, save/load logic.
        input_handler (GameplayInputHandler): Handles pygame inputs.
        renderer_manager (GameplayRenderer): Manages rendering subsystems.
    """

    INJECTIONS: ClassVar[dict[str, type]] = {"money": int, "time": float}

    def __init__(self, application: Application) -> None:
        """
        Initializes the GameplayScene.

        Args:
            application (Application): The main application instance.
        """
        super().__init__(application)
        self.is_setup = False
        
        # Compute absolute path for theme file (relative to project root)
        _theme_path = (
            Path(__file__).parent.parent.parent.parent / "data" / "ui_theme.json"
        )
        logger.debug(
            f"Gameplay theme path: {_theme_path}, exists: {_theme_path.exists()}"
        )
        if not _theme_path.exists():
            logger.warning(f"Gameplay theme not found. CWD: {os.getcwd()}")

        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height),
            theme_path=str(_theme_path) if _theme_path.exists() else None,
        )
        self.dt = 0.0

        # Runtime attributes mapped for legacy support
        self.render_system: "RenderingSystem | None" = None
        self.day_night_system: "DayNightSystem | None" = None
        self.hud: "HUD | None" = None
        self.hud_surface: pygame.Surface | None = None
        self.hud_texture: Any = None  # pl2d.Texture at runtime

        # Services and Systems
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
        self.input_system: Any
        
        self.session_manager: GameSessionManager
        self.input_handler: GameplayInputHandler
        self.renderer_manager: GameplayRenderer

    def on_enter(self) -> None:
        """
        Called when the scene becomes active.
        """
        logger.info("Entered Gameplay Scene")
        self.ui_manager.set_window_resolution(
            (self.application.width, self.application.height)
        )

    def setup(self, context: SceneContext) -> None:
        """
        Sets up the game environment.

        Args:
            context (SceneContext): Context data passed from the previous scene.
        """
        self.game_config = load_config()

        self.camera = Camera(settings=self.game_config.world)
        self.audio = AudioManager()
        self.audio.load_from_config()

        self.physics_system = PhysicsSystem()
        self.event_manager = EventManager()
        self.event_bus = self.event_manager.bus
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.GAMEPLAY)

        # Initialize Loader
        self.loader = GameLoader(self.world, self.application, self.game_config)

        # Register services
        self.loader.register_services(
            context, self.audio, self.camera, self.physics_system, self.event_bus
        )

        # Cache service references for local usage
        self.economy_service = self.world.services.get(EconomyService)
        self.time_service = self.world.services.get(TimeService)
        self.settings_service = self.world.services.get(SettingsService)

        self._apply_initial_settings()

        # Factories
        self.loader.register_factories_and_managers()
        self.game_service = self.world.services.get(GameService)

        # Save Manager
        self.save_manager = SaveManager(
            self.world, self.loader.collect_component_types()
        )
        self.world.services.register(self.save_manager, SaveManager)

        # Systems
        self.input_system = self.loader.register_systems(
            self.camera, self.physics_system, self.ui_manager
        )

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
        """Applies initial settings from the SettingsService."""
        audio_settings = self.settings_service.settings.audio
        self.audio.set_master_volume(audio_settings.master_volume)
        self.audio.set_bgm_volume(audio_settings.bgm_volume)
        self.audio.set_sfx_volume(audio_settings.sfx_volume)

    def on_exit(self) -> None:
        """
        Called when the scene is exited.

        Clears UI, shuts down services, and syncs global state.
        """
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()  # type: ignore[no-untyped-call]

        # Cleanup via managers
        if hasattr(self, "session_manager"):
            self.session_manager.cleanup()
            
        if hasattr(self, "renderer_manager"):
            self.renderer_manager.cleanup()

        # Sync back global state to Application/SceneManager
        if hasattr(self, "economy_service") and self.economy_service:
            self.application.scene_manager.set_global_data(
                "money", self.economy_service.money
            )
        if hasattr(self, "time_service") and self.time_service:
            self.application.scene_manager.set_global_data(
                "time", self.time_service.time_elapsed
            )

        # Shutdown Navigation Service
        nav_service = self.world.services.try_get(NavigationService)
        if nav_service:
            nav_service.shutdown()
        else:
            logger.warning("NavigationService NOT found in on_exit.")

        # Clear local audio resources
        if hasattr(self, "audio") and self.audio:
            self.audio.clear()

        # Cleanup Event Bus
        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.clear()

    def update(self, dt: float) -> None:
        """
        Updates the scene logic.

        Args:
            dt (float): Delta time in seconds.
        """
        self.dt = dt
        self.ui_manager.update(dt)

        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        # Calculate simulation delta time
        if not self.session_manager.paused:
            sim_dt = dt * self.session_manager.time_scale
            self.event_manager.process_phase(GamePhase.UPDATE)
        else:
            sim_dt = 0.0

        # Run world update
        self.world.update(sim_dt)

        # Camera should always update with real dt so panning/zoom works while paused
        self.camera.update(dt)

        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        self.renderer_manager.update(dt)

    def render(self, alpha: float) -> None:
        """
        Renders the scene.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        self.renderer_manager.render(alpha)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handles input events via the GameplayInputHandler.

        Args:
            event (pygame.event.Event): The Pygame event.
        """
        self.input_handler.handle_event(event)

    def take_screenshot(self) -> None:
        """Takes a screenshot and saves it to the screenshots directory."""
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = (
            f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        if self.application.screen:
            pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def init_render_system_headless(self) -> None:
        """
        Initializes the render system in headless mode for screenshots/verification.
        """
        if (
            not hasattr(self.renderer_manager, "render_system") or self.renderer_manager.render_system is None
        ) and self.application.screen:
            from ..game.systems.rendering.system import RenderingSystem
            render_system = RenderingSystem(
                self.application.screen,
                self.world,
                lights_engine=getattr(self.application, "lights_engine", None),
            )
            self.world.services.register(render_system, RenderingSystem)
            self.render_system = render_system
            self.renderer_manager.render_system = render_system
