from collections import defaultdict
from typing import Callable, Any, Dict, List

class EventBus:
    def __init__(self) -> None:
        self.listeners: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable[[Any], None]) -> None:
        """Subscribe a listener to an event type."""
        self.listeners[event_type].append(listener)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribed listeners."""
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                listener(data)

# Event Types (as constants for consistency)
AGENT_SPOKE: str = "agent_spoke"
NEED_CHANGED: str = "need_changed"
ITEM_USED: str = "item_used"
PLACEMENT_COMMITTED: str = "placement_committed"
