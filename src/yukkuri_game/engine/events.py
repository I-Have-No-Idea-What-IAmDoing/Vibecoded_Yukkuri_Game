from dataclasses import dataclass
from .event_bus import Event

@dataclass(frozen=True)
class EntityDestroyedEvent(Event):
    """
    Event fired when an entity is destroyed.
    """
    entity_id: int
