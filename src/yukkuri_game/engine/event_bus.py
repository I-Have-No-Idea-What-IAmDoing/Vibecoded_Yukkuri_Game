"""
Module defining the EventBus system.

The EventBus provides a mechanism for decoupled communication between different
parts of the application using a publish-subscribe pattern.
"""

from typing import Dict, List, Type, Callable, Any, TypeVar
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """
    Base class for all events.

    Events are simple data containers used to communicate between systems.
    Subclasses should be frozen dataclasses to ensure immutability.
    """

    pass


E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], None]


class EventBus:
    """
    A lightweight Event Bus to decouple producers from consumers.

    Allows systems to subscribe to and publish events without knowing about each other.

    Attributes:
        _subscribers (Dict[Type[Event], List[Callable[[Any], None]]]): A dictionary
            mapping event types to lists of handlers.
    """

    def __init__(self) -> None:
        """Initializes the EventBus."""
        self._subscribers: Dict[Type[Event], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Subscribes a handler to a specific event type.

        Args:
            event_type (Type[E]): The class of the event to subscribe to.
            handler (EventHandler[E]): The function to call when the event is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)  # type: ignore

    def unsubscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Unsubscribes a handler from a specific event type.

        Args:
            event_type (Type[E]): The class of the event to unsubscribe from.
            handler (EventHandler[E]): The handler function to remove.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)  # type: ignore
            except ValueError:
                pass  # Handler not found

    def publish(self, event: Event) -> None:
        """
        Publishes an event to all subscribers of its type.

        Args:
            event (Event): The event instance to publish.
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler(event)
