import pytest
from unittest.mock import MagicMock, patch
import pygame
from src.yukkuri_game.game.input_system import InputSystem
from src.yukkuri_game.game.components import Transform, Selectable
from src.yukkuri_game.game.yukkuri_components import Poop
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.events import EntitySelectedEvent, CleanToolRequestedEvent
from src.yukkuri_game.game.services import InputService

# Mock pygame.key.get_pressed
@pytest.fixture
def mock_keys():
    with patch('pygame.key.get_pressed') as mock:
        # Return a mock object that returns False (0) for any key access by default
        mock_return = MagicMock()
        mock_return.__getitem__.return_value = 0
        mock.return_value = mock_return
        yield mock

def test_handle_selection_drag(mock_keys):
    # Test drag selection logic directly
    world = World()
    yukkurrium = MagicMock()
    system = InputSystem(yukkurrium)
    system.event_bus = MagicMock()

    # Create entities
    e1 = world.create_entity()
    world.add_component(e1, Transform(x=10, y=10))
    world.add_component(e1, Selectable(selected=False))

    e2 = world.create_entity()
    world.add_component(e2, Transform(x=100, y=100))
    world.add_component(e2, Selectable(selected=False))

    # Select area covering e1 only
    start_pos = (0, 0)
    end_pos = (20, 20)

    # Simulate drag distance > 5.0
    system._handle_selection(world, start_pos, end_pos, drag_dist=10.0)

    # e1 should be selected, e2 not
    sel1 = world.get_component(e1, Selectable)
    sel2 = world.get_component(e2, Selectable)
    assert sel1.selected
    assert not sel2.selected

    # Verify event
    system.event_bus.publish.assert_called()
    args, _ = system.event_bus.publish.call_args
    event = args[0]
    assert isinstance(event, EntitySelectedEvent)
    assert e1 in event.entity_ids

def test_handle_selection_click(mock_keys):
    world = World()
    yukkurrium = MagicMock()
    system = InputSystem(yukkurrium)
    system.event_bus = MagicMock()

    e1 = world.create_entity()
    world.add_component(e1, Transform(x=10, y=10))
    world.add_component(e1, Selectable(selected=False))

    # Click near e1
    start_pos = (12, 12)
    end_pos = (12, 12)

    system._handle_selection(world, start_pos, end_pos, drag_dist=0.0)

    sel1 = world.get_component(e1, Selectable)
    assert sel1.selected

def test_cleaning_logic():
    world = World()
    yukkurrium = MagicMock()
    system = InputSystem(yukkurrium)
    system.audio = MagicMock()

    # Create poop
    poop = world.create_entity()
    world.add_component(poop, Poop())
    world.add_component(poop, Transform(x=50, y=50))

    # Clean near poop
    system._handle_cleaning(world, 55, 55)

    # Poop should be destroyed
    assert not world.entity_exists(poop)
    assert system.audio.play_sound.called

def test_clean_tool_requested_event():
    system = InputSystem(MagicMock())
    system.input_service = MagicMock(spec=InputService)

    event = CleanToolRequestedEvent()
    system.on_clean_tool_requested(event)

    assert system.input_service.start_cleaning.called

def test_handle_event_mouse_motion_drag():
    # Test visual drag rect update
    system = InputSystem(MagicMock())
    system.input_service = MagicMock(spec=InputService)
    system.drag_start_pos = (0, 0)
    system.yukkurrium.world_to_screen.return_value = (0, 0)
    system.yukkurrium.screen_to_world.return_value = (100.0, 100.0)

    event = MagicMock()
    event.type = pygame.MOUSEMOTION
    event.pos = (100, 100)

    system.handle_event(event, MagicMock(), 800, 600)

    assert system.input_service.selection_rect is not None
    assert system.input_service.selection_rect.width == 100
    assert system.input_service.selection_rect.height == 100
