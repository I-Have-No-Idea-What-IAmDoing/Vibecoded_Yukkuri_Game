import pytest
from unittest.mock import MagicMock, patch
from src.yukkuri_game.game.events import NotificationEvent
from src.yukkuri_game.engine.event_bus import EventBus
from src.yukkuri_game.game.ui.hud import HUD

@patch('src.yukkuri_game.game.ui.notification_log.UITextBox')
@patch('src.yukkuri_game.game.ui.hud_layout.UILabel')
@patch('src.yukkuri_game.game.ui.hud_layout.UIButton')
@patch('src.yukkuri_game.game.ui.hud_layout.UIPanel')
def test_hud_notification_integration(mock_panel, mock_button, mock_label, mock_textbox):
    # Setup
    manager = MagicMock()
    world = MagicMock()

    # Mock Services
    services = MagicMock()
    world.services = services

    # Mock GameManager
    gm = MagicMock()
    services.get.return_value = gm # Default for any get

    # Need to make sure specific gets return correct mocks
    event_bus = EventBus()

    def get_side_effect(cls):
        if cls.__name__ == 'EventBus':
            return event_bus
        if cls.__name__ == 'GameManager':
            return gm
        if cls.__name__ == 'EntityFactory':
            rm = MagicMock()
            rm.yukkuri_types = {}
            rm.item_types = {}
            factory = MagicMock()
            factory.rm = rm
            return factory
        return MagicMock()

    services.get.side_effect = get_side_effect

    # Initialize HUD
    hud = HUD(manager, world)

    # Mock the notification log in layout
    hud.layout.notification_log = MagicMock()

    # Trigger Event
    event_bus.publish(NotificationEvent("Test Notification"))

    # Verify HUD received and logged it
    hud.layout.notification_log.add_message.assert_called_with("Test Notification")
