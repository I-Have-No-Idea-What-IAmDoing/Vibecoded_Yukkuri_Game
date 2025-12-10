"""
Tests for the Input Manager.
"""

import pytest
import pygame
from yukkuri_game.engine.input_manager import InputManager, InputContext


@pytest.fixture
def input_manager() -> InputManager:
    """
    Creates an InputManager instance for testing.
    """
    return InputManager()


def test_initialization(input_manager: InputManager) -> None:
    """
    Tests initialization of InputManager.
    """
    # Initially only MENU context is active
    assert InputContext.MENU in input_manager._active_contexts
    assert len(input_manager._active_contexts) == 1
    assert input_manager._mouse_pos == (0, 0)
    assert input_manager._mouse_wheel == 0.0


def test_context_management(input_manager: InputManager) -> None:
    """
    Tests enabling, disabling, and switching contexts.
    """
    # Add Gameplay context
    input_manager.set_context(InputContext.GAMEPLAY, active=True)
    assert InputContext.GAMEPLAY in input_manager._active_contexts
    assert InputContext.MENU in input_manager._active_contexts

    # Disable Gameplay context
    input_manager.set_context(InputContext.GAMEPLAY, active=False)
    assert InputContext.GAMEPLAY not in input_manager._active_contexts
    assert InputContext.MENU in input_manager._active_contexts

    # Switch to Gameplay context (clears others)
    input_manager.switch_context(InputContext.GAMEPLAY)
    assert InputContext.GAMEPLAY in input_manager._active_contexts
    assert InputContext.MENU not in input_manager._active_contexts
    assert len(input_manager._active_contexts) == 1


def test_process_keyboard_events(input_manager: InputManager) -> None:
    """
    Tests processing of keyboard events.
    """
    # Simulate Key Down
    key_down_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    input_manager.process_event(key_down_event)

    assert pygame.K_SPACE in input_manager._keys_pressed
    assert pygame.K_SPACE in input_manager._keys_down

    # Simulate Key Up
    key_up_event = pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)
    input_manager.process_event(key_up_event)

    assert pygame.K_SPACE not in input_manager._keys_pressed
    assert pygame.K_SPACE in input_manager._keys_up


def test_process_mouse_events(input_manager: InputManager) -> None:
    """
    Tests processing of mouse events.
    """
    # Simulate Mouse Button Down (Left Click)
    mouse_down_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 200)
    )
    input_manager.process_event(mouse_down_event)

    assert 1 in input_manager._mouse_buttons
    assert 1 in input_manager._mouse_buttons_down

    # Simulate Mouse Button Up
    mouse_up_event = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(100, 200))
    input_manager.process_event(mouse_up_event)

    assert 1 not in input_manager._mouse_buttons
    assert 1 in input_manager._mouse_buttons_up

    # Simulate Mouse Motion
    mouse_move_event = pygame.event.Event(pygame.MOUSEMOTION, pos=(150, 250))
    input_manager.process_event(mouse_move_event)
    assert input_manager.get_mouse_position() == (150, 250)

    # Simulate Mouse Wheel
    mouse_wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1.0)
    input_manager.process_event(mouse_wheel_event)
    assert input_manager.get_mouse_wheel() == 1.0


def test_update_clears_transient_state(input_manager: InputManager) -> None:
    """
    Tests that update() clears just_pressed/released states.
    """
    input_manager.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
    input_manager.process_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_b))
    input_manager.process_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    input_manager.process_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1.0))

    assert pygame.K_a in input_manager._keys_down
    assert pygame.K_b in input_manager._keys_up
    assert 1 in input_manager._mouse_buttons_down
    assert input_manager._mouse_wheel == 1.0

    input_manager.update()

    assert len(input_manager._keys_down) == 0
    assert len(input_manager._keys_up) == 0
    assert len(input_manager._mouse_buttons_down) == 0
    assert len(input_manager._mouse_buttons_up) == 0
    assert input_manager._mouse_wheel == 0.0


def test_action_mapping_menu(input_manager: InputManager) -> None:
    """
    Tests action mapping in MENU context.
    """
    # Default is MENU context
    # confirm -> pygame.K_RETURN

    input_manager.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    assert input_manager.is_action_pressed("confirm")
    assert input_manager.is_action_just_pressed("confirm")

    input_manager.process_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))

    assert not input_manager.is_action_pressed("confirm")
    assert input_manager.is_action_just_released("confirm")


def test_action_mapping_gameplay(input_manager: InputManager) -> None:
    """
    Tests action mapping in GAMEPLAY context.
    """
    input_manager.switch_context(InputContext.GAMEPLAY)

    # up -> pygame.K_UP
    input_manager.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))

    assert input_manager.is_action_pressed("up")

    # select -> Mouse Button 1
    input_manager.process_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    assert input_manager.is_action_pressed("select")


def test_input_consumption(input_manager: InputManager) -> None:
    """
    Tests that higher priority contexts consume input.
    """
    # Enable both contexts
    input_manager.set_context(InputContext.GAMEPLAY, active=True)  # Priority 1
    input_manager.set_context(InputContext.MENU, active=True)  # Priority 10

    # Assume MENU has 'up' mapped to K_UP, and GAMEPLAY also has 'up' mapped to K_UP.
    # But checking source code:
    # MENU: up -> K_UP
    # GAMEPLAY: up -> K_UP

    # If MENU is active (higher priority), checking "up" in GAMEPLAY context should fail
    # if it were checking internally, but is_action_pressed checks if ANY active context maps it.

    # However, the InputManager._check_action_in_collection iterates contexts from high to low.
    # If MENU handles it, it returns True.

    # To test consumption properly, we need a scenario where a high priority context consumes a key
    # that a lower priority context also uses, and we want to ensure the lower priority one
    # doesn't trigger if we were querying specifically for it?
    # Wait, `is_action_pressed` takes an action string. The action string might be the same or different.

    # Let's look at `_is_consumed`.
    # It checks if a key is used by a higher priority context.

    # Case: "pause" is in GAMEPLAY (K_ESCAPE). "cancel" is in MENU (K_ESCAPE).
    # If both contexts are active, K_ESCAPE should trigger "cancel" (MENU).
    # "pause" (GAMEPLAY) should be blocked because MENU consumes K_ESCAPE.

    input_manager.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    # MENU (Priority 10) should handle it
    assert input_manager.is_action_pressed("cancel")

    # GAMEPLAY (Priority 1) should NOT handle it because it's consumed
    assert not input_manager.is_action_pressed("pause")

    # Disable MENU context
    input_manager.set_context(InputContext.MENU, active=False)

    # Now GAMEPLAY should handle it
    assert input_manager.is_action_pressed("pause")
