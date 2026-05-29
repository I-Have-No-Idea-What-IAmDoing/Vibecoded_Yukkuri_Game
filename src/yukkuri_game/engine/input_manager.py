"""
Input Manager Module.
"""

from enum import IntEnum
from typing import Any

import pygame
from loguru import logger


class InputContext(IntEnum):
    """
    Enum representing input contexts with priority levels.
    """

    # Higher value = Higher Priority
    GAMEPLAY = 1
    MENU = 10


class InputManager:
    """
    Manages input state and contexts with priority-based consumption.

    Attributes:
        _active_contexts (set[InputContext]): The set of currently active input contexts.
        _keys_pressed (set[int]): Set of keys currently held down.
        _keys_down (set[int]): Set of keys pressed in the current frame.
        _keys_up (set[int]): Set of keys released in the current frame.
        _mouse_buttons (set[int]): Set of mouse buttons currently held down.
        _mouse_buttons_down (set[int]): Set of mouse buttons pressed in the current frame.
        _mouse_buttons_up (set[int]): Set of mouse buttons released in the current frame.
        _mouse_pos (tuple[int, int]): The current mouse position (x, y).
        _mouse_wheel (float): The mouse wheel delta.
        _key_mappings (dict[InputContext, dict[str, list[int]]]): Mapping of contexts to key actions.
        _mouse_mappings (dict[InputContext, dict[str, int]]): Mapping of contexts to mouse actions.
    """

    def __init__(self) -> None:
        """Initializes the InputManager."""
        self._active_contexts: set[InputContext] = {InputContext.MENU}
        self._keys_pressed: set[int] = set()
        self._keys_down: set[int] = set()
        self._keys_up: set[int] = set()

        self._mouse_buttons: set[int] = set()
        self._mouse_buttons_down: set[int] = set()
        self._mouse_buttons_up: set[int] = set()
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_rel: tuple[int, int] = (0, 0)
        self._mouse_wheel: float = 0.0

        # Mappings: Context -> Action -> List of Keys.
        self._key_mappings: dict[InputContext, dict[str, list[int]]] = {
            InputContext.GAMEPLAY: {
                "up": [pygame.K_UP, pygame.K_w],
                "down": [pygame.K_DOWN, pygame.K_s],
                "left": [pygame.K_LEFT, pygame.K_a],
                "right": [pygame.K_RIGHT, pygame.K_d],
                "pause": [pygame.K_ESCAPE],
                "toggle_pause": [pygame.K_SPACE, pygame.K_p],
                "interact": [pygame.K_z],
                "debug_toggle": [pygame.K_F3],
                "screenshot": [pygame.K_F12],
                "quicksave": [pygame.K_F5],
                "quickload": [pygame.K_F9],
                "time_speed_up": [pygame.K_EQUALS, pygame.K_PLUS],
                "time_speed_down": [pygame.K_MINUS],
                "shift": [pygame.K_LSHIFT, pygame.K_RSHIFT],
                "ctrl": [pygame.K_LCTRL, pygame.K_RCTRL],
                "alt": [pygame.K_LALT, pygame.K_RALT],
            },
            InputContext.MENU: {
                "confirm": [pygame.K_RETURN],
                "cancel": [pygame.K_ESCAPE],
                "up": [pygame.K_UP],
                "down": [pygame.K_DOWN],
            },
        }

        # Mappings: Context -> Action -> Mouse Button ID (1=Left, 2=Middle, 3=Right).
        self._mouse_mappings: dict[InputContext, dict[str, int]] = {
            InputContext.GAMEPLAY: {
                "select": 1,
                "place": 1,
                "clean": 1,
                "cancel_action": 3,
                "pan": 2,
            }
        }

    def load_key_mappings(self, config: dict[str, Any]) -> None:
        """
        Loads key mappings from a configuration dictionary.

        This method allows for runtime remapping of keys.

        Args:
            config (dict[str, Any]): Dictionary containing key mappings.
                Structure: { "GAMEPLAY": { "action": [key_code, ...] }, ... }

        Raises:
            ValueError: If the configuration is invalid.
        """
        try:
            # Deep update to avoid wiping unmentioned keys
            for context_name, actions in config.items():
                try:
                    context = InputContext[context_name.upper()]
                except KeyError:
                    logger.warning(f"Unknown input context: {context_name}")
                    continue

                if context not in self._key_mappings:
                    self._key_mappings[context] = {}

                for action, keys in actions.items():
                    if not isinstance(keys, list):
                        raise ValueError(f"Invalid mapping format for {action}: {keys}")
                    if not all(isinstance(key, int) for key in keys):
                        raise ValueError(f"Invalid key codes for {action}: {keys}")

                    self._key_mappings[context][action] = keys

        except Exception as e:
            logger.error(f"Failed to load key mappings: {e}")
            raise

    def set_context(self, context: InputContext, active: bool = True) -> None:
        """
        Enable or disable an input context.

        Args:
            context (InputContext): The context to modify.
            active (bool): True to enable the context, False to disable. Defaults to True.

        Returns:
            None
        """
        if active:
            self._active_contexts.add(context)
        else:
            self._active_contexts.discard(context)

    def switch_context(self, context: InputContext) -> None:
        """
        Switch to a single active context, disabling all others.

        Args:
            context (InputContext): The context to make active.

        Returns:
            None
        """
        self._active_contexts.clear()
        self._active_contexts.add(context)

    def process_event(self, event: pygame.event.Event) -> None:
        """
        Process pygame input events.

        Args:
            event (pygame.event.Event): The pygame event to process.

        Returns:
            None
        """
        if event.type == pygame.KEYDOWN:
            self._keys_pressed.add(event.key)
            self._keys_down.add(event.key)
        elif event.type == pygame.KEYUP:
            self._keys_pressed.discard(event.key)
            self._keys_up.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_buttons.add(event.button)
            self._mouse_buttons_down.add(event.button)
            # Handle wheel buttons if they come as buttons.
            if event.button == 4:
                self._mouse_wheel = 1.0
            elif event.button == 5:
                self._mouse_wheel = -1.0
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_buttons.discard(event.button)
            self._mouse_buttons_up.add(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
            rx, ry = self._mouse_rel
            ex, ey = getattr(event, "rel", (0, 0))
            self._mouse_rel = (rx + ex, ry + ey)
        elif event.type == pygame.MOUSEWHEEL:
            self._mouse_wheel = event.y

    def update(self) -> None:
        """
        Clear frame-transient state.
        Should be called at the beginning or end of each frame.

        Returns:
            None
        """
        self._keys_down.clear()
        self._keys_up.clear()
        self._mouse_buttons_down.clear()
        self._mouse_buttons_up.clear()
        self._mouse_wheel = 0.0
        self._mouse_rel = (0, 0)

    def _is_consumed_by_higher_priority(
        self, key_or_btn: int, current_context: InputContext, is_mouse: bool = False
    ) -> bool:
        """
        Check if a key/button is consumed by a higher priority context.

        The input system uses a strict priority hierarchy (STACK).
        If a higher priority context (e.g., MENU currently active) maps the same key,
        it "consumes" the event, preventing lower priority contexts (e.g., GAMEPLAY) from seeing it.

        Args:
            key_or_btn (int): The key code or mouse button ID.
            current_context (InputContext): The context checking for input.
            is_mouse (bool): True if checking a mouse button, False for keyboard key.

        Returns:
            bool: True if the input is consumed by a higher priority context, False otherwise.
        """
        sorted_contexts = sorted(
            self._active_contexts, key=lambda c: c.value, reverse=True
        )
        for context in sorted_contexts:
            if context.value <= current_context.value:
                continue

            if is_mouse:
                if (
                    context in self._mouse_mappings
                    and key_or_btn in self._mouse_mappings[context].values()
                ):
                    return True
            else:
                if context in self._key_mappings:
                    for keys_list in self._key_mappings[context].values():
                        if key_or_btn in keys_list:
                            return True
        return False

    def _action_triggered_in_collections(
        self, action: str, key_collection: set[int], mouse_collection: set[int]
    ) -> bool:
        """
        Helper to check if an action is triggered within the active contexts, respecting priority.

        Args:
            action (str): The name of the action to check.
            key_collection (set[int]): The set of keys to check (e.g., pressed, down).
            mouse_collection (set[int]): The set of mouse buttons to check.

        Returns:
            bool: True if the action is triggered, False otherwise.
        """
        # Iterate from highest priority to lowest; higher contexts consume input.
        sorted_contexts = sorted(
            self._active_contexts, key=lambda c: c.value, reverse=True
        )

        for context in sorted_contexts:
            # Check Keys (mappings are now lists)
            if context in self._key_mappings:
                keys_list = self._key_mappings[context].get(action)
                if keys_list:
                    for key in keys_list:
                        if key in key_collection:
                            if not self._is_consumed_by_higher_priority(
                                key, context, is_mouse=False
                            ):
                                return True

            # Check Mouse
            if context in self._mouse_mappings:
                btn = self._mouse_mappings[context].get(action)
                if btn and btn in mouse_collection:
                    if not self._is_consumed_by_higher_priority(
                        btn, context, is_mouse=True
                    ):
                        return True

        return False

    def is_action_pressed(self, action: str) -> bool:
        """
        Check if an action is active (key/button held down).

        Args:
            action (str): The action name.

        Returns:
            bool: True if the action is currently active.
        """
        return self._action_triggered_in_collections(
            action, self._keys_pressed, self._mouse_buttons
        )

    def is_action_just_pressed(self, action: str) -> bool:
        """
        Check if an action was just pressed this frame.

        Args:
            action (str): The action name.

        Returns:
            bool: True if the action was just pressed.
        """
        return self._action_triggered_in_collections(
            action, self._keys_down, self._mouse_buttons_down
        )

    def is_action_just_released(self, action: str) -> bool:
        """
        Check if an action was just released this frame.

        Args:
            action (str): The action name.

        Returns:
            bool: True if the action was just released.
        """
        return self._action_triggered_in_collections(
            action, self._keys_up, self._mouse_buttons_up
        )

    def get_mouse_position(self) -> tuple[int, int]:
        """
        Returns the current mouse position.

        Returns:
            tuple[int, int]: The (x, y) coordinates of the mouse.
        """
        return self._mouse_pos

    def get_mouse_wheel(self) -> float:
        """
        Returns the mouse wheel delta.

        Returns:
            float: The amount the mouse wheel was scrolled.
        """
        return self._mouse_wheel

    def get_mouse_rel(self) -> tuple[int, int]:
        """
        Returns the accumulated mouse movement delta since the last frame.

        Accumulated rather than per-event so that multiple MOUSEMOTION events
        within the same frame are collapsed into a single combined delta.

        Returns:
            tuple[int, int]: The (dx, dy) relative mouse movement this frame.
        """
        return self._mouse_rel
