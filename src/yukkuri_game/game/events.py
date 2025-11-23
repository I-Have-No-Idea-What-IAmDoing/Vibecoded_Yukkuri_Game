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
class PunishEntityRequest(Event):
    """
    Event published when a request to punish an entity is made.

    Attributes:
        entity_id (int): The ID of the entity to punish.
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
class LogMessageEvent(Event):
    """
    Event published to display a message in the HUD log.

    Attributes:
        message (str): The message text.
        color (tuple[int, int, int]): The RGB color of the message text.
    """
    message: str
    color: tuple[int, int, int] = (255, 255, 255)

@dataclass(frozen=True)
class EntitySoldEvent(Event):
    """
    Event published when an entity is sold.

    Attributes:
        entity_id (int): The ID of the sold entity.
        value (int): The value the entity was sold for.
        position (tuple[float, float]): The position where the entity was.
    """
    entity_id: int
    value: int
    position: tuple[float, float]

@dataclass(frozen=True)
class EntityPunishedEvent(Event):
    """
    Event published when an entity is punished.

    Attributes:
        entity_id (int): The ID of the punished entity.
        position (tuple[float, float]): The position of the entity.
    """
    entity_id: int
    position: tuple[float, float]

@dataclass(frozen=True)
class ResolutionChangedEvent(Event):
    """
    Event published when the window resolution or fullscreen mode changes.

    Attributes:
        width (int): New width.
        height (int): New height.
        fullscreen (bool): New fullscreen state.
    """
    width: int
    height: int
    fullscreen: bool

@dataclass(frozen=True)
class EntityGrewEvent(Event):
    """
    Event published when an entity grows to a new stage.

    Attributes:
        entity_id (int): The ID of the growing entity.
        new_stage (str): The new growth stage.
        position (tuple[float, float]): The position of the entity.
    """
    entity_id: int
    new_stage: str
    position: tuple[float, float]

@dataclass(frozen=True)
class EntityTrainedEvent(Event):
    """
    Event published when an entity is trained.

    Attributes:
        entity_id (int): The ID of the trained entity.
        position (tuple[float, float]): The position of the entity.
    """
    entity_id: int
    position: tuple[float, float]

@dataclass(frozen=True)
class EntityDiedEvent(Event):
    """
    Event published when an entity dies.

    Attributes:
        entity_id (int): The ID of the died entity.
        position (tuple[float, float]): The position of the entity.
    """
    entity_id: int
    position: tuple[float, float]
