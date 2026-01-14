"""
Game Events Module.

All game events inherit from the engine's Event base class for consistency.
Events are frozen dataclasses to ensure immutability.
"""

from dataclasses import dataclass
from ..engine.event_bus import Event


@dataclass(frozen=True)
class EntityDiedEvent(Event):
    """
    Event triggered when an entity dies (gameplay logic).
    """

    entity_id: int
    position: tuple[float, float]
    cause: str = "Unknown"


@dataclass(frozen=True)
class EntityGrewEvent(Event):
    """
    Event triggered when an entity grows to a new stage (e.g., Baby -> Child).
    """

    entity_id: int
    new_stage: str
    position: tuple[float, float]


@dataclass(frozen=True)
class AnimationEvent(Event):
    """
    Event triggered by animation system (e.g. keyframes or completion).
    """

    entity_id: int
    event_type: str  # "started", "finished", or custom event name
    animation_name: str
    frame_index: int = -1


@dataclass(frozen=True)
class PlacementStartedEvent(Event):
    """
    Event triggered when the user starts the placement mode.
    """

    type_id: str
    cost: int
    entity_type: str  # "yukkuri" or "item"
    image_name: str = ""


@dataclass(frozen=True)
class PlacementRequestedEvent(Event):
    """
    Event triggered when the user clicks to place an entity.
    """

    x: float
    y: float
    type_id: str
    cost: int
    entity_type: str


@dataclass(frozen=True)
class PlacementCancelledEvent(Event):
    """
    Event triggered when the user cancels placement mode.
    """

    pass


@dataclass(frozen=True)
class EntitySelectedEvent(Event):
    """
    Event triggered when entities are selected.
    """

    entity_ids: tuple[int, ...]  # Changed from List to Tuple for frozen dataclass


@dataclass(frozen=True)
class LogMessageEvent(Event):
    """
    Event to log a message to the in-game console/log.
    """

    message: str
    color: tuple[int, int, int] = (255, 255, 255)


@dataclass(frozen=True)
class TogglePauseRequest(Event):
    """
    Request to toggle game pause state.
    """

    pass


@dataclass(frozen=True)
class GamePausedEvent(Event):
    """
    Event indicating the game pause state has changed.
    """

    paused: bool


@dataclass(frozen=True)
class CycleSpeedRequest(Event):
    """
    Request to cycle through game speeds.
    """

    pass


@dataclass(frozen=True)
class ResolutionChangedEvent(Event):
    """
    Event indicating the window resolution has changed.
    """

    width: int
    height: int
    fullscreen: bool


@dataclass(frozen=True)
class TrainEntityRequest(Event):
    """
    Request to train a specific entity.
    """

    entity_id: int


@dataclass(frozen=True)
class EntityTrainedEvent(Event):
    """
    Event indicating an entity was trained.
    """

    entity_id: int
    position: tuple[float, float]
    success: bool = True


@dataclass(frozen=True)
class PunishEntityRequest(Event):
    """
    Request to punish a specific entity.
    """

    entity_id: int


@dataclass(frozen=True)
class EntityPunishedEvent(Event):
    """
    Event indicating an entity was punished.
    """

    entity_id: int
    position: tuple[float, float]


@dataclass(frozen=True)
class SellEntityRequest(Event):
    """
    Request to sell a specific entity.
    """

    entity_id: int


@dataclass(frozen=True)
class EntitySoldEvent(Event):
    """
    Event indicating an entity was sold.
    """

    entity_id: int
    value: int
    position: tuple[float, float]


@dataclass(frozen=True)
class CleanToolRequestedEvent(Event):
    """
    Request to activate the cleaning tool.
    """

    pass


@dataclass(frozen=True)
class SocialInteractionEvent(Event):
    """
    Event indicating a social interaction occurred between two entities.
    """

    initiator_id: int
    target_id: int
    interaction_type: str  # "Talk", "Fight", "Dance"


@dataclass(frozen=True)
class SaveGameRequest(Event):
    """
    Request to save the game.
    """

    filename: str = "savegame"


@dataclass(frozen=True)
class LoadGameRequest(Event):
    """
    Request to load a game.
    """

    filename: str = "savegame"


@dataclass(frozen=True)
class LevelUpEvent(Event):
    """
    Event triggered when a Yukkuri levels up a skill.
    """

    entity_id: int
    skill_id: str
    new_level: int


@dataclass(frozen=True)
class ContextMenuRequestedEvent(Event):
    """
    Event triggered when a user requests a context menu on an entity.
    """

    entity_id: int
    position: tuple[int, int]


@dataclass(frozen=True)
class InventoryViewRequestedEvent(Event):
    """
    Event triggered when a user requests to view an entity's inventory.
    Decouples the context menu from the inventory panel.
    """

    entity_id: int
    position: tuple[int, int] | None = None  # Optional screen position for panel


@dataclass(frozen=True)
class InventoryItemActionEvent(Event):
    """
    Event triggered when a user requests an action on an inventory item.
    Supports drop, use, transfer, and other item operations.
    """

    entity_id: int
    item_type_id: str
    action: str  # "drop", "use", "transfer"
    quantity: int = 1

