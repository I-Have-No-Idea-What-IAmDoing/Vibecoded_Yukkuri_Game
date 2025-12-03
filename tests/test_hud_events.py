"""
Tests for HUD Events handling.
"""

import unittest
from unittest.mock import Mock
import pygame
import pygame_gui
from yukkuri_game.game.ui.hud_events import HudEvents
from yukkuri_game.game.events import PlacementStartedEvent
from yukkuri_game.game.services import EconomyService


class TestHudEvents(unittest.TestCase):
    """
    Tests the logic for processing HUD UI events (button clicks).
    """

    def setUp(self) -> None:
        """
        Sets up mocks for layout, game manager, and event bus.
        """
        self.layout = Mock()
        self.world = Mock()
        self.event_bus = Mock()
        self.on_error = Mock()

        # Mock EconomyService
        self.economy = Mock(spec=EconomyService)
        # Mock world.services.get(EconomyService) -> self.economy
        self.world.services.get.return_value = self.economy

        # Setup mock buttons
        self.layout.buy_buttons = {}

        self.reimu_btn = Mock()
        self.layout.buy_buttons[self.reimu_btn] = {
            "type_id": "reimu",
            "cost": 100,
            "category": "yukkuri",
            "name": "Reimu",
        }

        self.cookie_btn = Mock()
        self.layout.buy_buttons[self.cookie_btn] = {
            "type_id": "cookie",
            "cost": 10,
            "category": "item",
            "name": "Cookie",
        }

        self.hud_events = HudEvents(
            self.layout, self.world, self.event_bus, self.on_error
        )

    def test_buy_reimu_success(self) -> None:
        """
        Tests successful purchase of a Yukkuri.
        """
        # Setup
        self.economy.get_money.return_value = 1000
        event = Mock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = self.reimu_btn

        # Execute
        result = self.hud_events.process_event(event)

        # Verify
        self.assertTrue(result)
        self.event_bus.publish.assert_called_once()
        args, _ = self.event_bus.publish.call_args
        self.assertIsInstance(args[0], PlacementStartedEvent)
        self.assertEqual(args[0].type_id, "reimu")
        self.on_error.assert_not_called()

    def test_buy_reimu_not_enough_money(self) -> None:
        """
        Tests failed purchase of a Yukkuri due to insufficient funds.
        """
        # Setup
        self.economy.get_money.return_value = 50
        event = Mock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = self.reimu_btn

        # Execute
        result = self.hud_events.process_event(event)

        # Verify
        self.assertTrue(result)  # Still returns True as event was handled
        self.event_bus.publish.assert_not_called()
        self.on_error.assert_called_once_with(
            "Not enough money to buy Reimu! Needed: $100"
        )

    def test_buy_cookie_success(self) -> None:
        """
        Tests successful purchase of an item.
        """
        # Setup
        self.economy.get_money.return_value = 100
        event = Mock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = self.cookie_btn

        # Execute
        result = self.hud_events.process_event(event)

        # Verify
        self.assertTrue(result)
        self.event_bus.publish.assert_called_once()
        args, _ = self.event_bus.publish.call_args
        self.assertIsInstance(args[0], PlacementStartedEvent)
        self.assertEqual(args[0].type_id, "cookie")
        self.on_error.assert_not_called()

    def test_buy_cookie_not_enough_money(self) -> None:
        """
        Tests failed purchase of an item due to insufficient funds.
        """
        # Setup
        self.economy.get_money.return_value = 5
        event = Mock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = self.cookie_btn

        # Execute
        result = self.hud_events.process_event(event)

        # Verify
        self.assertTrue(result)
        self.event_bus.publish.assert_not_called()
        self.on_error.assert_called_once_with(
            "Not enough money to buy Cookie! Needed: $10"
        )


if __name__ == "__main__":
    unittest.main()
