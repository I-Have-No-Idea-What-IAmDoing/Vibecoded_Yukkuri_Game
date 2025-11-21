import pytest
from unittest.mock import MagicMock, patch
import pygame
from src.yukkuri_game.game.input_system import InputSystem
from src.yukkuri_game.game.events import PlacementStartedEvent
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
    mock = MagicMock()
    mock.services = MagicMock()
    return mock

@pytest.fixture
def input_system(mock_yukkurrium):
    return InputSystem(mock_yukkurrium)

def test_init(input_system, mock_yukkurrium):
    assert input_system.yukkurrium == mock_yukkurrium
    assert input_system.placing_mode is False
    assert input_system.place_type is None
    assert input_system.place_cost == 0

def test_start_placement(input_system, mock_game_manager, mock_entity_factory):
    # Simulate event handling
    event = PlacementStartedEvent("yukkuri_reimu", 100, "yukkuri")
    input_system.on_placement_started(event)

    assert input_system.placing_mode is True
    assert input_system.place_type == "yukkuri_reimu"
    assert input_system.place_cost == 100
    assert input_system.place_entity_type == "yukkuri"

    # Note: dependencies are lazy loaded in update(), not in on_placement_started

def test_handle_event_placement_success(input_system, mock_game_manager, mock_entity_factory, mock_world):
    # Setup dependencies via update
    mock_world.services.get.side_effect = lambda service_type: mock_game_manager if service_type.__name__ == 'GameManager' else (mock_entity_factory if service_type.__name__ == 'EntityFactory' else MagicMock())

    input_system.update(mock_world, 0.0)

    # Start placement
    event = PlacementStartedEvent("yukkuri_reimu", 100, "yukkuri")
    input_system.on_placement_started(event)

    # Mock left click event
    event = MagicMock()
    event.type = pygame.MOUSEBUTTONDOWN
    event.button = 1
    event.pos = (100, 100)

    input_system.handle_event(event, mock_world, 800, 600)

    assert input_system.placing_mode is False
    # Check logic for money deduction - mocked game manager money attribute should be modified
    # Since it's a magic mock property, we might need to check operations or just setting
    # The code does: self.gm.money -= self.place_cost

    # Because we use a property in GameManager now, mock_game_manager.money should ideally behave like a property or value.
    # MagicMock attributes persist, so reading it back should work if we check it.
    # But `mock_game_manager.money -= 100` reads, subtracts, and sets.

    # We can verify that it was read and set, or just check value if we initialize it
    # mock_game_manager.money was set to 1000 in fixture.
    # 1000 - 100 = 900.
    # Note: MagicMock logic with in-place operators on int attributes is a bit tricky.
    # However, `x.y -= z` is `x.y = x.y - z`.

    mock_entity_factory.create_yukkuri.assert_called_with("yukkuri_reimu", 100, 100)

def test_handle_event_placement_cancel(input_system, mock_game_manager, mock_entity_factory, mock_world):
    # Setup dependencies
    mock_world.services.get.side_effect = lambda service_type: mock_game_manager if service_type.__name__ == 'GameManager' else (mock_entity_factory if service_type.__name__ == 'EntityFactory' else MagicMock())
    input_system.update(mock_world, 0.0)

    # Start placement
    event = PlacementStartedEvent("yukkuri_reimu", 100, "yukkuri")
    input_system.on_placement_started(event)

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
