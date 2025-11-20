import pytest
from unittest.mock import MagicMock, patch
import pygame
import pygame_gui
from src.yukkuri_game.game.ui.hud_layout import HudLayout
from src.yukkuri_game.game.ui.hud_events import HudEventHandler
from src.yukkuri_game.game.ui.windows import SelectionWindow, DebugWindow

# Mock pygame_gui elements to avoid needing a real display
@patch('src.yukkuri_game.game.ui.hud_layout.UIPanel')
@patch('src.yukkuri_game.game.ui.hud_layout.UILabel')
@patch('src.yukkuri_game.game.ui.hud_layout.UIButton')
def test_hud_layout_creation(mock_btn, mock_lbl, mock_panel):
    manager = MagicMock()
    layout = HudLayout(manager, 800, 600)

    assert layout.width == 800
    assert layout.height == 600

    # Check that elements were created
    assert mock_panel.call_count == 2 # Top and bottom
    assert layout.save_btn is not None
    assert layout.load_btn is not None
    assert layout.add_reimu_btn is not None

def test_hud_event_handler():
    gm = MagicMock()
    layout = MagicMock()

    # Mock buttons in layout
    save_btn = MagicMock()
    layout.save_btn = save_btn

    selection_window = MagicMock()
    selection_window.is_active.return_value = False

    handler = HudEventHandler(gm, layout, selection_window)

    # Test Save Button
    event = MagicMock()
    event.type = pygame_gui.UI_BUTTON_PRESSED
    event.ui_element = save_btn

    assert handler.process_event(event) is True
    gm.save_game.assert_called_once()

    # Test Unhandled Event
    event.ui_element = MagicMock() # Some other button
    assert handler.process_event(event) is False

@patch('src.yukkuri_game.game.ui.windows.UIWindow')
@patch('src.yukkuri_game.game.ui.windows.UITextBox')
@patch('src.yukkuri_game.game.ui.windows.UIButton')
def test_selection_window_show(mock_btn, mock_txt, mock_win):
    manager = MagicMock()
    window = SelectionWindow(manager, 800)

    world = MagicMock()
    # Setup world to have Selectable and YukkuriStats
    world.has_component.return_value = True
    stats = MagicMock()
    stats.name = "Reimu"
    world.get_component.return_value = stats

    window.show(1, world)

    assert window.is_active() is True
    assert window.current_entity == 1
    mock_win.assert_called_once()

    window.hide()
    assert window.is_active() is False
