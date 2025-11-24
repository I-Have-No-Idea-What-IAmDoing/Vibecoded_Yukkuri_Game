"""
Input injection helpers for testing.
"""
import pygame

def post_mouse_click(x: int, y: int, button: int = 1):
    """
    Posts a mouse button down and up event at the specified coordinates.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": button}))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x, y), "button": button}))
    return _inject

def post_key_press(key: int):
    """
    Posts a key down and key up event.
    """
    def _inject():
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": key}))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": key}))
    return _inject
