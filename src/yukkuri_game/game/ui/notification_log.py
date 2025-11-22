import pygame
import pygame_gui
from pygame_gui.elements import UITextBox

class NotificationLog:
    """
    A UI element that displays a scrollable log of notifications.
    """
    def __init__(self, relative_rect: pygame.Rect, manager: pygame_gui.UIManager, container=None):
        self.manager = manager
        self.text_box = UITextBox(
            html_text="",
            relative_rect=relative_rect,
            manager=manager,
            container=container
        )
        self.messages = []
        self.max_messages = 50

    def add_message(self, message: str, color: tuple[int, int, int] = None):
        """
        Adds a message to the log.

        Args:
            message (str): The message text.
            color (tuple): The RGB color for the message.
        """
        # Format message
        formatted_msg = message
        if color:
            hex_color = "#{:02x}{:02x}{:02x}".format(*color)
            formatted_msg = f"<font color='{hex_color}'>{message}</font>"

        self.messages.append(formatted_msg)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        self._update_text()

    def _update_text(self):
        """Updates the text box content."""
        full_text = "<br>".join(self.messages)
        self.text_box.set_text(full_text)
        # Scroll to bottom (pygame_gui doesn't have a direct method for this easily without rebuilding,
        # but appending usually keeps scroll or we can try to scroll).
        # For now, simple text update.

        # Auto-scroll if possible.
        if self.text_box.scroll_bar:
            self.text_box.scroll_bar.scroll_position = self.text_box.scroll_bar.scrollable_height - self.text_box.scroll_bar.visible_percentage * self.text_box.scroll_bar.scrollable_height
            self.text_box.scroll_bar.start_percentage = 1.0 # Try to force scroll to bottom?
            # Note: pygame_gui 0.6.x handles this variously. Usually setting text might reset scroll unless appended.
            # We will leave it as is for now.
