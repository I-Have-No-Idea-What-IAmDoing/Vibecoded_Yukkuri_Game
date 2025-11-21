import unittest
from unittest.mock import Mock, MagicMock
from src.yukkuri_game.engine.event_bus import EventBus, Event
from dataclasses import dataclass

@dataclass(frozen=True)
class TestEvent(Event):
    payload: str

class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()

    def test_subscribe_and_publish(self):
        mock_handler = Mock()
        self.event_bus.subscribe(TestEvent, mock_handler)

        event = TestEvent("test")
        self.event_bus.publish(event)

        mock_handler.assert_called_once_with(event)

    def test_unsubscribe(self):
        mock_handler = Mock()
        self.event_bus.subscribe(TestEvent, mock_handler)
        self.event_bus.unsubscribe(TestEvent, mock_handler)

        event = TestEvent("test")
        self.event_bus.publish(event)

        mock_handler.assert_not_called()

    def test_multiple_subscribers(self):
        handler1 = Mock()
        handler2 = Mock()
        self.event_bus.subscribe(TestEvent, handler1)
        self.event_bus.subscribe(TestEvent, handler2)

        event = TestEvent("test")
        self.event_bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)

if __name__ == '__main__':
    unittest.main()
