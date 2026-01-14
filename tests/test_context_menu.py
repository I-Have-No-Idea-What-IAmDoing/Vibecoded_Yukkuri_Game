"""
Tests for Context Menu UI component.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pygame
import pygame_gui


class TestContextMenu:
    """Tests for the ContextMenu class."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock UI manager."""
        manager = MagicMock(spec=pygame_gui.UIManager)
        manager.window_resolution = (1280, 720)
        return manager

    @pytest.fixture
    def context_menu(self, mock_manager):
        """Create a ContextMenu instance with mocked dependencies."""
        # Patch UIPanel and UISelectionList to avoid actual pygame_gui initialization
        with patch("yukkuri_game.game.ui.context_menu.UIPanel") as MockPanel, \
             patch("yukkuri_game.game.ui.context_menu.UISelectionList") as MockList:
            MockPanel.return_value = MagicMock()
            MockList.return_value = MagicMock()
            
            from yukkuri_game.game.ui.context_menu import ContextMenu
            menu = ContextMenu(mock_manager)
            return menu

    def test_initial_state(self, context_menu):
        """Test that context menu starts inactive."""
        assert context_menu.active is False
        assert context_menu.panel is None
        assert context_menu.selection_list is None
        assert context_menu.on_action is None
        assert context_menu.target_data is None

    def test_show_creates_panel(self, context_menu):
        """Test that show() creates UI elements."""
        with patch("yukkuri_game.game.ui.context_menu.UIPanel") as MockPanel, \
             patch("yukkuri_game.game.ui.context_menu.UISelectionList") as MockList:
            mock_panel = MagicMock()
            MockPanel.return_value = mock_panel
            MockList.return_value = MagicMock()
            
            options = [("Option 1", "action_1"), ("Option 2", "action_2")]
            callback = Mock()
            
            context_menu.show((100, 100), options, callback, 42)
            
            assert context_menu.active is True
            assert context_menu.on_action == callback
            assert context_menu.target_data == 42
            assert context_menu.options == options
            MockPanel.assert_called_once()

    def test_show_with_empty_options_does_nothing(self, context_menu):
        """Test that show() with empty options list does nothing."""
        callback = Mock()
        context_menu.show((100, 100), [], callback, 42)
        
        assert context_menu.active is False
        assert context_menu.panel is None

    def test_hide_clears_state(self, context_menu):
        """Test that hide() properly cleans up state."""
        # Setup: Create a mock panel
        context_menu.panel = MagicMock()
        context_menu.selection_list = MagicMock()
        context_menu.active = True
        context_menu.on_action = Mock()
        context_menu.target_data = 42
        context_menu.options = [("Test", "test")]
        
        context_menu.hide()
        
        assert context_menu.active is False
        assert context_menu.panel is None
        assert context_menu.selection_list is None
        assert context_menu.on_action is None
        assert context_menu.target_data is None
        assert context_menu.options == []

    def test_process_event_inactive_returns_false(self, context_menu):
        """Test that process_event returns False when menu is inactive."""
        event = Mock()
        event.type = pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
        
        result = context_menu.process_event(event)
        
        assert result is False

    def test_process_event_click_outside_closes_menu(self, context_menu):
        """Test that clicking outside the menu closes it."""
        # Setup menu as active with panel
        context_menu.active = True
        context_menu.panel = MagicMock()
        # Use a MagicMock for rect with collidepoint returning False (click outside)
        mock_rect = MagicMock()
        mock_rect.collidepoint.return_value = False
        context_menu.panel.rect = mock_rect
        
        event = Mock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.pos = (500, 500)  # Outside panel
        
        result = context_menu.process_event(event)
        
        assert result is True
        assert context_menu.active is False
        mock_rect.collidepoint.assert_called_once_with(500, 500)

    def test_process_event_selection_triggers_callback(self, context_menu):
        """Test that selecting an option triggers the callback."""
        callback = Mock()
        context_menu.active = True
        context_menu.options = [("Option 1", "action_1"), ("Option 2", "action_2")]
        context_menu.on_action = callback
        context_menu.target_data = {"entity_id": 42}
        context_menu.selection_list = MagicMock()
        context_menu.panel = MagicMock()
        
        event = Mock()
        event.type = pygame_gui.UI_SELECTION_LIST_NEW_SELECTION
        event.ui_element = context_menu.selection_list
        event.text = "Option 1"
        
        result = context_menu.process_event(event)
        
        assert result is True
        callback.assert_called_once_with("action_1", {"entity_id": 42})
        assert context_menu.active is False


class TestContextMenuPositioning:
    """Tests for context menu screen positioning logic."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock UI manager with specific resolution."""
        manager = MagicMock(spec=pygame_gui.UIManager)
        manager.window_resolution = (1280, 720)
        return manager

    def test_menu_stays_on_screen_right_edge(self, mock_manager):
        """Test that menu doesn't go off right edge of screen."""
        with patch("yukkuri_game.game.ui.context_menu.UIPanel") as MockPanel, \
             patch("yukkuri_game.game.ui.context_menu.UISelectionList"):
            
            from yukkuri_game.game.ui.context_menu import ContextMenu
            menu = ContextMenu(mock_manager)
            
            # Click near right edge
            options = [("Test", "test")]
            menu.show((1250, 100), options, Mock(), None)
            
            # Verify panel was created with adjusted position
            call_args = MockPanel.call_args
            rect = call_args.kwargs.get("relative_rect") or call_args[1].get("relative_rect")
            # The rect should be adjusted to not go off screen
            assert rect.right <= 1280

    def test_menu_stays_on_screen_bottom_edge(self, mock_manager):
        """Test that menu doesn't go off bottom edge of screen."""
        with patch("yukkuri_game.game.ui.context_menu.UIPanel") as MockPanel, \
             patch("yukkuri_game.game.ui.context_menu.UISelectionList"):
            
            from yukkuri_game.game.ui.context_menu import ContextMenu
            menu = ContextMenu(mock_manager)
            
            # Click near bottom edge
            options = [("Test 1", "test1"), ("Test 2", "test2"), ("Test 3", "test3")]
            menu.show((100, 680), options, Mock(), None)
            
            # Verify panel was created with adjusted position
            call_args = MockPanel.call_args
            rect = call_args.kwargs.get("relative_rect") or call_args[1].get("relative_rect")
            # The rect should be adjusted to not go off screen
            assert rect.bottom <= 720


class TestInventoryIntegration:
    """Integration tests for inventory-related context menu actions."""

    @pytest.fixture
    def world(self):
        """Create a minimal World instance."""
        from yukkuri_game.engine.ecs import World
        from yukkuri_game.engine.event_bus import EventBus
        w = World()
        w.services.register(EventBus(), EventBus)
        return w

    def test_inventory_view_event_published(self, world):
        """Test that selecting 'Inventory' publishes InventoryViewRequestedEvent."""
        from yukkuri_game.engine.event_bus import EventBus
        from yukkuri_game.game.events import InventoryViewRequestedEvent
        
        event_bus = world.services.get(EventBus)
        captured_events = []
        event_bus.subscribe(InventoryViewRequestedEvent, lambda e: captured_events.append(e))
        
        # Simulate what HUD.on_context_menu_action does
        entity_id = 42
        position = (100, 100)
        event_bus.publish(InventoryViewRequestedEvent(entity_id, position))
        
        assert len(captured_events) == 1
        assert captured_events[0].entity_id == 42
        assert captured_events[0].position == (100, 100)

    def test_inventory_item_action_event(self, world):
        """Test InventoryItemActionEvent for drop action."""
        from yukkuri_game.engine.event_bus import EventBus
        from yukkuri_game.game.events import InventoryItemActionEvent
        
        event_bus = world.services.get(EventBus)
        captured_events = []
        event_bus.subscribe(InventoryItemActionEvent, lambda e: captured_events.append(e))
        
        event_bus.publish(InventoryItemActionEvent(
            entity_id=42,
            item_type_id="cookie",
            action="drop",
            quantity=1
        ))
        
        assert len(captured_events) == 1
        assert captured_events[0].entity_id == 42
        assert captured_events[0].item_type_id == "cookie"
        assert captured_events[0].action == "drop"
        assert captured_events[0].quantity == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
