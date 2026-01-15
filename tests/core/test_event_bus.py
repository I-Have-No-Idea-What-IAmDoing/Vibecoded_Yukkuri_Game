"""
Tests for the EventBus system.
"""

import unittest
from unittest.mock import Mock
from yukkuri_game.engine.event_bus import EventBus, Event
from dataclasses import dataclass


@dataclass(frozen=True)
class MockEvent(Event):
    """Event for testing purposes."""

    payload: str


class TestEventBus(unittest.TestCase):
    """
    Tests the EventBus functionality.
    """

    def setUp(self) -> None:
        """
        Sets up a fresh EventBus for each test.
        """
        self.event_bus = EventBus()

    def test_subscribe_and_publish(self) -> None:
        """
        Tests that subscribed handlers receive published events.
        """
        mock_handler = Mock()
        self.event_bus.subscribe(MockEvent, mock_handler)

        event = MockEvent("test")
        self.event_bus.publish(event)

        mock_handler.assert_called_once_with(event)

    def test_unsubscribe(self) -> None:
        """
        Tests that unsubscribed handlers do not receive events.
        """
        mock_handler = Mock()
        self.event_bus.subscribe(MockEvent, mock_handler)
        self.event_bus.unsubscribe(MockEvent, mock_handler)

        event = MockEvent("test")
        self.event_bus.publish(event)

        mock_handler.assert_not_called()

    def test_multiple_subscribers(self) -> None:
        """
        Tests that multiple handlers can subscribe to the same event type.
        """
        handler1 = Mock()
        handler2 = Mock()
        self.event_bus.subscribe(MockEvent, handler1)
        self.event_bus.subscribe(MockEvent, handler2)

        event = MockEvent("test")
        self.event_bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)


if __name__ == "__main__":
    unittest.main()
