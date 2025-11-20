import unittest
import pygame
from src.ui.interface import Interface
from src.core.game import Game
from src.systems.data_loader import DataLoader
from src.core.yukkurrium import Yukkurrium

# Mock classes to avoid full Pygame dependency in headless tests
class MockEvent:
    def __init__(self, type, pos=None, key=None):
        self.type = type
        self.pos = pos
        self.key = key

class TestInterface(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(data_dir='data')
        self.loader.load_all()
        self.game = Game(self.loader)
        # Setup game width needed for UI logic
        self.game.width = 1024
        self.interface = Interface(self.game)

        # Mock Yukkuri
        self.yukkuri = self.game.yukkurrium.spawn_yukkuri("Reimu", 0, 0)
        self.game.selected_yukkuri = self.yukkuri

    def test_sell_button_click(self):
        # UI Panel is at width - 250 = 1024 - 250 = 774
        # Sell Button is at 1024 - 240 = 784, y = 250, w=100, h=40

        # Click inside the button
        event = MockEvent(pygame.MOUSEBUTTONDOWN, pos=(790, 260))
        consumed = self.interface.handle_input(event)

        self.assertTrue(consumed)
        self.assertIsNone(self.game.selected_yukkuri) # Should be sold (removed from selection)
        self.assertNotIn(self.yukkuri, self.game.yukkurrium.yukkuris)

    def test_click_outside_ui(self):
        # Click in game world
        event = MockEvent(pygame.MOUSEBUTTONDOWN, pos=(100, 100))
        consumed = self.interface.handle_input(event)

        self.assertFalse(consumed) # Should let Game handle it

    def test_click_on_panel_but_miss_button(self):
        # Click on panel (x > 774) but not on button
        event = MockEvent(pygame.MOUSEBUTTONDOWN, pos=(900, 10))
        consumed = self.interface.handle_input(event)

        self.assertTrue(consumed) # Should consume to prevent click-through
        self.assertIsNotNone(self.game.selected_yukkuri) # Should NOT be sold

if __name__ == '__main__':
    unittest.main()
