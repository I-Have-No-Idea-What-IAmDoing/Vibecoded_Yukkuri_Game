from dataclasses import dataclass
from typing import Optional
from ..engine.event_bus import Event

@dataclass(frozen=True)
class EntitySelectedEvent(Event):
    """
    Event published when entities are selected or deselected.

    Attributes:
        entity_ids (list[int]): The IDs of the selected entities. Empty list if deselected.
    """
    entity_ids: list[int]

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
class PlacementRequestedEvent(Event):
    """
    Event published when the user requests to place an entity at a location.
    """
    x: float
    y: float
    type_id: str
    cost: int
    entity_type: str # "yukkuri" or "item"

@dataclass(frozen=True)
class PlacementCancelledEvent(Event):
    """
    Event published when placement mode is cancelled.
    """
    pass

@dataclass(frozen=True)
class GamePausedEvent(Event):
    """
    Event published when the game paused state changes.

    Attributes:
        paused (bool): True if the game is now paused, False otherwise.
    """
    paused: bool

@dataclass(frozen=True)
class TogglePauseRequest(Event):
    """
    Event published when a request to toggle the game pause state is made.
    """
    pass

@dataclass(frozen=True)
class CycleSpeedRequest(Event):
    """
    Event published when a request to cycle the game speed is made.
    """
    pass

@dataclass(frozen=True)
class TrainEntityRequest(Event):
    """
    Event published when a request to train an entity is made.

    Attributes:
        entity_id (int): The ID of the entity to train.
    """
    entity_id: int

@dataclass(frozen=True)
class SellEntityRequest(Event):
    """
    Event published when a request to sell an entity is made.

    Attributes:
        entity_id (int): The ID of the entity to sell.
    """
    entity_id: int

@dataclass
class CleanToolRequestedEvent:
    """
    Event triggered when the Clean tool is requested via UI.
    """
    pass

@dataclass(frozen=True)
class AnimationEvent(Event):
    """
    Event published when an animation triggers a specific event.

    Attributes:
        entity_id (int): The ID of the entity.
        event_name (str): The name of the trigger event (e.g., "step", "attack_hit").
        animation_name (str): The name of the animation playing.
        frame_index (int): The frame index where the event occurred.
    """
    entity_id: int
    event_name: str
    animation_name: str
    frame_index: int

@dataclass(frozen=True)
class NotificationEvent(Event):
    """
    Event published to display a global notification.

    Attributes:
        message (str): The message to display.
    """
    message: str
