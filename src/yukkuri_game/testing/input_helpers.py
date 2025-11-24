"""
Input injection helpers for testing.
"""
import pygame
from typing import Callable, Any

class InputHelper:
    """Base class for input helpers."""
    def __call__(self):
        raise NotImplementedError

class Click(InputHelper):
    """
    Simulates a mouse click (button down then up).
    """
    def __init__(self, x: int, y: int, button: int = 1):
        self.x = x
        self.y = y
        self.button = button

    def __call__(self):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (self.x, self.y), "button": self.button}))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (self.x, self.y), "button": self.button}))

class KeyPress(InputHelper):
    """
    Simulates a key press (key down then up).
    """
    def __init__(self, key: int):
        self.key = key

    def __call__(self):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": self.key}))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": self.key}))

# Backwards compatibility wrappers
def post_mouse_click(x: int, y: int, button: int = 1) -> Callable[[], None]:
    return Click(x, y, button)

def post_key_press(key: int) -> Callable[[], None]:
    return KeyPress(key)
