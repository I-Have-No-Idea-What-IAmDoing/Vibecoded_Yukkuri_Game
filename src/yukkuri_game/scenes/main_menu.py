"""
Main Menu Scene.
"""

import pygame
import pygame_gui
import pygame_light2d as pl2d
from loguru import logger
from ..engine.scene import Scene
from ..engine.application import Application
from ..engine.input_manager import InputManager, InputContext


class MainMenuScene(Scene):
    """
    The Main Menu Scene.
    """

    def __init__(self, application: Application):
        super().__init__(application)
        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height)
        )
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.MENU)

        # Surface for UI rendering when using lights engine
        self.ui_surface = pygame.Surface(
            (self.application.width, self.application.height), pygame.SRCALPHA
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Sets up the main menu UI."""
        center_x = self.application.width / 2
        center_y = self.application.height / 2

        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((center_x - 100, center_y - 50), (200, 50)),
            text="Start Game",
            manager=self.ui_manager,
        )

        self.quit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((center_x - 100, center_y + 20), (200, 50)),
            text="Quit",
            manager=self.ui_manager,
        )

    def on_enter(self) -> None:
        """
        Called when the scene is entered.
        Sets up the UI resolution.
        """
        logger.info("Entered Main Menu Scene")
        # Ensure we have the right resolution for UI
        self.ui_manager.set_window_resolution(
            (self.application.width, self.application.height)
        )

    def on_exit(self) -> None:
        """
        Called when the scene is exited.
        Clears the UI manager.
        """
        logger.info("Exited Main Menu Scene")
        self.ui_manager.clear_and_reset()

    def update(self, dt: float) -> None:
        """
        Updates the scene.

        Args:
            dt (float): Delta time.
        """
        super().update(dt)
        self.ui_manager.update(dt)

    def render(self) -> None:
        """
        Renders the scene.
        """
        if self.application.lights_engine:
            # Clear the UI surface
            self.ui_surface.fill((0, 0, 0, 0))

            # Draw UI to the surface
            self.ui_manager.draw_ui(self.ui_surface)

            # Convert surface to texture and render via lights engine
            tex = self.application.lights_engine.surface_to_texture(self.ui_surface)
            self.application.lights_engine.render_texture(
                tex,
                pl2d.FOREGROUND,
                pygame.Rect(0, 0, self.application.width, self.application.height),
                pygame.Rect(0, 0, self.application.width, self.application.height)
            )
            tex.release()
        else:
            self.ui_manager.draw_ui(self.application.screen)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handles input events.

        Args:
            event (pygame.event.Event): The Pygame event.
        """
        self.ui_manager.process_events(event)
        # InputManager processing is handled by Application

        if self.input_manager.is_action_just_pressed("cancel"):
            self.application.quit()

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.start_button:
                from .gameplay import GameplayScene

                self.application.scene_manager.replace(GameplayScene(self.application))
            elif event.ui_element == self.quit_button:
                self.application.quit()
