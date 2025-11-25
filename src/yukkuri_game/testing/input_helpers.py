"""
Input injection helpers for testing.
"""
import pygame
from .predicates import InjectInput

def post_mouse_click(x: int, y: int, button: int = 1):
    """
    Posts a mouse button down and up event at the specified coordinates.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": button}))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x, y), "button": button}))
    return InjectInput(_inject)

def post_click(x: int, y: int, button: int = 1):
    """Alias for post_mouse_click."""
    return post_mouse_click(x, y, button)

def post_key_press(key: int):
    """
    Posts a key down and key up event.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": key}))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": key}))
    return InjectInput(_inject)

def post_key_down(key: int):
    """
    Posts a key down event.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": key}))
    return InjectInput(_inject)

def post_key_up(key: int):
    """
    Posts a key up event.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": key}))
    return InjectInput(_inject)

# Aliases for convenience in scenarios
Click = post_click
KeyPress = post_key_press
