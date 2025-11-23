from dataclasses import dataclass, field
from typing import Dict, Any, Set, List, Optional
from ..engine.ecs import Component

# Yukkuri Specific Components

@dataclass
class Personality:
    """
    Component defining the personality of a Yukkuri.
    """
    traits: Set[str] = field(default_factory=set)    # IDs referencing TOML data
    values: Dict[str, float] = field(default_factory=dict) # "compassion": 50.0
    mood: str = "NEUTRAL"        # Current Mood State
    mood_score: float = 0.0      # Intensity of the mood
    cached_overrides: Optional[Dict[str, Any]] = None # Cached "effective overrides"

@dataclass
class MemoryRecord:
    timestamp: float
    actor_id: int
    action_type: str
    impact: float
    permanent: bool = False # For trauma

@dataclass
class RelationshipData:
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    memories: List[MemoryRecord] = field(default_factory=list) # Short list of recent impactful events
    last_update: float = 0.0  # Timestamp of last decay update

@dataclass
class RelationshipRegistry:
    """
    Component tracking social relationships and family ties.
    """
    relationships: Dict[int, RelationshipData] = field(default_factory=dict)
    # Biological Lineage
    biological_parents: List[int] = field(default_factory=list)
    biological_children: List[int] = field(default_factory=list)
    # Social Group
    family_group_id: Optional[int] = None
    mate_id: Optional[int] = None

@dataclass
class YukkuriStats:
    """
    Component containing the statistics and state of a Yukkuri.

    Attributes:
        name (str): The name of the Yukkuri.
        type_id (str): The type identifier (e.g., "reimu").
        health (float): Current health. Defaults to 100.0.
        max_health (float): Maximum health. Defaults to 100.0.
        hunger (float): Hunger level (0 = full, 100 = starving). Defaults to 0.0.
        happiness (float): Happiness level (0 = sad, 100 = happy). Defaults to 50.0.
        cleanliness (float): Cleanliness level (0 = dirty, 100 = clean). Defaults to 100.0.
        age (float): Age in game seconds/ticks. Defaults to 0.0.
        growth_stage (str): Current growth stage ("Baby", "Child", "Adult"). Defaults to "Baby".
        badges (int): Number of badges earned. Defaults to 0.
        quality_score (float): Calculated quality score/value. Defaults to 0.0.
    """
    name: str
    type_id: str
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0      # 0 = full, 100 = starving
    happiness: float = 50.0  # 0 = sad, 100 = happy
    social: float = 50.0     # 0 = lonely, 100 = satisfied
    stress: float = 0.0      # 0 = calm, 100 = stressed
    energy: float = 100.0    # 0 = exhausted, 100 = full energy
    cleanliness: float = 100.0
    age: float = 0.0         # In game seconds/ticks
    growth_stage: str = "Baby" # Baby, Child, Adult
    badges: int = 0
    quality_score: float = 0.0
    discipline: float = 0.0  # 0 = undisciplined, 100 = perfectly disciplined

@dataclass
class AIState:
    """
    Component maintaining the AI state of an entity.

    Attributes:
        current_action (str): The name of the current action being performed. Defaults to "Idle".
        current_target_id (int): The ID of the target entity for the current action. Defaults to -1.
        path (list): A list of points representing the current movement path.
        action_progress (float): Progress counter for the current action. Defaults to 0.0.
        state_data (Dict[str, Any]): Additional data for the current state.
    """
    current_action: str = "Idle"
    current_target_id: int = -1
    path: list[Any] | None = None
    action_progress: float = 0.0
    state_data: Dict[str, Any] | None = None

@dataclass
class ItemStats:
    """
    Component containing statistics for an Item.

    Attributes:
        name (str): The name of the item.
        type_id (str): The type identifier.
        cost (int): The purchase cost of the item.
        nutrition (float): Nutritional value provided when consumed. Defaults to 0.0.
        fun (float): Fun value provided when interacted with. Defaults to 0.0.
        comfort (float): Comfort value provided. Defaults to 0.0.
        is_portable (bool): Whether the item can be carried. Defaults to False.
    """
    name: str
    type_id: str
    cost: int
    nutrition: float = 0.0
    fun: float = 0.0
    comfort: float = 0.0
    is_portable: bool = False

@dataclass
class Poop:
    """
    Tag component identifying an entity as Poop.
    """
    pass

class Dead:
    """
    Tag component for dead entities.
    """
    pass
