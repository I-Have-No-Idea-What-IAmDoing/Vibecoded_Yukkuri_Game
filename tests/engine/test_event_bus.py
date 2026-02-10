"""
Tests for the EventBus.
"""

from yukkuri_game.engine.event_bus import Event, EventBus


class SampleEvent(Event):
    """Simple event for testing."""


def test_publish_calls_handlers_in_registration_order() -> None:
    """Handlers should run in the order they were registered."""
    bus = EventBus()
    calls: list[str] = []

    def handler_one(event: SampleEvent) -> None:
        calls.append("one")

    def handler_two(event: SampleEvent) -> None:
        calls.append("two")

    bus.subscribe(SampleEvent, handler_one)
    bus.subscribe(SampleEvent, handler_two)

    bus.publish(SampleEvent())

    assert calls == ["one", "two"]


def test_unsubscribe_removes_handler() -> None:
    """Unsubscribed handlers should not be called."""
    bus = EventBus()
    calls: list[str] = []

    def handler(event: SampleEvent) -> None:
        calls.append("called")

    bus.subscribe(SampleEvent, handler)
    bus.unsubscribe(SampleEvent, handler)

    bus.publish(SampleEvent())

    assert calls == []


def test_unsubscribe_missing_handler_is_safe() -> None:
    """Unsubscribing a handler that was never registered should not raise."""
    bus = EventBus()

    def handler(event: SampleEvent) -> None:
        pass

    bus.unsubscribe(SampleEvent, handler)


def test_exception_in_handler_does_not_stop_others() -> None:
    """Exceptions in one handler should not prevent others from running."""
    bus = EventBus()
    calls: list[str] = []

    def bad_handler(event: SampleEvent) -> None:
        raise RuntimeError("boom")

    def good_handler(event: SampleEvent) -> None:
        calls.append("ok")

    bus.subscribe(SampleEvent, bad_handler)
    bus.subscribe(SampleEvent, good_handler)

    bus.publish(SampleEvent())

    assert calls == ["ok"]


def test_clear_removes_all_subscribers() -> None:
    """clear() should remove all subscribers."""
    bus = EventBus()
    calls: list[str] = []

    def handler(event: SampleEvent) -> None:
        calls.append("called")

    bus.subscribe(SampleEvent, handler)
    bus.clear()
    bus.publish(SampleEvent())

    assert calls == []
