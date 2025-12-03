"""
Custom UI Elements for Yukkuri Game.
"""

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
        """
        return False
