import pytest
import pygame
from unittest.mock import MagicMock
from yukkuri_game.engine.input_manager import InputManager, InputContext

@pytest.fixture
def input_manager():
    return InputManager()

def test_input_context_management(input_manager):
    assert InputContext.MENU in input_manager._active_contexts

    input_manager.set_context(InputContext.GAMEPLAY, active=True)
    assert InputContext.GAMEPLAY in input_manager._active_contexts

    input_manager.set_context(InputContext.MENU, active=False)
    assert InputContext.MENU not in input_manager._active_contexts

    input_manager.switch_context(InputContext.MENU)
    assert len(input_manager._active_contexts) == 1
    assert InputContext.MENU in input_manager._active_contexts

def test_key_processing(input_manager):
    # Simulate Key Press
    event_down = MagicMock()
    event_down.type = pygame.KEYDOWN
    event_down.key = pygame.K_z

    input_manager.process_event(event_down)

    assert pygame.K_z in input_manager._keys_pressed
    assert pygame.K_z in input_manager._keys_down

    # Simulate Key Release
    event_up = MagicMock()
    event_up.type = pygame.KEYUP
    event_up.key = pygame.K_z

    input_manager.process_event(event_up)

    assert pygame.K_z not in input_manager._keys_pressed
    assert pygame.K_z in input_manager._keys_up

    # Update should clear frame transient state
    input_manager.update()
    assert pygame.K_z not in input_manager._keys_down
    assert pygame.K_z not in input_manager._keys_up

def test_action_checking(input_manager):
    input_manager.switch_context(InputContext.GAMEPLAY)

    # "interact" is mapped to K_z in GAMEPLAY
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_z
    input_manager.process_event(event)

    assert input_manager.is_action_pressed("interact")
    assert input_manager.is_action_just_pressed("interact")

    input_manager.update()
    assert input_manager.is_action_pressed("interact")
    assert not input_manager.is_action_just_pressed("interact")

def test_context_priority_blocking(input_manager):
    """Test that higher priority context blocks lower priority input if consumed."""
    # MENU (10) > GAMEPLAY (1)

    # Suppose both have "up" mapped to K_UP
    # MENU: up -> K_UP
    # GAMEPLAY: up -> K_UP

    input_manager.set_context(InputContext.GAMEPLAY, True)
    input_manager.set_context(InputContext.MENU, True)

    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_UP
    input_manager.process_event(event)

    # Check if MENU consumes it
    # Implementation detail: _is_consumed checks if a HIGHER priority context consumes it.
    # When checking for MENU (High), no higher context exists -> Not consumed -> Action triggered.
    # When checking for GAMEPLAY (Low), MENU (High) has it mapped -> Consumed -> Action BLOCKED.

    # We need to verify that is_action_pressed("up") returns True for MENU but False for GAMEPLAY logic?
    # Actually is_action_pressed takes an action name string.
    # If I ask for "up", it checks all contexts.
    # If MENU handles "up", it returns True.
    # If I had different action names, say "menu_up" and "game_up", and both used K_UP.

    # Let's test with custom mappings or rely on existing.
    # Existing: Both have "up": K_UP.

    # However, InputManager._check_action_in_collection iterates contexts high to low.
    # It finds "up" in MENU. Checks if anything HIGHER consumes it. No. Returns True.

    assert input_manager.is_action_pressed("up")

    # But what if we want to verify that GAMEPLAY didn't receive it?
    # The public API doesn't expose "get action for context".
    # But we can infer priority behavior by consuming a key that is used in Low context but mapped to something else in High context?
    # Or simply: if I disable MENU, GAMEPLAY should get it.

    input_manager.set_context(InputContext.MENU, False)
    assert input_manager.is_action_pressed("up")

def test_priority_consumption_explicit(input_manager):
    # Let's mock the mappings to be sure
    input_manager._key_mappings = {
        InputContext.MENU: {"unique_menu": pygame.K_a}, # Priority 10
        InputContext.GAMEPLAY: {"unique_game": pygame.K_a} # Priority 1
    }

    input_manager.set_context(InputContext.MENU, True)
    input_manager.set_context(InputContext.GAMEPLAY, True)

    # Press K_a
    event = MagicMock()
    event.type = pygame.KEYDOWN
    event.key = pygame.K_a
    input_manager.process_event(event)

    # MENU should see it
    assert input_manager.is_action_pressed("unique_menu")

    # GAMEPLAY should NOT see it because MENU consumes K_a
    assert not input_manager.is_action_pressed("unique_game")

    # If we disable MENU
    input_manager.set_context(InputContext.MENU, False)
    assert input_manager.is_action_pressed("unique_game")

def test_mouse_input(input_manager):
    input_manager.switch_context(InputContext.GAMEPLAY)

    # Move mouse
    event_move = MagicMock()
    event_move.type = pygame.MOUSEMOTION
    event_move.pos = (100, 200)
    input_manager.process_event(event_move)

    assert input_manager.get_mouse_position() == (100, 200)

    # Click Left Button (1) -> "select"
    event_click = MagicMock()
    event_click.type = pygame.MOUSEBUTTONDOWN
    event_click.button = 1
    input_manager.process_event(event_click)

    assert input_manager.is_action_just_pressed("select")

    # Wheel
    event_wheel = MagicMock()
    event_wheel.type = pygame.MOUSEWHEEL
    event_wheel.y = 1.0
    input_manager.process_event(event_wheel)

    assert input_manager.get_mouse_wheel() == 1.0

    input_manager.update()
    assert input_manager.get_mouse_wheel() == 0.0
