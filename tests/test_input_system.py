import pytest
from unittest.mock import MagicMock, patch
import pygame
from src.yukkuri_game.game.input_system import InputSystem
from src.yukkuri_game.game.components import Transform, Selectable

@pytest.fixture
def mock_yukkurrium():
    mock = MagicMock()
    mock.screen_to_world.return_value = (100, 100)
    return mock

@pytest.fixture
def mock_game_manager():
    mock = MagicMock()
    mock.money = 1000
    return mock

@pytest.fixture
def mock_entity_factory():
    return MagicMock()

@pytest.fixture
def mock_world():
    return MagicMock()

@pytest.fixture
def input_system(mock_yukkurrium):
    return InputSystem(mock_yukkurrium)

def test_init(input_system, mock_yukkurrium):
    assert input_system.yukkurrium == mock_yukkurrium
    assert input_system.placing_mode is False
    assert input_system.place_type is None
    assert input_system.place_cost == 0

def test_start_placement(input_system, mock_game_manager, mock_entity_factory):
    input_system.start_placement("yukkuri_reimu", 100, "yukkuri", mock_game_manager, mock_entity_factory)

    assert input_system.placing_mode is True
    assert input_system.place_type == "yukkuri_reimu"
    assert input_system.place_cost == 100
    assert input_system.place_entity_type == "yukkuri"
    assert input_system.gm == mock_game_manager
    assert input_system.factory == mock_entity_factory

def test_handle_event_placement_success(input_system, mock_game_manager, mock_entity_factory, mock_world):
    input_system.start_placement("yukkuri_reimu", 100, "yukkuri", mock_game_manager, mock_entity_factory)

    # Mock left click event
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = (100, 100)

    input_system.handle_event(event, mock_world, 800, 600)

    assert input_system.placing_mode is False
    mock_game_manager.money = 900 # Should have deducted 100
    mock_entity_factory.create_yukkuri.assert_called_with("yukkuri_reimu", 100, 100)

def test_handle_event_placement_cancel(input_system, mock_game_manager, mock_entity_factory, mock_world):
    input_system.start_placement("yukkuri_reimu", 100, "yukkuri", mock_game_manager, mock_entity_factory)

    # Mock right click event
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 3

    input_system.handle_event(event, mock_world, 800, 600)

    assert input_system.placing_mode is False
    mock_entity_factory.create_yukkuri.assert_not_called()

def test_handle_event_ui_interaction(input_system, mock_world):
    # Mock UI Manager hovering
    mock_ui_manager = MagicMock()
    mock_ui_manager.get_hovering_any_element.return_value = True

    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1

    input_system.handle_event(event, mock_world, 800, 600, mock_ui_manager)

    # Should return early, so no world interaction
    input_system.yukkurrium.screen_to_world.assert_not_called()

def test_handle_event_selection(input_system, mock_world):
    # Setup mock entities
    entity = 1
    trans = Transform(x=100, y=100)
    selectable = Selectable()

    mock_world.get_entities_with.return_value = [entity]

    def get_component_side_effect(ent, comp_type):
        if comp_type == Transform:
            return trans
        if comp_type == Selectable:
            return selectable
        return None

    mock_world.get_component.side_effect = get_component_side_effect

    # Mock left click at (100, 100) which matches the entity position
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = (100, 100) # screen coords mock -> world coords mock is also 100,100

    with patch('pygame.key.get_pressed', return_value={pygame.K_LSHIFT: False}):
        input_system.handle_event(event, mock_world, 800, 600)

    assert selectable.selected is True
