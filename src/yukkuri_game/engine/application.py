"""
Application Module.
"""
import pygame
import pygame_gui
import os
from loguru import logger
from .resource_manager import ResourceManager
from .scene_manager import SceneManager

class Application:
    """
    Main Application class responsible for the main loop, window management, and scene management.
    """
    def __init__(self, width: int = 1280, height: int = 720, title: str = "Yukkuri Raising Game", headless: bool = False):
        self.width = width
        self.height = height
        self.headless = headless

        if self.headless:
            # Set dummy driver for headless mode
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()

        if self.headless:
             self.screen = pygame.display.set_mode((width, height))
        else:
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()
        self.running = True

        self.resources = ResourceManager()
        self.resources.load_all_data()

        self.scene_manager = SceneManager()

        # Global UI Manager (for overlays or shared UI resources)
        self.ui_manager = pygame_gui.UIManager((width, height))

        self.fixed_dt = 1.0 / 60.0
        self.accumulator = 0.0

    def run(self) -> None:
        """Starts the main application loop."""
        logger.info("Application Started")
        current_time = pygame.time.get_ticks() / 1000.0

        while self.running:
            new_time = pygame.time.get_ticks() / 1000.0
            frame_time = new_time - current_time
            current_time = new_time

            if frame_time > 0.25: frame_time = 0.25
            self.accumulator += frame_time

            # Input processing should happen every frame
            self.handle_events()

            while self.accumulator >= self.fixed_dt:
                self.update(self.fixed_dt)
                self.accumulator -= self.fixed_dt

            if not self.headless:
                self.render()
                self.clock.tick(60)
            else:
                self.clock.tick(60)

        pygame.quit()
        logger.info("Application Ended")

    def handle_events(self) -> None:
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            self.ui_manager.process_events(event)
            self.scene_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """
        Update application logic.

        Args:
            dt (float): Delta time in seconds.
        """
        self.ui_manager.update(dt)
        self.scene_manager.update(dt)

    def render(self) -> None:
        """Render the application."""
        self.screen.fill((0, 0, 0))
        self.scene_manager.render()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def quit(self) -> None:
        """Stops the application."""
        self.running = False
