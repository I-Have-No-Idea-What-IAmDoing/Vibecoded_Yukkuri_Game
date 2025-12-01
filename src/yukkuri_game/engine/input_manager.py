"""
Input Manager Module.
"""
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import Enum, auto, IntEnum
import pygame

class InputContext(IntEnum):
    # Higher value = Higher Priority
    GAMEPLAY = 1
    MENU = 10

class InputManager:
    """
    Manages input state and contexts with priority-based consumption.
    """
    def __init__(self):
        self._active_contexts: Set[InputContext] = {InputContext.MENU}
        self._keys_pressed: Set[int] = set()
        self._keys_down: Set[int] = set()
        self._keys_up: Set[int] = set()

        self._mouse_buttons: Set[int] = set()
        self._mouse_buttons_down: Set[int] = set()
        self._mouse_buttons_up: Set[int] = set()
        self._mouse_pos: Tuple[int, int] = (0, 0)
        self._mouse_wheel: float = 0.0

        # Mappings: Context -> Action -> Key
        self._key_mappings: Dict[InputContext, Dict[str, int]] = {
            InputContext.GAMEPLAY: {
                "up": pygame.K_UP,
                "down": pygame.K_DOWN,
                "left": pygame.K_LEFT,
                "right": pygame.K_RIGHT,
                "pause": pygame.K_ESCAPE,
                "interact": pygame.K_z,
                "debug_toggle": pygame.K_F3,
                "screenshot": pygame.K_F12,
                "quicksave": pygame.K_F5,
                "quickload": pygame.K_F9
            },
            InputContext.MENU: {
                "confirm": pygame.K_RETURN,
                "cancel": pygame.K_ESCAPE,
                "up": pygame.K_UP,
                "down": pygame.K_DOWN
            }
        }

        # Mappings: Context -> Action -> Mouse Button ID
        # 1=Left, 2=Middle, 3=Right
        self._mouse_mappings: Dict[InputContext, Dict[str, int]] = {
            InputContext.GAMEPLAY: {
                "select": 1,
                "place": 1,
                "clean": 1,
                "cancel_action": 3,
                "pan": 2
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
            self._mouse_buttons_down.add(event.button)
            # Handle wheel buttons if they come as buttons
            if event.button == 4: self._mouse_wheel = 1.0
            elif event.button == 5: self._mouse_wheel = -1.0
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_buttons.discard(event.button)
            self._mouse_buttons_up.add(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
        elif event.type == pygame.MOUSEWHEEL:
             self._mouse_wheel = event.y

    def update(self):
        """Clear frame-transient state."""
        self._keys_down.clear()
        self._keys_up.clear()
        self._mouse_buttons_down.clear()
        self._mouse_buttons_up.clear()
        self._mouse_wheel = 0.0

    def _is_consumed(self, key_or_btn: int, current_context: InputContext, is_mouse: bool = False) -> bool:
        """
        Check if a key/button is consumed by a higher priority context.
        """
        for context in self._active_contexts:
            if context.value > current_context.value:
                if is_mouse:
                    if context in self._mouse_mappings and key_or_btn in self._mouse_mappings[context].values():
                        return True
                else:
                    if context in self._key_mappings and key_or_btn in self._key_mappings[context].values():
                        return True
        return False

    def _check_action_in_collection(self, action: str, key_collection: Set[int], mouse_collection: Set[int]) -> bool:
        """
        Helper to check if an action is triggered within the active contexts, respecting priority.
        """
        # Sort contexts high to low.
        # If a higher context consumes the input, lower contexts are blocked.
        sorted_contexts = sorted(self._active_contexts, key=lambda c: c.value, reverse=True)

        for context in sorted_contexts:
            # Check Keys
            if context in self._key_mappings:
                key = self._key_mappings[context].get(action)
                if key and key in key_collection:
                    if not self._is_consumed(key, context, is_mouse=False):
                        return True

            # Check Mouse
            if context in self._mouse_mappings:
                btn = self._mouse_mappings[context].get(action)
                if btn and btn in mouse_collection:
                    if not self._is_consumed(btn, context, is_mouse=True):
                        return True

        return False

    def is_action_pressed(self, action: str) -> bool:
        """Check if an action is active (key/button held down)."""
        return self._check_action_in_collection(
            action,
            self._keys_pressed,
            self._mouse_buttons
        )

    def is_action_just_pressed(self, action: str) -> bool:
        """Check if an action was just pressed this frame."""
        return self._check_action_in_collection(
            action,
            self._keys_down,
            self._mouse_buttons_down
        )

    def is_action_just_released(self, action: str) -> bool:
        """Check if an action was just released this frame."""
        return self._check_action_in_collection(
            action,
            self._keys_up,
            self._mouse_buttons_up
        )

    def get_mouse_position(self) -> Tuple[int, int]:
        """Returns the current mouse position."""
        return self._mouse_pos

    def get_mouse_wheel(self) -> float:
        """Returns the mouse wheel delta."""
        return self._mouse_wheel
