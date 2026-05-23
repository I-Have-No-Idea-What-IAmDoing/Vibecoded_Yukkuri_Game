"""
Integration tests for HUD logging level and channel filters.
"""

import pygame
import pygame_gui
from unittest.mock import MagicMock, patch

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.events import LogMessageEvent
from yukkuri_game.game.ui.hud import HUD


class MockTextBox:
    """Mock for pygame_gui UITextBox to capture text and HTML text."""

    def __init__(self, *args, **kwargs) -> None:
        self.html_text = kwargs.get("html_text", "")
        self.scroll_bar = MagicMock()
        self.scroll_bar.scrollable_height = 100
        self.scroll_bar.scroll_position = 0

    def set_text(self, text: str) -> None:
        self.html_text = text

    def append_html_text(self, text: str) -> None:
        self.html_text += text


class MockButton:
    """Mock for pygame_gui UIButton to capture selection state and text."""

    def __init__(self, *args, **kwargs) -> None:
        self.text = kwargs.get("text", "")
        self.selected = False

    def select(self) -> None:
        self.selected = True

    def unselect(self) -> None:
        self.selected = False

    def set_text(self, text: str) -> None:
        self.text = text


class MockDropDownMenu:
    """Mock for pygame_gui UIDropDownMenu to capture chosen option."""

    def __init__(self, *args, **kwargs) -> None:
        self.selected_option = kwargs.get("starting_option", "All Logs")


def test_logging_filters_integration() -> None:
    """
    Test routing, filtering, freezing, and unfreezing of HUD logs.
    """
    # 1. Setup mock UIManager and ecs World
    ui_manager = MagicMock(spec=pygame_gui.UIManager)

    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    rm = MagicMock(spec=ResourceManager)
    rm.yukkuri_types = {}
    rm.item_types = {}
    world.services.register(rm, ResourceManager)

    # 2. Patch GUI elements to use our custom mock classes for the entire test
    with (
        patch(
            "yukkuri_game.game.ui.hud_layout.UITextBox",
            side_effect=MockTextBox,
        ),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIButton",
            side_effect=MockButton,
        ),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIDropDownMenu",
            side_effect=MockDropDownMenu,
        ),
        patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
        patch("yukkuri_game.game.ui.hud_layout.UILabel"),
        patch("yukkuri_game.game.ui.hud_layout.UIWindow"),
        patch("yukkuri_game.game.ui.hud_layout.UIScrollingContainer"),
        patch("yukkuri_game.game.ui.hud_layout.NonBlockingTextBox"),
    ):
        hud = HUD(ui_manager, world)

        # Pre-check initial welcome message
        assert len(hud.log_history) == 1
        assert hud.log_history[0].message == "Welcome to Yukkuri Game!"
        assert hud.log_history[0].channel == "General"

        # Send messages on different channels
        event_bus.publish(
            LogMessageEvent(message="General log", channel="General")
        )
        event_bus.publish(
            LogMessageEvent(message="AI decision", channel="AI")
        )
        event_bus.publish(
            LogMessageEvent(message="Economy deal", channel="Economy")
        )

        # Verify history has all logs
        assert len(hud.log_history) == 4

        # 1. By default, show_debug is False. Debug logs should NOT be in the console.
        ui_manager.update(0.1)
        html_text = hud.layout.log_box.html_text
        assert "General log" in html_text
        assert "Economy deal" in html_text
        assert "AI decision" not in html_text

        # 2. Toggle debug mode on. Debug logs should now be rendered.
        hud.toggle_debug()
        assert hud.show_debug is True
        ui_manager.update(0.1)
        html_text = hud.layout.log_box.html_text
        assert "General log" in html_text
        assert "Economy deal" in html_text
        assert "AI decision" in html_text

        # Test set log filter to "AI"
        hud.set_log_filter("AI")
        html_text = hud.layout.log_box.html_text
        assert "AI decision" in html_text
        assert "General log" not in html_text
        assert "Economy deal" not in html_text

        # Test set log filter to "Economy"
        hud.set_log_filter("Economy")
        html_text = hud.layout.log_box.html_text
        assert "Economy deal" in html_text
        assert "General log" not in html_text
        assert "AI decision" not in html_text

        # Test reset log filter to "All"
        hud.set_log_filter("All")
        html_text = hud.layout.log_box.html_text
        assert "General log" in html_text
        assert "AI decision" in html_text
        assert "Economy deal" in html_text

        # Test freezing
        hud.toggle_log_freeze()
        assert hud.is_log_frozen is True
        assert hud.layout.log_freeze_btn.selected is True
        assert hud.layout.log_freeze_btn.text == "Frozen"

        # Publish message while frozen
        event_bus.publish(
            LogMessageEvent(message="Frozen AI log", channel="AI")
        )
        assert len(hud.log_history) == 5

        # Should not appear in log box yet
        html_text = hud.layout.log_box.html_text
        assert "Frozen AI log" not in html_text

        # Unfreeze and verify it flushes
        hud.toggle_log_freeze()
        assert hud.is_log_frozen is False
        assert hud.layout.log_freeze_btn.selected is False
        assert hud.layout.log_freeze_btn.text == "Freeze"

        html_text = hud.layout.log_box.html_text
        assert "Frozen AI log" in html_text

        hud.cleanup()


def test_logging_filters_ui_events() -> None:
    """
    Test that dropdown changes and button clicks trigger correct HUD logic.
    """
    ui_manager = MagicMock(spec=pygame_gui.UIManager)

    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    rm = MagicMock(spec=ResourceManager)
    rm.yukkuri_types = {}
    rm.item_types = {}
    world.services.register(rm, ResourceManager)

    with (
        patch(
            "yukkuri_game.game.ui.hud_layout.UITextBox",
            side_effect=MockTextBox,
        ),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIButton",
            side_effect=MockButton,
        ),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIDropDownMenu",
            side_effect=MockDropDownMenu,
        ),
        patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
        patch("yukkuri_game.game.ui.hud_layout.UILabel"),
        patch("yukkuri_game.game.ui.hud_layout.UIWindow"),
        patch("yukkuri_game.game.ui.hud_layout.UIScrollingContainer"),
        patch("yukkuri_game.game.ui.hud_layout.NonBlockingTextBox"),
    ):
        hud = HUD(ui_manager, world)

        # Trigger dropdown changed event
        fake_dropdown_event = pygame.event.Event(
            pygame_gui.UI_DROP_DOWN_MENU_CHANGED,
            {
                "ui_element": hud.layout.log_filter_menu,
                "text": "AI",
            },
        )
        hud.process_event(fake_dropdown_event)
        assert hud.current_log_filter == "AI"

        # Trigger freeze button pressed event
        fake_btn_event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {
                "ui_element": hud.layout.log_freeze_btn,
            },
        )
        hud.process_event(fake_btn_event)
        assert hud.is_log_frozen is True

        hud.cleanup()
