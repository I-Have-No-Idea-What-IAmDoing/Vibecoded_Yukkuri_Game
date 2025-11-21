from dataclasses import dataclass
from typing import Optional
from ..engine.event_bus import Event

@dataclass(frozen=True)
class EntitySelectedEvent(Event):
    """
    Event published when an entity is selected or deselected.

    Attributes:
        entity_id (int): The ID of the selected entity, or -1 if deselected.
    """
    entity_id: int # -1 if deselected

@dataclass(frozen=True)
class PlacementStartedEvent(Event):
    """
    Event published when placement mode is initiated.

    Attributes:
        type_id (str): The ID of the type being placed.
        cost (int): The cost of the item/yukkuri.
        entity_type (str): The category of the entity ("yukkuri" or "item").
    """
    type_id: str
    cost: int
    entity_type: str # "yukkuri" or "item"

@dataclass(frozen=True)
class GamePausedEvent(Event):
    """
    Event published when the game paused state changes.

    Attributes:
        paused (bool): True if the game is now paused, False otherwise.
    """
    paused: bool
