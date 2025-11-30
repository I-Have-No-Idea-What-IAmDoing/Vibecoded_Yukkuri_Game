"""
Event Manager Module for Phase-Based Event System.
"""
from typing import Dict, List, Callable, Any, Type
from enum import Enum, auto
from dataclasses import dataclass
from .event_bus import EventBus, Event

class GamePhase(Enum):
    PRE_UPDATE = auto()
    UPDATE = auto()
    POST_UPDATE = auto()
    RENDER = auto()

class EventManager:
    """
    Manages event dispatching and processing during specific game phases.
    Uses an underlying EventBus for actual subscription and publishing.
    """
    def __init__(self):
        self.bus = EventBus()
        # Events can be queued to be processed at specific phases if needed.
        # But usually, events are immediate. The "Phase-Based" part implies
        # that *systems* run in phases and emit events, or events are *processed* in phases.
        # The proposal says: "Events are processed at specific points in the frame"
        # This implies a queue.

        self._queues: Dict[GamePhase, List[Event]] = {phase: [] for phase in GamePhase}
        self._immediate_bus = EventBus() # For events that need immediate handling

    def subscribe(self, event_type: Type[Event], handler: Callable[[Any], None]) -> None:
        """Subscribe to an event type (immediate dispatch)."""
        self._immediate_bus.subscribe(event_type, handler)

    def publish(self, event: Event) -> None:
        """Publish an event immediately."""
        self._immediate_bus.publish(event)

    def queue_event(self, event: Event, phase: GamePhase) -> None:
        """Queue an event to be processed during a specific phase."""
        self._queues[phase].append(event)

    def process_phase(self, phase: GamePhase) -> None:
        """Process all events queued for the given phase."""
        events = self._queues[phase]
        self._queues[phase] = [] # Clear queue *before* processing to handle recursive events properly if needed

        # Dispatch queued events.
        # Note: We need a way to subscribe to these queued events.
        # If we use the same bus, we can just publish them now.
        for event in events:
            self._immediate_bus.publish(event)
