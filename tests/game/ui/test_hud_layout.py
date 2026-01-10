import pytest
from unittest.mock import MagicMock, patch
import pygame
import pygame_gui
from yukkuri_game.game.ui.hud_layout import HudLayout


class TestHudLayout:
    @pytest.fixture
    def mock_ui_manager(self, monkeypatch):
        # We need to mock pygame.display.get_surface because pygame_gui calls it
        monkeypatch.setattr(
            pygame.display, "get_surface", lambda: MagicMock(spec=pygame.Surface)
        )
        manager = MagicMock(spec=pygame_gui.UIManager)
        manager.ui_window_stack = MagicMock()
        return manager

    @pytest.fixture
    def layout(self, mock_ui_manager, monkeypatch):
        yukkuri_types = {
            "reimu": MagicMock(cost=100, name="Reimu"),
            "marisa": MagicMock(cost=100, name="Marisa"),
        }
        item_types = {"cookie": MagicMock(cost=10, name="Cookie", description="Tasty")}

        # Mock UI Elements
        monkeypatch.setattr("yukkuri_game.game.ui.hud_layout.UIPanel", MagicMock())
        monkeypatch.setattr("yukkuri_game.game.ui.hud_layout.UILabel", MagicMock())
        # Ensure UIButton returns unique mocks so dictionary keys are unique
        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.UIButton",
            MagicMock(side_effect=lambda *args, **kwargs: MagicMock()),
        )
        monkeypatch.setattr("yukkuri_game.game.ui.hud_layout.UIWindow", MagicMock())
        monkeypatch.setattr("yukkuri_game.game.ui.hud_layout.UITextBox", MagicMock())
        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.UIHorizontalSlider", MagicMock()
        )
        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.UIDropDownMenu", MagicMock()
        )
        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.NonBlockingTextBox", MagicMock()
        )

        layout = HudLayout(mock_ui_manager, 800, 600, yukkuri_types, item_types)
        return layout

    def test_initialization(self, layout):
        """Test that layout initializes components."""
        assert layout.top_panel is not None
        assert layout.bottom_panel is not None
        assert layout.money_label is not None
        assert layout.time_label is not None
        assert len(layout.buy_buttons) == 3  # 2 yukkuri + 1 item

    def test_resize(self, layout):
        """Test resizing the layout."""
        layout.rebuild_ui = MagicMock()
        layout.resize(1024, 768)

        assert layout.width == 1024
        assert layout.height == 768
        assert layout.rebuild_ui.called

    def test_rebuild_ui(self, layout):
        """Test rebuilding the UI."""
        # Mock methods called by rebuild_ui
        layout.clear_ui = MagicMock()
        layout._create_top_bar = MagicMock()
        layout._create_bottom_bar = MagicMock()
        layout.close_settings_window = MagicMock()
        layout.close_debug_window = MagicMock()
        layout.close_selection_window = MagicMock()

        layout.rebuild_ui()

        assert layout.clear_ui.called
        assert layout._create_top_bar.called
        assert layout._create_bottom_bar.called
        assert layout.close_settings_window.called

    def test_clear_ui(self, layout):
        """Test clearing the UI."""
        # Mock kill methods
        layout.top_panel.kill = MagicMock()
        layout.bottom_panel.kill = MagicMock()

        layout.clear_ui()

        assert layout.top_panel is None
        assert layout.bottom_panel is None
        assert len(layout.buy_buttons) == 0

    def test_create_selection_window(self, layout):
        """Test creating selection window."""
        with patch("yukkuri_game.game.ui.hud_layout.EntityInfoPanel"):
            layout.create_selection_window(has_stats=True)

            assert layout.entity_info_panel is not None
            layout.entity_info_panel.show.assert_called_once()

        # Test item selection (no stats actions)
        # Reset panel to force creation or just clear state
        layout.entity_info_panel = None
        with patch("yukkuri_game.game.ui.hud_layout.EntityInfoPanel"):
            layout.create_selection_window(has_stats=False)
            assert layout.entity_info_panel is not None
            layout.entity_info_panel.show.assert_called_once()

    def test_create_debug_window(self, layout):
        """Test creating debug window."""
        layout.create_debug_window()
        assert layout.debug_window is not None
        assert layout.debug_text_box is not None

        # Test toggling (closing via close_debug_window)
        layout.close_debug_window()
        assert layout.debug_window is None

    def test_create_settings_window(self, layout):
        """Test creating settings window."""
        settings = {
            "audio": {"master_volume": 0.5},
            "window": {"width": 800, "height": 600},
        }
        layout.create_settings_window(settings)

        assert layout.settings_window is not None
        assert "master_slider" in layout.settings_controls
        assert "resolution_dropdown" in layout.settings_controls

        layout.close_settings_window()
        assert layout.settings_window is None
        assert len(layout.settings_controls) == 0

    def test_hover_tooltip(self, layout):
        """Test hover tooltip creation and update."""
        # Initial state
        assert layout.hover_tooltip_label is None

        # Create
        layout.create_hover_tooltip()
        assert layout.hover_tooltip_label is not None
        assert layout.hover_tooltip_label.hide.called

        # Update with text
        # Set visible to False initially
        layout.hover_tooltip_label.visible = False
        # Mock rect size
        layout.hover_tooltip_label.rect.size = (200, 60)

        layout.update_hover_tooltip("Test Tooltip", (100, 100))
        assert layout.hover_tooltip_label.show.called

        # Update without text (hide)
        layout.hover_tooltip_label.visible = True
        layout.update_hover_tooltip("", (0, 0))
        assert layout.hover_tooltip_label.hide.called
