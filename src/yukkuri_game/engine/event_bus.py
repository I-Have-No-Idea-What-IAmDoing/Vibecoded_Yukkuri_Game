"""
Event Bus Module.

This module provides the `EventBus`, a mechanism for decoupled communication between
systems via a publish-subscribe pattern. It promotes loose coupling by allowing
producers and consumers to interact without direct references to each other.
"""

from typing import Any, TypeVar
from collections.abc import Callable
from dataclasses import dataclass
from loguru import logger


@dataclass(frozen=True)
class Event:
    """
    Base class for all system events.

    Events are immutable data containers carrying state change information.
    Subclasses must be decorated with `@dataclass(frozen=True)`.
    """

    pass


E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], None]


class EventBus:
    """
    A lightweight, type-safe Event Bus.

    Manages subscriptions and publication of events.

    Attributes:
        _subscribers: A mapping of Event types to a list of callable handlers.
    """

    def __init__(self) -> None:
        """Initializes a new, empty EventBus."""
        self._subscribers: dict[type[Event], list[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """
        Registers a callback function for a specific event type.

        Args:
            event_type: The class of the event to listen for.
            handler: The function to execute when the event is published.
                     Must accept a single argument of type `event_type`.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        # Type-casting needed as Dict is invariant, but runtime behavior is safe.
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """
        Removes a previously registered callback.

        Safe to call even if the handler was never registered.

        Args:
            event_type: The class of the event.
            handler: The function to remove.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """
        Broadcasts an event to all registered subscribers.

        Handlers are executed synchronously in the order they were registered.
        Exceptions within handlers are caught and logged to prevent system crashes.

        Args:
            event: The event instance to broadcast.
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.exception(f"Error handling event {event_type.__name__}: {e}")

    def clear(self) -> None:
        """
        Removes all subscribers, effectively resetting the bus.
        """
        self._subscribers.clear()
