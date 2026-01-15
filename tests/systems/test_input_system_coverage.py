import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.components import Transform, Selectable
from yukkuri_game.game.yukkuri_components import Poop
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, CleanToolRequestedEvent
from yukkuri_game.game.services import InputService
from yukkuri_game.engine.input_manager import InputManager


# Mock pygame.key.get_pressed
@pytest.fixture
def mock_keys():
    with patch("pygame.key.get_pressed") as mock:
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
    # Test drag position update
    world = World()
    yukkurrium = MagicMock()
    yukkurrium.screen_to_world.return_value = (100.0, 100.0)
    system = InputSystem(yukkurrium)

    # Setup Services
    input_service = InputService()
    input_service.is_dragging = True
    world.services.register(input_service, InputService)

    input_manager = MagicMock(spec=InputManager)
    input_manager.get_mouse_position.return_value = (100, 100)
    input_manager.is_action_just_pressed.return_value = False
    input_manager.is_action_just_released.return_value = False
    world.services.register(input_manager, InputManager)

    # Register EventBus
    event_bus = MagicMock(spec=EventBus)
    world.services.register(event_bus, EventBus)

    # Pre-set dependencies on system
    system.input_service = input_service
    system.input_manager = input_manager
    system.drag_start_pos = (0, 0)

    # Mock pygame.display
    with patch("pygame.display.get_surface") as mock_get_surface:
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (800, 600)
        mock_get_surface.return_value = mock_surface

        # Call update
        system.update(world, 0.1)

    # Verify input_service updated
    assert input_service.drag_current_pos == (100, 100)
    assert system.drag_end_pos == (100.0, 100.0)
