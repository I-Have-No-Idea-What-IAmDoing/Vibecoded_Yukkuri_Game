"""
Custom UI Elements for Yukkuri Game.
"""

from typing import Any
from pygame_gui.elements import UIScrollingContainer
from pygame_gui.elements import UITextBox


class NonBlockingTextBox(UITextBox):
    """
    A UITextBox that does not block mouse input (hover).
    Used for tooltips and floating text that should not interfere with gameplay interaction.
    """

    def hover_point(self, hover_x: float, hover_y: float) -> bool:
        """
        Override hover_point to always return False.
        This prevents the UI Manager from considering this element as 'hovered',
        allowing input to pass through to the game world.

        Args:
            hover_x (float): The x-coordinate of the mouse hover.
            hover_y (float): The y-coordinate of the mouse hover.

        Returns:
            bool: Always returns False.
            """
        return False


class SafeUIScrollingContainer(UIScrollingContainer):
    """
    Subclass of UIScrollingContainer to prevent hidden tab init errors.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.vert_scroll_bar = None
        self.horiz_scroll_bar = None
        self._root_container = None
        self._view_container: Any = None
        super().__init__(*args, **kwargs)
