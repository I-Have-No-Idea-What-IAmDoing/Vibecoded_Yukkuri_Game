import unittest
from unittest.mock import MagicMock, patch
import pygame
import pygame_gui
from yukkuri_game.game.ui.hud_layout import HudLayout

class TestHudLayout(unittest.TestCase):
    def setUp(self):
        self.mock_ui_manager = MagicMock(spec=pygame_gui.UIManager)
        self.width = 1280
        self.height = 720
        self.yukkuri_types = {"reimu": MagicMock(cost=100, name="Reimu")}
        self.item_types = {"cookie": MagicMock(cost=10, name="Cookie")}

        # Patch pygame_gui elements to avoid actual UI creation overhead/errors in headless env
        self.patcher_panel = patch('yukkuri_game.game.ui.hud_layout.UIPanel', spec=True)
        self.patcher_label = patch('yukkuri_game.game.ui.hud_layout.UILabel', spec=True)
        self.patcher_button = patch('yukkuri_game.game.ui.hud_layout.UIButton', spec=True)
        self.patcher_window = patch('yukkuri_game.game.ui.hud_layout.UIWindow', spec=True)
        self.patcher_textbox = patch('yukkuri_game.game.ui.hud_layout.UITextBox', spec=True)
        self.patcher_scroll = patch('yukkuri_game.game.ui.hud_layout.UIScrollingContainer', spec=True)

        self.MockPanel = self.patcher_panel.start()
        self.MockLabel = self.patcher_label.start()
        self.MockButton = self.patcher_button.start()
        self.MockWindow = self.patcher_window.start()
        self.MockTextBox = self.patcher_textbox.start()
        self.MockScroll = self.patcher_scroll.start()

        # Ensure side_effect creates a new mock for each call to differentiate buttons as dict keys
        self.MockButton.side_effect = lambda **kwargs: MagicMock()

    def tearDown(self):
        self.patcher_panel.stop()
        self.patcher_label.stop()
        self.patcher_button.stop()
        self.patcher_window.stop()
        self.patcher_textbox.stop()
        self.patcher_scroll.stop()

    def test_initialization(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height, self.yukkuri_types, self.item_types)

        # Verify top bar creation
        self.MockPanel.assert_any_call(
            relative_rect=pygame.Rect(0, 0, self.width, 50),
            manager=self.mock_ui_manager
        )

        # Verify labels and buttons in top bar
        self.MockLabel.assert_any_call(
            relative_rect=pygame.Rect(10, 10, 200, 30),
            text="Money: $0",
            manager=self.mock_ui_manager,
            container=layout.top_panel
        )

        # Verify bottom bar creation
        self.MockPanel.assert_any_call(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.mock_ui_manager
        )

        # Verify buy buttons creation
        # We expect 2 buttons (1 yukkuri, 1 item)
        # Note: If patched classes return the same mock instance, using it as a dictionary key
        # will overwrite previous entries. We need to ensure each call returns a new mock.
        self.assertEqual(len(layout.buy_buttons), 2)
        # 5 top buttons (pause, speed, save, load, settings) + 2 buy buttons + 1 clean button = 8
        self.assertEqual(self.MockButton.call_count, 5 + 2 + 1)

    def test_initialization_no_types(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height)
        self.assertEqual(len(layout.buy_buttons), 0)

    def test_create_selection_window(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height)

        # Test creating window with stats (e.g. yukkuri)
        layout.create_selection_window(has_stats=True)

        self.MockWindow.assert_called()
        self.MockTextBox.assert_called()
        self.assertIsNotNone(layout.selection_window)

        # Check buttons created
        # Sell and Train buttons should be created
        self.assertTrue(any(call[1]['text'] == "Sell" for call in self.MockButton.call_args_list))
        self.assertTrue(any(call[1]['text'] == "Train (+Badge)" for call in self.MockButton.call_args_list))

        # Test creating window without stats (e.g. item or multiple) - assuming currently only uses this bool
        # Code actually creates generic info label but skips buttons if no stats?
        # Let's check logic: if has_stats: create sell/train buttons.

        # Reset mocks
        self.MockButton.reset_mock()
        layout.create_selection_window(has_stats=False)

        # Should not create buttons
        self.assertFalse(any(call[1]['text'] == "Sell" for call in self.MockButton.call_args_list))

    def test_close_selection_window(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height)

        # Mock the window object
        mock_window_instance = MagicMock()
        layout.selection_window = mock_window_instance
        layout.info_label = MagicMock()
        layout.sell_btn = MagicMock()
        layout.train_btn = MagicMock()

        layout.close_selection_window()

        mock_window_instance.kill.assert_called_once()
        self.assertIsNone(layout.selection_window)
        self.assertIsNone(layout.info_label)
        self.assertIsNone(layout.sell_btn)
        self.assertIsNone(layout.train_btn)

    def test_create_debug_window(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height)

        layout.create_debug_window()

        self.MockWindow.assert_called()
        self.MockTextBox.assert_called()
        self.assertIsNotNone(layout.debug_window)
        self.assertIsNotNone(layout.debug_text_box)

        # Test re-creation kills old one
        old_window = layout.debug_window

        layout.create_debug_window()

        old_window.kill.assert_called()

    def test_close_debug_window(self):
        layout = HudLayout(self.mock_ui_manager, self.width, self.height)

        mock_window_instance = MagicMock()
        layout.debug_window = mock_window_instance
        layout.debug_text_box = MagicMock()

        layout.close_debug_window()

        mock_window_instance.kill.assert_called_once()
        self.assertIsNone(layout.debug_window)
        self.assertIsNone(layout.debug_text_box)

if __name__ == '__main__':
    unittest.main()
