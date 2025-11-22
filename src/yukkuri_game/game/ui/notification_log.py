import pygame
import pygame_gui
from pygame_gui.elements import UITextBox, UIPanel

class NotificationLog:
    """
    A UI component that displays a scrolling log of notifications.
    """

    def __init__(self, manager: pygame_gui.UIManager, container: UIPanel, rect: pygame.Rect):
        """
        Initializes the NotificationLog.

        Args:
            manager (pygame_gui.UIManager): The UI manager.
            container (UIPanel): The parent container.
            rect (pygame.Rect): The relative rectangle for the log.
        """
        self.manager = manager
        self.container = container
        self.rect = rect
        self.messages = []
        self.max_messages = 20

        self.text_box = UITextBox(
            html_text="",
            relative_rect=rect,
            manager=manager,
            container=container,
            object_id="#notification_log"
        )

    def add_message(self, message: str, color: str = "#FFFFFF") -> None:
        """
        Adds a message to the log.

        Args:
            message (str): The message text.
            color (str): The hex color code for the message.
        """
        formatted_msg = f"<font color='{color}'>{message}</font>"
        self.messages.append(formatted_msg)

        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        self.update_display()

    def update_display(self) -> None:
        """
        Updates the text box content.
        """
        # Join messages with line breaks
        full_text = "<br>".join(self.messages)
        self.text_box.set_text(full_text)

        # Auto-scroll to bottom (by setting scroll bar to 1.0)
        if self.text_box.scroll_bar:
            self.text_box.scroll_bar.scroll_position = 1.0
            self.text_box.scroll_bar.scroll_wheel_down = False # Trigger update
