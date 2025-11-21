from dataclasses import dataclass
from typing import Optional
from ..engine.event_bus import Event

@dataclass(frozen=True)
class EntitySelectedEvent(Event):
    """
    Event published when an entity is selected or deselected.
    """
    entity_id: int # -1 if deselected

@dataclass(frozen=True)
class PlacementStartedEvent(Event):
    """
    Event published when placement mode is initiated.
    """
    type_id: str
    cost: int
    entity_type: str # "yukkuri" or "item"

@dataclass(frozen=True)
class GamePausedEvent(Event):
    """
    Event published when the game paused state changes.
    """
    paused: bool
