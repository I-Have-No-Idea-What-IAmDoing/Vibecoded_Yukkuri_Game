import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UITextBox
from typing import Optional

class NotificationLog:
    """
    A UI component that displays a scrollable log of game notifications.
    """

    def __init__(self, manager: pygame_gui.UIManager, screen_width: int, screen_height: int):
        """
        Initializes the NotificationLog.

        Args:
            manager (pygame_gui.UIManager): The UI manager.
            screen_width (int): Screen width.
            screen_height (int): Screen height.
        """
        self.manager = manager
        self.width = 300
        self.height = 200
        self.x = 10
        self.y = screen_height - self.height - 10

        # Since it's part of the HUD, we might not want a window with a title bar,
        # or maybe we do. Let's use a panel or a transparent window.
        # For now, a simple text box might suffice if we want it always visible.
        # Or a window if we want it toggleable/movable.
        # Let's make it a text box directly on the HUD for simplicity first.

        self.log_text_box = UITextBox(
            html_text="",
            relative_rect=pygame.Rect(self.x, self.y, self.width, self.height),
            manager=self.manager,
            # container=self.manager.get_root_container()
        )

        self.messages = []
        self.max_messages = 50

    def add_message(self, message: str):
        """
        Adds a message to the log.

        Args:
            message (str): The message to add.
        """
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        self._update_display()

    def _update_display(self):
        """
        Updates the text box content.
        """
        text = "<br>".join(self.messages)
        self.log_text_box.set_text(text)

        # Auto-scroll to bottom
        # pygame_gui's UITextBox handles scrolling if text is too long.
        # To auto-scroll, we might need to access the scroll bar.
        if self.log_text_box.scroll_bar:
            self.log_text_box.scroll_bar.scroll_position = self.log_text_box.scroll_bar.bottom_limit
            self.log_text_box.scroll_bar.redraw() # Force redraw
