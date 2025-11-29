"""
Module defining the Yukkuri-specific components for the game.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Set, List, Optional
from ..engine.ecs import Component

# Yukkuri Specific Components

@dataclass
class Personality:
    """
    Component defining the personality of a Yukkuri.

    Attributes:
        traits (Set[str]): A set of trait IDs referencing TOML data.
        values (Dict[str, float]): A dictionary of personality values (e.g., {"compassion": 50.0}).
        mood (str): The current mood state (e.g., "NEUTRAL", "HAPPY").
        mood_score (float): The intensity of the current mood.
        cached_overrides (Optional[Dict[str, Any]]): Cached "effective overrides" for AI considerations.
    """
    traits: Set[str] = field(default_factory=set)
    values: Dict[str, float] = field(default_factory=dict)
    mood: str = "NEUTRAL"
    mood_score: float = 0.0
    cached_overrides: Optional[Dict[str, Any]] = None

@dataclass
class MemoryRecord:
    """
    Represents a single memory of a social interaction.

    Attributes:
        timestamp (float): The game time when the event occurred.
        actor_id (int): The ID of the entity that performed the action.
        action_type (str): The type of action (e.g., "Hit", "Greet").
        impact (float): The emotional impact value of the event.
        permanent (bool): Whether the memory is permanent (e.g., trauma). Defaults to False.
    """
    timestamp: float
    actor_id: int
    action_type: str
    impact: float
    permanent: bool = False

@dataclass
class RelationshipData:
    """
    Stores data about a relationship with another entity.

    Attributes:
        affinity (float): How much the entity likes the other (-100 to 100).
        trust (float): How much the entity trusts the other (0 to 100).
        fear (float): How much the entity fears the other (0 to 100).
        familiarity (float): How well the entity knows the other (0 to 100).
        memories (List[MemoryRecord]): A short list of recent impactful events.
        last_update (float): Timestamp of the last decay update.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    memories: List[MemoryRecord] = field(default_factory=list)
    last_update: float = 0.0

@dataclass
class RelationshipRegistry:
    """
    Component tracking social relationships and family ties.

    Attributes:
        relationships (Dict[int, RelationshipData]): A map of entity IDs to relationship data.
        biological_parents (List[int]): IDs of biological parents.
        biological_children (List[int]): IDs of biological children.
        family_group_id (Optional[int]): ID of the family group this entity belongs to.
        mate_id (Optional[int]): ID of the entity's mate.
    """
    relationships: Dict[int, RelationshipData] = field(default_factory=dict)
    biological_parents: List[int] = field(default_factory=list)
    biological_children: List[int] = field(default_factory=list)
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
        social (float): Social satisfaction level. Defaults to 50.0.
        stress (float): Stress level. Defaults to 0.0.
        energy (float): Energy level. Defaults to 100.0.
        cleanliness (float): Cleanliness level (0 = dirty, 100 = clean). Defaults to 100.0.
        age (float): Age in game seconds/ticks. Defaults to 0.0.
        growth_stage (str): Current growth stage ("Baby", "Child", "Adult"). Defaults to "Baby".
        badges (int): Number of badges earned. Defaults to 0.
        quality_score (float): Calculated quality score/value. Defaults to 0.0.
        discipline (float): Discipline level (0 = undisciplined, 100 = perfectly disciplined). Defaults to 0.0.
    """
    name: str
    type_id: str
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0
    happiness: float = 50.0
    social: float = 50.0
    stress: float = 0.0
    energy: float = 100.0
    cleanliness: float = 100.0
    age: float = 0.0
    growth_stage: str = "Baby"
    badges: int = 0
    quality_score: float = 0.0
    discipline: float = 0.0

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
    failed_targets: Set[int] = field(default_factory=set)

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
