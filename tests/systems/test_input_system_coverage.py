"""
Tests for InputSystem coverage — adapted for command-buffer architecture.

The private _handle_selection and _handle_cleaning methods have been
replaced by SelectEntitiesCommand and CleanEntityCommand respectively.
These tests verify the same gameplay logic through the command's execute().
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.commands import SelectEntitiesCommand, CleanEntityCommand
from yukkuri_game.engine.components import Transform, Selectable
from yukkuri_game.game.components import Poop
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, CleanToolRequestedEvent
from yukkuri_game.game.services import InputBufferService, InputService
from yukkuri_game.engine.input_manager import InputManager


def _make_world_with_bus() -> tuple[World, MagicMock]:
    """Creates a world with a mocked EventBus registered."""
    world = World()
    bus = MagicMock(spec=EventBus)
    world.services.register(bus, EventBus)
    return world, bus


# ---------------------------------------------------------------------------
# SelectEntitiesCommand — formerly _handle_selection
# ---------------------------------------------------------------------------


def test_handle_selection_drag() -> None:
    """Drag selection selects entities within the bounding box."""
    world, bus = _make_world_with_bus()

    e1 = world.create_entity(Transform(x=10, y=10), Selectable(selected=False))
    e2 = world.create_entity(Transform(x=100, y=100), Selectable(selected=False))

    cmd = SelectEntitiesCommand(
        start_pos=(0.0, 0.0),
        end_pos=(20.0, 20.0),
        drag_dist=10.0,
        is_shift_pressed=False,
    )
    cmd.execute(world)

    sel1 = world.get_component(e1, Selectable)
    sel2 = world.get_component(e2, Selectable)
    assert sel1 is not None and sel1.selected
    assert sel2 is not None and not sel2.selected

    bus.publish.assert_called()
    args, _ = bus.publish.call_args
    event = args[0]
    assert isinstance(event, EntitySelectedEvent)
    assert e1 in event.entity_ids


def test_handle_selection_click() -> None:
    """Click selection selects entity within click_radius."""
    world, _ = _make_world_with_bus()

    e1 = world.create_entity(Transform(x=10, y=10), Selectable(selected=False))

    cmd = SelectEntitiesCommand(
        start_pos=(12.0, 12.0),
        end_pos=(12.0, 12.0),
        drag_dist=0.0,
        is_shift_pressed=False,
    )
    cmd.execute(world)

    sel1 = world.get_component(e1, Selectable)
    assert sel1 is not None and sel1.selected


# ---------------------------------------------------------------------------
# CleanEntityCommand — formerly _handle_cleaning
# ---------------------------------------------------------------------------


def test_cleaning_logic() -> None:
    """CleanEntityCommand destroys nearby poop and plays a sound."""
    world, _ = _make_world_with_bus()
    audio_mock = MagicMock()
    from yukkuri_game.engine.protocols import IAudioProvider

    world.services.register(audio_mock, IAudioProvider)

    poop = world.create_entity(Poop(), Transform(x=50, y=50))

    cmd = CleanEntityCommand(wx=55, wy=55)
    cmd.execute(world)

    assert not world.entity_exists(poop)
    audio_mock.play_sound.assert_called()


# ---------------------------------------------------------------------------
# InputSystem event handlers
# ---------------------------------------------------------------------------


def test_clean_tool_requested_event() -> None:
    """CleanToolRequestedEvent calls start_cleaning on InputService."""
    system = InputSystem(MagicMock())
    system.input_service = MagicMock(spec=InputService)

    event = CleanToolRequestedEvent()
    system.on_clean_tool_requested(event)

    assert system.input_service.start_cleaning.called


# ---------------------------------------------------------------------------
# Drag-state update through InputSystem.update()
# ---------------------------------------------------------------------------


def test_handle_event_mouse_motion_drag() -> None:
    """Drag position is updated each frame while dragging."""
    world = World()
    camera_mock = MagicMock()
    camera_mock.screen_to_world.return_value = (100.0, 100.0)
    system = InputSystem(camera_mock)

    input_service = InputService()
    input_service.is_dragging = True
    world.services.register(input_service, InputService)

    buf = InputBufferService()
    world.services.register(buf, InputBufferService)

    input_manager = MagicMock(spec=InputManager)
    input_manager.get_mouse_position.return_value = (100, 100)
    input_manager.get_mouse_wheel.return_value = 0.0
    input_manager.get_mouse_rel.return_value = (0, 0)
    input_manager.is_action_just_pressed.return_value = False
    input_manager.is_action_just_released.return_value = False
    input_manager.is_action_pressed.return_value = False
    world.services.register(input_manager, InputManager)

    event_bus = MagicMock(spec=EventBus)
    world.services.register(event_bus, EventBus)

    system.input_service = input_service
    system.input_manager = input_manager
    system.drag_start_pos = (0.0, 0.0)

    with patch("pygame.display.get_surface") as mock_get_surface:
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (800, 600)
        mock_get_surface.return_value = mock_surface
        system.update(world, 0.1)

    assert input_service.drag_current_pos == (100, 100)
    assert system.drag_end_pos == (100.0, 100.0)
