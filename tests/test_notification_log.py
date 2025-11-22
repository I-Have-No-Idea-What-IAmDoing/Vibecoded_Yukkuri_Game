
import unittest
from unittest.mock import MagicMock, patch
import pygame_gui
import pygame
from src.yukkuri_game.game.ui.notification_log import NotificationLog

class TestNotificationLog(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.manager = MagicMock(spec=pygame_gui.UIManager)
        self.container = MagicMock()
        self.rect = pygame.Rect(0, 0, 100, 100)
        # Mock UITextBox to avoid actual UI creation issues in test
        with patch('src.yukkuri_game.game.ui.notification_log.UITextBox') as mock_textbox:
            self.log = NotificationLog(self.manager, self.container, self.rect)
            self.mock_textbox_instance = mock_textbox.return_value

    def test_add_message(self):
        self.log.add_message("Hello", "#FFFFFF")
        self.assertEqual(len(self.log.messages), 1)
        self.assertIn("<font color='#FFFFFF'>Hello</font>", self.log.messages[0])

        # Test max messages
        self.log.max_messages = 2
        self.log.add_message("World", "#000000")
        self.log.add_message("!", "#FF0000")

        self.assertEqual(len(self.log.messages), 2)
        self.assertIn("World", self.log.messages[0])
        self.assertIn("!", self.log.messages[1])

        # Check display update called
        self.mock_textbox_instance.set_text.assert_called()

if __name__ == '__main__':
    unittest.main()
