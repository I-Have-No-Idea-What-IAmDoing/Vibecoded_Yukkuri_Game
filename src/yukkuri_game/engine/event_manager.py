"""
Event Manager Module for Phase-Based Event System.
"""

from typing import Any
from collections.abc import Callable
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
        self._queues: dict[GamePhase, list[Event]] = {phase: [] for phase in GamePhase}

    def subscribe(
        self, event_type: type[Event], handler: Callable[[Any], None]
    ) -> None:
        """
        Register a handler for a specific event type.
        Handlers are called immediately when the event is published.
        """
        self.bus.subscribe(event_type, handler)

    def publish(self, event: Event) -> None:
        """
        Dispatch an event to all subscribers immediately.
        """
        self.bus.publish(event)

    def queue_event(self, event: Event, phase: GamePhase) -> None:
        """
        Store an event to be processed later during the specified game phase.
        """
        self._queues[phase].append(event)

    def process_phase(self, phase: GamePhase) -> None:
        """
        Dispatch all events queued for the given phase and clear the queue.
        """
        events = self._queues[phase]
        self._queues[
            phase
        ] = []  # Clear queue *before* processing to handle recursive events properly if needed

        for event in events:
            self.bus.publish(event)
