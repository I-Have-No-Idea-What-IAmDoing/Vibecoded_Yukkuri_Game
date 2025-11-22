import pygame
import pygame_gui
from pygame_gui.elements import UITextBox, UIPanel

class NotificationLog:
    """
    UI component that displays a scrolling log of notifications.
    """

    def __init__(self, manager: pygame_gui.UIManager, container: UIPanel, rect: pygame.Rect):
        """
        Initializes the NotificationLog.

        Args:
            manager: Pygame GUI manager.
            container: Parent container (UIPanel).
            rect: Relative rect within the container.
        """
        self.manager = manager

        # Use a UITextBox for the log.
        # We will append HTML text to it.
        self.log_box = UITextBox(
            html_text="",
            relative_rect=rect,
            manager=manager,
            container=container,
            object_id='#notification_log'
        )

        self.history = []
        self.max_lines = 50

    def add_message(self, message: str, color: tuple = None) -> None:
        """
        Adds a message to the log.

        Args:
            message (str): The text to add.
            color (tuple): RGB color tuple (optional).
        """
        # Format color to hex
        if color:
            hex_color = "#{:02x}{:02x}{:02x}".format(*color)
            formatted_msg = f"<font color='{hex_color}'>{message}</font>"
        else:
            formatted_msg = message

        self.history.append(formatted_msg)

        if len(self.history) > self.max_lines:
            self.history.pop(0)

        # Update text box
        full_text = "<br>".join(self.history)
        self.log_box.set_text(full_text)

        # Scroll to bottom (UITextBox doesn't have direct scroll_to_bottom,
        # but setting text usually keeps scroll if at bottom, or resets.
        # We might need to check how pygame_gui handles this.
        # Usually appending requires resetting the scroll bar.

        if self.log_box.scroll_bar:
            self.log_box.scroll_bar.scroll_position = self.log_box.scroll_bar.scrollable_height - self.log_box.scroll_bar.visible_percentage * self.log_box.scroll_bar.scrollable_height
            self.log_box.scroll_bar.scroll_position = min(self.log_box.scroll_bar.scroll_position, self.log_box.scroll_bar.bottom_limit)
            # This is a bit hacky, but let's see if default behavior is enough.
            # Often UITextBox auto-scrolls if the user hasn't scrolled up.
