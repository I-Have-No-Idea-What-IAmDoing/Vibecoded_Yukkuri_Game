import pytest
from unittest.mock import MagicMock, patch
import pygame
import pygame_gui
from yukkuri_game.game.ui.hud import HUD
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, GamePausedEvent
from yukkuri_game.game.yukkuri_components import YukkuriStats

@pytest.fixture
def mock_ui_manager():
    return MagicMock(spec=pygame_gui.UIManager)

@pytest.fixture
def mock_world():
    return MagicMock()

@pytest.fixture
def hud(mock_ui_manager, mock_world):
    # Mock services used in HUD init
    gm = MagicMock(spec=GameManager)
    factory = MagicMock(spec=EntityFactory)
    event_bus = MagicMock(spec=EventBus)

    mock_world.services.get.side_effect = lambda t: gm if t == GameManager else (factory if t == EntityFactory else (event_bus if t == EventBus else None))

    with patch('yukkuri_game.game.ui.hud.HudLayout'), \
         patch('yukkuri_game.game.ui.hud.HudEvents'), \
         patch('yukkuri_game.game.ui.hud.HudRenderer'):

        hud = HUD(mock_ui_manager, mock_world)

    return hud

def test_hud_init(hud, mock_world):
    assert hud.layout is not None
    assert hud.events is not None
    assert hud.renderer is not None

    # Check event subscriptions
    hud.event_bus.subscribe.assert_any_call(EntitySelectedEvent, hud.on_entity_selected)
    hud.event_bus.subscribe.assert_any_call(GamePausedEvent, hud.on_game_paused)

def test_on_entity_selected(hud, mock_world):
    event = EntitySelectedEvent(entity_id=10)

    # Mock has_component for selection window update
    mock_world.has_component.return_value = True

    hud.on_entity_selected(event)

    assert hud.selected_entity == 10
    hud.events.set_selected_entity.assert_called_with(10)
    hud.layout.create_selection_window.assert_called_with(True)

def test_on_entity_selected_none(hud):
    event = EntitySelectedEvent(entity_id=-1)

    hud.on_entity_selected(event)

    assert hud.selected_entity == -1
    hud.layout.close_selection_window.assert_called()

def test_on_game_paused(hud):
    # We need to mock pause_btn on layout
    hud.layout.pause_btn = MagicMock()

    event = GamePausedEvent(paused=True)
    hud.on_game_paused(event)
    hud.layout.pause_btn.set_text.assert_called_with("Resume")

    event = GamePausedEvent(paused=False)
    hud.on_game_paused(event)
    hud.layout.pause_btn.set_text.assert_called_with("Pause")

def test_toggle_debug(hud):
    assert hud.show_debug is False

    hud.toggle_debug()
    assert hud.show_debug is True
    hud.layout.create_debug_window.assert_called()

    hud.toggle_debug()
    assert hud.show_debug is False
    hud.layout.close_debug_window.assert_called()

def test_update(hud):
    hud.fps = 60.0
    hud.update(0.1)

    assert hud.renderer.fps == 60.0
    hud.renderer.update.assert_called_with(0.1, -1, False)

def test_show_error(hud):
    hud.show_error("Error!")
    hud.renderer.show_error.assert_called_with("Error!")

def test_process_event_integration(hud):
    # Test interaction between HUD and its components during event processing
    event = MagicMock()
    event.type = pygame_gui.UI_BUTTON_PRESSED

    hud.process_event(event)

    # Verify events process_event is called
    hud.events.process_event.assert_called_with(event)

def test_process_event_sell_logic(hud):
    # Test logic that happens in HUD.process_event after delegation
    event = MagicMock()
    event.type = pygame_gui.UI_BUTTON_PRESSED
    hud.layout.sell_btn = MagicMock()
    event.ui_element = hud.layout.sell_btn

    hud.selected_entity = 10

    hud.process_event(event)

    assert hud.selected_entity == -1
    hud.layout.close_selection_window.assert_called()
    hud.events.set_selected_entity.assert_called_with(-1)
