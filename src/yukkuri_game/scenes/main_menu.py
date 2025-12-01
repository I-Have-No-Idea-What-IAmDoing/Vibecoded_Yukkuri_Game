"""
Main Menu Scene.
"""
import pygame
import pygame_gui
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
        self.ui_manager = pygame_gui.UIManager((self.application.width, self.application.height))
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.MENU)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Sets up the main menu UI."""
        center_x = self.application.width / 2
        center_y = self.application.height / 2

        self.start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((center_x - 100, center_y - 50), (200, 50)),
            text='Start Game',
            manager=self.ui_manager
        )

        self.quit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((center_x - 100, center_y + 20), (200, 50)),
            text='Quit',
            manager=self.ui_manager
        )

    def on_enter(self) -> None:
        logger.info("Entered Main Menu Scene")
        # Ensure we have the right resolution for UI
        self.ui_manager.set_window_resolution((self.application.width, self.application.height))

    def on_exit(self) -> None:
        logger.info("Exited Main Menu Scene")
        self.ui_manager.clear_and_reset()

    def update(self, dt: float) -> None:
        super().update(dt)
        self.ui_manager.update(dt)

    def render(self) -> None:
        self.ui_manager.draw_ui(self.application.screen)

    def handle_event(self, event: pygame.event.Event) -> None:
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
