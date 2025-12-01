"""
Game Events Module.
"""
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class EntityDestroyedEvent:
    """
    Event triggered when an entity is destroyed.
    """
    entity_id: int

@dataclass
class EntityDiedEvent:
    """
    Event triggered when an entity dies (gameplay logic).
    """
    entity_id: int
    position: Tuple[float, float]
    cause: str = "Unknown"

@dataclass
class EntityGrewEvent:
    """
    Event triggered when an entity grows to a new stage (e.g., Baby -> Child).
    """
    entity_id: int
    new_stage: str
    position: Tuple[float, float]

@dataclass
class AnimationEvent:
    """
    Event triggered by animation system (e.g. keyframes or completion).
    """
    entity_id: int
    event_type: str # "started", "finished", or custom event name
    animation_name: str
    frame_index: int = -1

@dataclass
class PlacementStartedEvent:
    """
    Event triggered when the user starts the placement mode.
    """
    type_id: str
    cost: int
    entity_type: str # "yukkuri" or "item"

@dataclass
class PlacementRequestedEvent:
    """
    Event triggered when the user clicks to place an entity.
    """
    x: float
    y: float
    type_id: str
    cost: int
    entity_type: str

@dataclass
class PlacementCancelledEvent:
    """
    Event triggered when the user cancels placement mode.
    """
    pass

@dataclass
class EntitySelectedEvent:
    """
    Event triggered when entities are selected.
    """
    entity_ids: List[int]

@dataclass
class LogMessageEvent:
    """
    Event to log a message to the in-game console/log.
    """
    message: str
    color: Tuple[int, int, int] = (255, 255, 255)

@dataclass
class TogglePauseRequest:
    """
    Request to toggle game pause state.
    """
    pass

@dataclass
class GamePausedEvent:
    """
    Event indicating the game pause state has changed.
    """
    paused: bool

@dataclass
class CycleSpeedRequest:
    """
    Request to cycle through game speeds.
    """
    pass

@dataclass
class ResolutionChangedEvent:
    """
    Event indicating the window resolution has changed.
    """
    width: int
    height: int
    fullscreen: bool

@dataclass
class TrainEntityRequest:
    """
    Request to train a specific entity.
    """
    entity_id: int

@dataclass
class EntityTrainedEvent:
    """
    Event indicating an entity was trained.
    """
    entity_id: int
    position: Tuple[float, float]
    success: bool = True

@dataclass
class PunishEntityRequest:
    """
    Request to punish a specific entity.
    """
    entity_id: int

@dataclass
class EntityPunishedEvent:
    """
    Event indicating an entity was punished.
    """
    entity_id: int
    position: Tuple[float, float]

@dataclass
class SellEntityRequest:
    """
    Request to sell a specific entity.
    """
    entity_id: int

@dataclass
class EntitySoldEvent:
    """
    Event indicating an entity was sold.
    """
    entity_id: int
    value: int
    position: Tuple[float, float]

@dataclass
class CleanToolRequestedEvent:
    """
    Request to activate the cleaning tool.
    """
    pass

@dataclass
class SocialInteractionEvent:
    """
    Event indicating a social interaction occurred between two entities.
    """
    initiator_id: int
    target_id: int
    interaction_type: str # "Talk", "Fight", "Dance"

@dataclass
class SaveGameRequest:
    """
    Request to save the game.
    """
    filename: str = "savegame"

@dataclass
class LoadGameRequest:
    """
    Request to load a game.
    """
    filename: str = "savegame"
