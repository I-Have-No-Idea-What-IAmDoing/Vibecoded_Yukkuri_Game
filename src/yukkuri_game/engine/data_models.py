from typing import Dict, List, Optional
import msgspec

class YukkuriType(msgspec.Struct):
    name: str
    image: str
    width: int
    height: int
    max_health: int
    base_happiness: int

class ItemType(msgspec.Struct):
    name: str
    image: str
    width: int
    height: int
    cost: int
    is_portable: bool
    nutrition: Optional[int] = None
    comfort: Optional[int] = None
    fun: Optional[int] = None

class ActionEffect(msgspec.Struct):
    type: str
    target_stat: Optional[str] = None
    consume: bool = False
    stat_changes: Dict[str, float] = {}

class ActionConsideration(msgspec.Struct):
    name: str
    input: str
    curve: str
    params: Dict[str, float] = {}

class AIAction(msgspec.Struct):
    weight: float
    effects: ActionEffect
    considerations: List[ActionConsideration] = []

# Root containers for the TOML structure
class YukkuriData(msgspec.Struct):
    yukkuris: Dict[str, YukkuriType]

class ItemData(msgspec.Struct):
    items: Dict[str, ItemType]

class AIData(msgspec.Struct):
    actions: Dict[str, AIAction]
