"""
Main Menu Scene Module.

This module provides the `MainMenuScene`, which serves as the entry point for the
user interaction, allowing them to start the game or quit.
"""

import os
from pathlib import Path

import pygame
import pygame_gui
from loguru import logger

from ..engine.application import Application
from ..engine.input_manager import InputContext, InputManager
from ..engine.scene import Scene


class MainMenuScene(Scene):
    """
    The Main Menu Scene.

    Manages the initial menu screen with Start and Quit buttons.

    Attributes:
        ui_manager (pygame_gui.UIManager): The UI manager for the menu.
        input_manager (InputManager): The input manager service.
        ui_surface (pygame.Surface): Surface for UI rendering (used with lights engine).
        start_button (pygame_gui.elements.UIButton): The start button element.
        quit_button (pygame_gui.elements.UIButton): The quit button element.
    """

    def __init__(self, application: Application) -> None:
        """
        Initializes the MainMenuScene.

        Args:
            application (Application): The main application instance.
        """
        super().__init__(application)
        # Compute absolute path for theme file (relative to project root)
        _theme_path = (
            Path(__file__).parent.parent.parent.parent / "data" / "ui_theme.json"
        )
        logger.debug(
            f"MainMenu theme path: {_theme_path}, exists: {_theme_path.exists()}"
        )
        if not _theme_path.exists():
            logger.warning(f"MainMenu theme not found. CWD: {os.getcwd()}")

        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height),
            theme_path=str(_theme_path) if _theme_path.exists() else None,
        )
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.MENU)

        # Surface for UI rendering when using lights engine
        self.ui_surface = pygame.Surface(
            (self.application.width, self.application.height), pygame.SRCALPHA
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Sets up the main menu UI elements (Start, Quit buttons).
        """
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
            dt (float): Delta time in seconds.
        """
        super().update(dt)
        self.ui_manager.update(dt)

    def render(self, alpha: float) -> None:
        """
        Renders the scene.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        if self.application.screen:
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
