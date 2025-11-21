from typing import Dict, List, Type, Callable, Any, TypeVar, Generic
from dataclasses import dataclass

@dataclass(frozen=True)
class Event:
    """Base class for all events."""
    pass

E = TypeVar('E', bound=Event)
EventHandler = Callable[[E], None]

class EventBus:
    """
    A lightweight Event Bus to decouple producers from consumers.
    """
    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Subscribes a handler to a specific event type.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler) # type: ignore

    def unsubscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Unsubscribes a handler from a specific event type.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler) # type: ignore
            except ValueError:
                pass # Handler not found

    def publish(self, event: Event) -> None:
        """
        Publishes an event to all subscribers of its type.
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler(event)
