"""
Application Module.
"""

import pygame
import pygame_gui
import os
from typing import Any
from loguru import logger
from .resource_manager import ResourceManager
from .scene_manager import SceneManager
from .input_manager import InputManager
from .event_manager import EventManager, GamePhase
from .audio import AudioManager
import gc


class Application:
    """
    Main Application class responsible for the main loop, window management, and scene management.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Yukkuri Raising Game",
        headless: bool = False,
        render_scale: float = 1.0,
    ):
        """
        Initializes the Application.

        Args:
            width (int): The width of the application window in pixels. Defaults to 1280.
            height (int): The height of the application window in pixels. Defaults to 720.
            title (str): The title of the application window. Defaults to "Yukkuri Raising Game".
            headless (bool): Whether to run in headless mode (no graphics). Defaults to False.
            render_scale (float): Scale factor for rendering resolution relative to screen resolution. Defaults to 1.0.
        """
        self.width = width
        self.height = height
        self.title = title
        self.headless = headless
        self.render_scale = render_scale

        self.lights_engine: Any = None
        self.screen: pygame.Surface | None = None

        if self.headless:
            # Set dummy driver for headless mode
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
            width (int): Window width.
            height (int): Window height.
            fullscreen (bool): Whether to use fullscreen mode.
        """
        if self.headless:
            # Initialize the dummy surface first
            self.screen = pygame.display.set_mode((width, height))

            # In headless mode, we force software rendering to avoid EGL/OpenGL dependency issues in sandboxes/CI.
            # We explicitly set lights_engine to None so that RenderSystem falls back to PygameBackend (software).
            self.lights_engine = None
            logger.info("Headless mode: forced software rendering (PygameBackend).")

        else:
            try:
                # Calculate native resolution based on render scale

                # Initialize LightingEngine instead of standard display
                # We match native_res to screen_res for now to keep pixel density same as before
                # unless we want pixel art style (which yukkuri usually is).
                # If we want scaling, we can adjust native_res.

                # CRITICAL FIX: Force Disable OpenGL/LightingEngine to use Software Renderer (PygameBackend)
                # The OpenGL backend is broken and overwrites the screen with black.
                # self.lights_engine = LightingEngine(
                #     screen_res=(width, height),
                #     native_res=(native_w, native_h),
                #     lightmap_res=(lightmap_w, lightmap_h),
                #     fullscreen=fullscreen,
                # )
                self.lights_engine = None

                # Initialize standard display for Software Renderer
                flags = pygame.FULLSCREEN if fullscreen else 0
                self.screen = pygame.display.set_mode((width, height), flags)
                pygame.display.set_caption(self.title)

                # Store native resolution for aspect correction in NewRenderSystem
                # self.lights_engine._native_res = (native_w, native_h)
                # LightingEngine creates the window, so we can get the surface if needed,
                # but usually we render via engine.
                # Some parts of code expect self.screen to be the display surface.
                # LightingEngine manages display, but we can access it via pygame.display.get_surface()
                # self.screen = pygame.display.get_surface()
                # pygame.display.set_caption(self.title)
                # self.lights_engine.set_ambient(128, 128, 128, 255)
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
            width (int): New width.
            height (int): New height.
            fullscreen (bool): Fullscreen flag.
            render_scale (float | None): New render scale. If None, keeps current scale.
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
        Starts the main application loop.

        This method enters an infinite loop until the application is signaled to quit.
        It handles timing, event processing, updates, and rendering.

        Returns:
            None
        """
        logger.info("Application Started")
        current_time = pygame.time.get_ticks() / 1000.0

        while self.running:
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

        self.quit()

    def process_events(self) -> None:
        """
        Process input events from the system queue.

        Delegates events to InputManager, UIManager, and SceneManager.

        Returns:
            None
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.input_manager.process_event(event)
            self.ui_manager.process_events(event)
            self.scene_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """
        Update application logic.

        Args:
            dt (float): Delta time in seconds.

        Returns:
            None
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
        Render the application to the screen.

        Clears the screen, renders the current scene, draws the UI, and flips the display buffer.

        Returns:
            None
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
            # Dynamic dispatch requires Any or explicit cast
            from typing import Any
            from typing import cast

            scene = cast(Any, self.scene_manager.current_scene)
            scene.init_render_system_headless()

    def quit(self) -> None:
        """
        Stops the application.

        Sets the running flag to False and quits pygame.

        Returns:
            None
        """
        logger.info("Application Ended")
        # Explicit cleanup order
        if self.scene_manager:
            # Pop all scenes to trigger their on_exit and cleanup
            while self.scene_manager.current_scene:
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
