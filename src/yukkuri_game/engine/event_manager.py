"""
Event Manager Module for Phase-Based Event System.
"""

from typing import Dict, List, Callable, Any, Type
from enum import Enum, auto
from .event_bus import EventBus, Event


class GamePhase(Enum):
    """
    Enum representing the different phases of the game loop.
    """

    PRE_UPDATE = auto()
    UPDATE = auto()
    POST_UPDATE = auto()
    RENDER = auto()


class EventManager:
    """
    Manages event dispatching and processing during specific game phases.
    Uses an underlying EventBus for actual subscription and publishing.

    Attributes:
        bus (EventBus): The main event bus.
        _queues (Dict[GamePhase, List[Event]]): Queues for events to be processed in specific phases.
    """

    def __init__(self) -> None:
        """Initializes the EventManager."""
        self.bus = EventBus()
        self._queues: Dict[GamePhase, List[Event]] = {phase: [] for phase in GamePhase}

    def subscribe(
        self, event_type: Type[Event], handler: Callable[[Any], None]
    ) -> None:
        """
        Subscribe to an event type (immediate dispatch).

        Args:
            event_type (Type[Event]): The type of event to subscribe to.
            handler (Callable[[Any], None]): The handler function.
        """
        self.bus.subscribe(event_type, handler)

    def publish(self, event: Event) -> None:
        """
        Publish an event immediately.

        Args:
            event (Event): The event to publish.
        """
        self.bus.publish(event)

    def queue_event(self, event: Event, phase: GamePhase) -> None:
        """
        Queue an event to be processed during a specific phase.

        Args:
            event (Event): The event to queue.
            phase (GamePhase): The phase in which to process the event.
        """
        self._queues[phase].append(event)

    def process_phase(self, phase: GamePhase) -> None:
        """
        Process all events queued for the given phase.

        Args:
            phase (GamePhase): The phase to process.
        """
        events = self._queues[phase]
        self._queues[
            phase
        ] = []  # Clear queue *before* processing to handle recursive events properly if needed

        for event in events:
            self.bus.publish(event)
