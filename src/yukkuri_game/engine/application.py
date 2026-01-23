"""
Application Module.
"""

import gc
import os
import pygame
import pygame_gui
from typing import Any
from loguru import logger
from .resource_manager import ResourceManager
from .scene_manager import SceneManager
from .input_manager import InputManager
from .event_manager import EventManager, GamePhase
from .audio import AudioManager


class Application:
    """
    Main Application class responsible for the game loop, window, and scene management.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Yukkuri Raising Game",
        headless: bool = False,
        render_scale: float = 1.0,
        deterministic: bool = False,
    ):
        """
        Initializes the application.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            title: Application window title.
            headless: If True, runs without graphics (for tests/server).
            render_scale: Rendering resolution scale relative to window size.
            deterministic: If True, enforcing deterministic behavior (e.g., synchronous NavService, seeded RNG).
        """
        self.width = width
        self.height = height
        self.title = title
        self.headless = headless
        self.render_scale = render_scale
        self.deterministic = deterministic

        if self.deterministic:
            from .rng import seed

            seed(42)
            logger.info("Deterministic mode enabled. RNG seeded with 42.")

        self.lights_engine: Any = None
        self.screen: pygame.Surface | None = None

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()

        self._initialize_display(width, height, fullscreen=False)

        self.clock = pygame.time.Clock()
        self.running = True

        self.resources = ResourceManager()
        self.resources.load_all_data()

        self.input_manager = InputManager()
        self.event_manager = EventManager()

        self.scene_manager = SceneManager()

        # Global UI Manager (for overlays or shared UI resources)
        self.ui_manager = pygame_gui.UIManager((width, height))

        # Surface for UI rendering
        self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        self.fixed_dt = 1.0 / 60.0
        self.accumulator = 0.0

        logger.info("Application initialized.")

    def _initialize_display(
        self, width: int, height: int, fullscreen: bool = False
    ) -> None:
        """
        Initializes the display and lighting engine.

        Args:
            width: Width of the display.
            height: Height of the display.
            fullscreen: Whether to enable fullscreen mode.
        """
        if self.headless:
            self.screen = pygame.display.set_mode((width, height))
            self.lights_engine = None  # Force software rendering in headless.
            logger.info("Headless mode: forced software rendering (PygameBackend).")

        else:
            try:
                # OpenGL backend disabled - using PygameBackend (software renderer).
                self.lights_engine = None

                flags = pygame.FULLSCREEN if fullscreen else 0
                self.screen = pygame.display.set_mode((width, height), flags)
                pygame.display.set_caption(self.title)

            except Exception as e:
                logger.error(
                    f"Failed to initialize LightingEngine: {e}. Falling back to standard Pygame display."
                )
                self.lights_engine = None
                flags = pygame.FULLSCREEN if fullscreen else 0
                self.screen = pygame.display.set_mode((width, height), flags)
                pygame.display.set_caption(self.title)

    def change_resolution(
        self,
        width: int,
        height: int,
        fullscreen: bool,
        render_scale: float | None = None,
    ) -> None:
        """
        Changes the resolution and fullscreen state.

        Args:
            width: New width.
            height: New height.
            fullscreen: New fullscreen state.
            render_scale: Optional new render scale.
        """
        if render_scale is not None:
            self.render_scale = render_scale

        logger.info(
            f"Changing resolution to {width}x{height}, Fullscreen: {fullscreen}, Render Scale: {self.render_scale}"
        )
        self.width = width
        self.height = height

        # Re-initialize display (and LightingEngine)
        self._initialize_display(width, height, fullscreen)

        # Update UI Surface and Manager
        self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.ui_manager.set_window_resolution((width, height))

    def run(self) -> None:
        """
        Starts the main game loop.
        """
        logger.info("Application Started")
        current_time = pygame.time.get_ticks() / 1000.0

        while self.running:
            try:
                new_time = pygame.time.get_ticks() / 1000.0
                frame_time = new_time - current_time
                current_time = new_time

                if frame_time > 0.25:
                    frame_time = 0.25
                self.accumulator += frame_time

                # Input processing should happen every frame
                self.process_events()

                while self.accumulator >= self.fixed_dt:
                    self.update(self.fixed_dt)
                    self.accumulator -= self.fixed_dt

                if not self.headless:
                    self.render()
                    self.clock.tick(60)
                else:
                    self.clock.tick(60)
            except Exception as e:
                logger.critical(f"Unhandled exception in game loop: {e}")
                import traceback

                logger.critical(traceback.format_exc())
                self.running = False

        self.quit()

    def process_events(self) -> None:
        """
        Process input events from the system queue.

        Delegates to InputManager, UIManager, and SceneManager.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.input_manager.process_event(event)
            self.ui_manager.process_events(event)
            self.scene_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """
        Update application logic and systems.

        Args:
            dt: Delta time in seconds.
        """
        # 1. Pre-Update Phase (Prepare systems)
        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        # 2. Main Game Logic
        self.ui_manager.update(dt)
        self.scene_manager.update(dt)

        # 3. Update Phase (Systems responding to frame logic)
        self.event_manager.process_phase(GamePhase.UPDATE)

        # 4. Post-Update (Cleanup)
        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        # 5. Update Input State (Clear transient state)
        self.input_manager.update()

    def render(self) -> None:
        """
        Render the application frame.
        """
        # Ensure screen is available (mypy check)
        if self.screen is None:
            return

        self.screen.fill((0, 0, 0))
        self.scene_manager.render()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def init_render_system_headless(self) -> None:
        """
        Initializes the render system for the current scene if in headless mode.

        This allows taking screenshots or verifying rendering logic without a window.
        """
        if self.scene_manager.current_scene and hasattr(
            self.scene_manager.current_scene, "init_render_system_headless"
        ):
            from typing import Any, cast

            scene = cast(Any, self.scene_manager.current_scene)
            scene.init_render_system_headless()

    def quit(self) -> None:
        """
        Stops the application and cleans up resources.
        """
        logger.info("Application Ended")
        if self.scene_manager:
            while self.scene_manager.current_scene:  # Pop all scenes for cleanup.
                self.scene_manager.pop()

        if hasattr(self, "audio") and isinstance(self.audio, AudioManager):
            self.audio.clear()

        if self.resources:
            self.resources.clear()

        if self.running:
            self.running = False
        pygame.quit()

        # Final GC
        gc.collect()
