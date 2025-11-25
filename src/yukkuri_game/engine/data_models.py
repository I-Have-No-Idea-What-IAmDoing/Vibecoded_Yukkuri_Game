"""
Module defining data models for game configuration (TOML schema).
"""
from typing import Dict, List, Optional, TYPE_CHECKING
import msgspec

if TYPE_CHECKING:
    # Mypy doesn't play nice with msgspec extension types sometimes
    class YukkuriTypeBase: ...
    class ItemTypeBase: ...
    class ActionEffectBase: ...
    class ActionConsiderationBase: ...
    class AIActionBase: ...
    class AnimationDefinitionBase: ...
    class YukkuriDataBase: ...
    class ItemDataBase: ...
    class AIDataBase: ...
    class MovementVisualsBase: ...
    class VisualTuningBase: ...
    class GameTuningBase: ...
else:
    YukkuriTypeBase = msgspec.Struct
    ItemTypeBase = msgspec.Struct
    ActionEffectBase = msgspec.Struct
    ActionConsiderationBase = msgspec.Struct
    AIActionBase = msgspec.Struct
    AnimationDefinitionBase = msgspec.Struct
    YukkuriDataBase = msgspec.Struct
    ItemDataBase = msgspec.Struct
    AIDataBase = msgspec.Struct
    MovementVisualsBase = msgspec.Struct
    VisualTuningBase = msgspec.Struct
    GameTuningBase = msgspec.Struct


class AnimationDefinition(AnimationDefinitionBase):
    """
    Data model representing an animation sequence.
    """
    name: str
    frames: List[int]
    frame_duration: float
    loop: bool = True
    ping_pong: bool = False
    events: Dict[int, str] = msgspec.field(default_factory=dict)
    image: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class YukkuriType(YukkuriTypeBase):
    """
    Data model representing a type of Yukkuri.
    """
    name: str
    image: str
    width: int
    height: int
    max_health: int
    base_happiness: int
    cost: int = 100
    animations: Dict[str, AnimationDefinition] = {}

class ItemType(ItemTypeBase):
    """
    Data model representing a type of Item.
    """
    name: str
    image: str
    width: int
    height: int
    cost: int
    is_portable: bool
    nutrition: Optional[int] = None
    comfort: Optional[int] = None
    fun: Optional[int] = None

class ActionEffect(ActionEffectBase):
    """
    Data model representing the effects of an AI action.
    """
    type: str
    target_stat: Optional[str] = None
    consume: bool = False
    stat_changes: Dict[str, float] = {}

class ActionConsideration(ActionConsiderationBase):
    """
    Data model representing a consideration (input factor) for an AI action.
    """
    name: str
    input: str
    curve: str
    params: Dict[str, float] = {}

class AIAction(AIActionBase):
    """
    Data model representing an AI action definition.
    """
    weight: float
    effects: ActionEffect
    considerations: List[ActionConsideration] = []

# --- Game Tuning Data Models (from yukkuri_tuning.json) ---

class MovementVisuals(MovementVisualsBase):
    """Tuning for movement visual effects."""
    bob_height: float = 10.0
    bob_speed: float = 5.0

class VisualTuning(VisualTuningBase):
    """Container for all visual-related tuning."""
    movement: MovementVisuals

class GameTuning(GameTuningBase):
    """Root container for the main JSON tuning file."""
    visuals: VisualTuning

# --- Root containers for the TOML structure ---
class YukkuriData(YukkuriDataBase):
    """
    Root container for Yukkuri type definitions loaded from TOML.
    """
    yukkuris: Dict[str, YukkuriType]

class ItemData(ItemDataBase):
    """
    Root container for Item type definitions loaded from TOML.
    """
    items: Dict[str, ItemType]

class AIData(AIDataBase):
    """
    Root container for AI action definitions loaded from TOML.
    """
    actions: Dict[str, AIAction]
