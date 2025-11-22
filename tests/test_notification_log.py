import pytest
from unittest.mock import MagicMock, patch
import pygame_gui
from src.yukkuri_game.game.ui.notification_log import NotificationLog

@patch('src.yukkuri_game.game.ui.notification_log.UITextBox')
def test_notification_log_creation(mock_textbox):
    manager = MagicMock(spec=pygame_gui.UIManager)
    log = NotificationLog(manager, 1280, 720)
    assert log.messages == []
    assert log.max_messages == 50
    mock_textbox.assert_called_once()

@patch('src.yukkuri_game.game.ui.notification_log.UITextBox')
def test_notification_log_add_message(mock_textbox):
    manager = MagicMock(spec=pygame_gui.UIManager)
    log = NotificationLog(manager, 1280, 720)

    log.add_message("Test Message")
    assert "Test Message" in log.messages
    assert len(log.messages) == 1

    log.log_text_box.set_text.assert_called_with("Test Message")

@patch('src.yukkuri_game.game.ui.notification_log.UITextBox')
def test_notification_log_limit(mock_textbox):
    manager = MagicMock(spec=pygame_gui.UIManager)
    log = NotificationLog(manager, 1280, 720)
    log.max_messages = 5

    for i in range(10):
        log.add_message(f"Msg {i}")

    assert len(log.messages) == 5
    assert log.messages[0] == "Msg 5"
    assert log.messages[-1] == "Msg 9"
