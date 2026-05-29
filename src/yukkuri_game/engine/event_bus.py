"""
Event Bus Module.

This module provides the `EventBus`, a mechanism for decoupled communication between
systems via a publish-subscribe pattern. It promotes loose coupling by allowing
producers and consumers to interact without direct references to each other.
"""

from collections import deque
from collections.abc import Callable
import dataclasses
from dataclasses import dataclass
import time
from typing import Any, TypeVar

from loguru import logger


@dataclass(frozen=True)
class Event:
    """
    Base class for all system events.

    Events are immutable data containers carrying state change information.
    Subclasses must be decorated with `@dataclass(frozen=True)`.
    """


E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], None]


class EventBus:
    """
    A lightweight, type-safe Event Bus.

    Manages subscriptions and publication of events. Handlers execute synchronously
    in registration order, and exceptions are caught per handler to keep the bus running.

    Attributes:
        _subscribers: A mapping of Event types to a list of callable handlers.
    """

    def __init__(self) -> None:
        """Initializes a new, empty EventBus."""
        self._subscribers: dict[type[Event], list[Callable[[Any], None]]] = {}
        # Optional trace mode: logs every published event at DEBUG level and
        # records dead-letter events (no subscribers) as WARNINGs.
        self.trace: bool = False
        # Rolling history of the last 100 published event records.
        # Accessible via crash reporter for post-mortem analysis.
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=100)

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """
        Registers a callback function for a specific event type.

        Args:
            event_type (type[E]): The class of the event to listen for.
            handler (EventHandler[E]): The function to execute when the event is published.
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
            event_type (type[E]): The class of the event.
            handler (EventHandler[E]): The function to remove.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """
        Broadcasts an event to all registered subscribers.

        Handlers are executed synchronously in registration order. Exceptions are
        caught per handler and logged so that one failure does not block others.

        Args:
            event (Event): The event instance to broadcast.
        """
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        # Build representation of event payload
        payload_str = ""
        if dataclasses.is_dataclass(event):
            try:
                kv = []
                for f in dataclasses.fields(event):
                    kv.append(f"{f.name}={getattr(event, f.name)!r}")
                payload_str = f"({', '.join(kv)})"
            except Exception:  # noqa: BLE001
                payload_str = f"({repr(event)})"
        else:
            payload_str = f"({repr(event)})"

        event_record = {
            "timestamp": time.time(),
            "type": event_type.__name__,
            "payload": payload_str,
        }

        if self.trace:
            self.recent_events.append(event_record)
            if not handlers:
                logger.warning(
                    "Event {} published with no subscribers (dead letter)",
                    event_type.__name__,
                )
            else:
                logger.debug(
                    "Event {} → {} handler(s)",
                    event_type.__name__,
                    len(handlers),
                )
        elif handlers:
            # Always record to history, even without full trace.
            self.recent_events.append(event_record)

        for handler in list(handlers):
            try:
                handler(event)
            except Exception as e:
                logger.exception(
                    f"Error handling event {event_type.__name__}: {e}"
                )

    def clear(self) -> None:
        """
        Removes all subscribers, effectively resetting the bus.
        """
        self._subscribers.clear()
