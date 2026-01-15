"""
Tests for the HudLayout class.
"""

import pytest
from unittest.mock import MagicMock, patch
from pygame_gui import UIManager
from pygame_gui.core.interfaces import IContainerLikeInterface
from yukkuri_game.game.ui.hud_layout import HudLayout


class TestHudLayout:
    @pytest.fixture
    def mock_ui_manager(self):
        manager = MagicMock(spec=UIManager)
        manager.ui_window_stack = MagicMock()  # Needs this attr
        return manager

    @pytest.fixture
    def layout(self, mock_ui_manager, monkeypatch):
        yukkuri_types = {
            "reimu": MagicMock(cost=100, name="Reimu"),
            "marisa": MagicMock(cost=100, name="Marisa"),
        }
        item_types = {"cookie": MagicMock(cost=10, name="Cookie", description="Tasty")}

        # Mock UI Elements
        # Ensure they have a kill method
        MockPanel = MagicMock(spec=IContainerLikeInterface)
        MockPanel.kill = MagicMock()
        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.UIPanel", lambda *args, **kwargs: MockPanel
        )

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

        # Patch UIScrollingContainer specifically because it validates container types
        MockScrollingContainer = MagicMock(spec=IContainerLikeInterface)
        MockScrollingContainer.set_scrollable_area_dimensions = MagicMock()

        monkeypatch.setattr(
            "yukkuri_game.game.ui.hud_layout.UIScrollingContainer",
            lambda *args, **kwargs: MockScrollingContainer,
        )

        layout = HudLayout(mock_ui_manager, 800, 600, yukkuri_types, item_types)
        return layout

    def test_initialization(self, layout):
        assert layout.width == 800
        assert layout.height == 600
        assert layout.top_panel is not None
        assert layout.bottom_panel is not None
        assert len(layout.buy_buttons) == 3  # 2 yukkuris + 1 item

    def test_resize(self, layout):
        layout.resize(1024, 768)
        assert layout.width == 1024
        assert layout.height == 768
        # Should have recreated panels
        assert layout.top_panel is not None
        assert layout.bottom_panel is not None

    def test_rebuild_ui(self, layout):
        layout.rebuild_ui()
        assert layout.top_panel is not None
        assert layout.bottom_panel is not None

    def test_clear_ui(self, layout):
        layout.clear_ui()
        assert layout.top_panel is None
        assert layout.bottom_panel is None
        assert len(layout.buy_buttons) == 0

    def test_create_selection_window(self, layout):
        with patch("yukkuri_game.game.ui.hud_layout.EntityInfoPanel") as MockInfoPanel:
            layout.create_selection_window(has_stats=True)
            assert layout.entity_info_panel is not None
            MockInfoPanel.return_value.show.assert_called_once()

    def test_create_debug_window(self, layout):
        layout.create_debug_window()
        assert layout.debug_window is not None
        assert layout.debug_text_box is not None

    def test_create_settings_window(self, layout):
        settings = {
            "audio": {"master_volume": 1.0, "bgm_volume": 0.8, "sfx_volume": 0.5},
            "window": {"width": 800, "height": 600, "fullscreen": False},
        }
        layout.create_settings_window(settings)
        assert layout.settings_window is not None
        assert "master_slider" in layout.settings_controls
        assert "save_btn" in layout.settings_controls

    def test_hover_tooltip(self, layout):
        # Setup rect size for mock
        mock_label = MagicMock()
        mock_label.rect.size = (200, 60)

        with patch(
            "yukkuri_game.game.ui.hud_layout.NonBlockingTextBox",
            return_value=mock_label,
        ):
            layout.update_hover_tooltip("Test Tooltip", (100, 100))
            assert layout.hover_tooltip_label is not None
