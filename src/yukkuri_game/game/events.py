from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class EntityDestroyedEvent:
    entity_id: int

@dataclass
class EntityDiedEvent:
    entity_id: int
    cause: str

@dataclass
class EntityGrewEvent:
    entity_id: int
    new_stage: str

@dataclass
class AnimationEvent:
    entity_id: int
    event_type: str # "started", "finished"
    animation_name: str

@dataclass
class PlacementStartedEvent:
    type_id: str
    cost: int
    entity_type: str # "yukkuri" or "item"

@dataclass
class PlacementRequestedEvent:
    x: float
    y: float
    type_id: str
    cost: int
    entity_type: str

@dataclass
class PlacementCancelledEvent:
    pass

@dataclass
class EntitySelectedEvent:
    entity_ids: List[int]

@dataclass
class LogMessageEvent:
    message: str
    color: Tuple[int, int, int] = (255, 255, 255)

@dataclass
class TogglePauseRequest:
    pass

@dataclass
class GamePausedEvent:
    paused: bool

@dataclass
class CycleSpeedRequest:
    pass

@dataclass
class ResolutionChangedEvent:
    width: int
    height: int
    fullscreen: bool

@dataclass
class TrainEntityRequest:
    entity_id: int

@dataclass
class EntityTrainedEvent:
    entity_id: int
    success: bool

@dataclass
class PunishEntityRequest:
    entity_id: int

@dataclass
class EntityPunishedEvent:
    entity_id: int

@dataclass
class SellEntityRequest:
    entity_id: int

@dataclass
class EntitySoldEvent:
    entity_id: int
    value: int

@dataclass
class CleanToolRequestedEvent:
    pass

@dataclass
class SocialInteractionEvent:
    initiator_id: int
    target_id: int
    interaction_type: str # "Talk", "Fight", "Dance"

@dataclass
class SaveGameRequest:
    filename: str = "savegame"

@dataclass
class LoadGameRequest:
    filename: str = "savegame"
