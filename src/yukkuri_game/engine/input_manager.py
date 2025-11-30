"""
Input Manager Module.
"""
from typing import Dict, List, Optional, Set
from enum import Enum, auto
import pygame

class InputContext(Enum):
    GAMEPLAY = auto()
    MENU = auto()

class InputManager:
    """
    Manages input state and contexts.
    """
    def __init__(self):
        self._active_contexts: Set[InputContext] = {InputContext.MENU} # Default to MENU? Or empty?
        self._keys_pressed: Set[int] = set()
        self._keys_down: Set[int] = set()
        self._keys_up: Set[int] = set()
        self._mouse_buttons: Set[int] = set()
        self._mouse_pos: tuple[int, int] = (0, 0)

        # Mappings: Context -> Action -> Key/Button
        # Ideally this would be configurable.
        self._mappings: Dict[InputContext, Dict[str, int]] = {
            InputContext.GAMEPLAY: {
                "up": pygame.K_UP,
                "down": pygame.K_DOWN,
                "left": pygame.K_LEFT,
                "right": pygame.K_RIGHT,
                "pause": pygame.K_ESCAPE,
                "interact": pygame.K_z
            },
            InputContext.MENU: {
                "confirm": pygame.K_RETURN,
                "cancel": pygame.K_ESCAPE,
                "up": pygame.K_UP,
                "down": pygame.K_DOWN
            }
        }

    def set_context(self, context: InputContext, active: bool = True):
        """Enable or disable an input context."""
        if active:
            self._active_contexts.add(context)
        else:
            self._active_contexts.discard(context)

    def switch_context(self, context: InputContext):
        """Switch to a single active context."""
        self._active_contexts.clear()
        self._active_contexts.add(context)

    def process_event(self, event: pygame.event.Event):
        """Process pygame input events."""
        if event.type == pygame.KEYDOWN:
            self._keys_pressed.add(event.key)
            self._keys_down.add(event.key)
        elif event.type == pygame.KEYUP:
            self._keys_pressed.discard(event.key)
            self._keys_up.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_buttons.add(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_buttons.discard(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos

    def update(self):
        """Clear frame-transient state."""
        self._keys_down.clear()
        self._keys_up.clear()

    def is_action_pressed(self, action: str) -> bool:
        """Check if an action is active (key held down) in any active context."""
        for context in self._active_contexts:
            mapping = self._mappings.get(context, {})
            key = mapping.get(action)
            if key and key in self._keys_pressed:
                return True
        return False

    def is_action_just_pressed(self, action: str) -> bool:
        """Check if an action was just pressed this frame."""
        for context in self._active_contexts:
            mapping = self._mappings.get(context, {})
            key = mapping.get(action)
            if key and key in self._keys_down:
                return True
        return False
