"""
Module defining the Yukkuri-specific components for the game.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Set, List, Optional
from collections import deque
from ..engine.ecs import Component

# Yukkuri Specific Components

@dataclass
class Personality:
    """
    Component defining the personality of a Yukkuri using the Quad-Axis Model.

    Attributes:
        kindness (int): -100 (Gesu) to +100 (Nice).
        energy (int): -100 (Lazy) to +100 (Hyper).
        bravery (int): -100 (Coward) to +100 (Brave).
        greed (int): -100 (Generous) to +100 (Greedy).
        traits (Set[str]): A set of trait IDs referencing TOML data.
        cached_overrides (Optional[Dict[str, Any]]): Cached "effective overrides" for AI considerations.
    """
    kindness: int = 0
    energy: int = 0
    bravery: int = 0
    greed: int = 0
    traits: Set[str] = field(default_factory=set)
    cached_overrides: Optional[Dict[str, Any]] = None

@dataclass
class EmotionalState:
    """
    Component tracking the emotional state of a Yukkuri.

    Attributes:
        happiness (float): -100 (Depressed) to 100 (Ecstatic).
        stress (float): 0 (Calm) to 100 (Panic).
        current_mood (str): The derived mood state (e.g., "Relaxed", "Excited").
    """
    happiness: float = 0.0
    stress: float = 0.0
    current_mood: str = "Neutral"

@dataclass
class MemoryRecord:
    """
    Represents a "Headline" memory of a social interaction.

    Attributes:
        timestamp (float): The game time when the event occurred.
        actor_id (int): The ID of the entity that performed the action.
        action_type (str): The type of action.
        impact (float): The emotional impact value of the event.
        description (str): Text description of the event.
        is_locked (bool): If True, this memory is hard to overwrite (Core Memory).
    """
    timestamp: float
    actor_id: int
    action_type: str
    impact: float
    description: str = ""
    is_locked: bool = False

@dataclass
class RelationshipData:
    """
    Stores data about a relationship with another entity, using Split Buffers.

    Attributes:
        affinity (float): How much the entity likes the other (-100 to 100).
        trust (float): How much the entity trusts the other (0 to 100).
        fear (float): How much the entity fears the other (0 to 100).
        familiarity (float): How well the entity knows the other (0 to 100).

        trivial_events (deque): Ring buffer for small, everyday interactions (Size 25).
        core_memories (List[MemoryRecord]): List for major life events (Max Size 35).
                                            We use List instead of deque to handle Locking logic manually.

        last_update (float): Timestamp of the last decay update.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0

    trivial_events: deque = field(default_factory=lambda: deque(maxlen=25))
    core_memories: List[MemoryRecord] = field(default_factory=list) # Max 35, managed manually

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
class GossipPacket:
    """
    Represents a piece of gossip to be shared.
    """
    timestamp: float
    source_id: int # Who observed/generated this gossip
    subject_id: int # Who is the gossip about (the doer)
    target_id: int # Who was the target of the action
    action_type: str
    impact: float

    def __lt__(self, other):
        # We want Priority Queue to pop HIGHEST impact first.
        # Python heapq is a min-heap (pops smallest element).
        # So we want High Impact to be "smaller" than Low Impact.
        # Therefore: self < other if self.impact > other.impact
        return abs(self.impact) > abs(other.impact)

@dataclass
class GossipQueue:
    """
    Component holding gossip to share with others.
    """
    queue: List[GossipPacket] = field(default_factory=list)

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
        social (float): Social satisfaction level. Defaults to 50.0.
        energy (float): Energy level. Defaults to 100.0.
        cleanliness (float): Cleanliness level (0 = dirty, 100 = clean). Defaults to 100.0.
        age (float): Age in game seconds/ticks. Defaults to 0.0.
        growth_stage (str): Current growth stage ("Baby", "Child", "Adult"). Defaults to "Baby".
        badges (int): Number of badges earned. Defaults to 0.
        quality_score (float): Calculated quality score/value. Defaults to 0.0.
        discipline (float): Discipline level (0 = undisciplined, 100 = perfectly disciplined). Defaults to 0.0.

        happiness (float): Deprecated/Synced with EmotionalState.
        stress (float): Deprecated/Synced with EmotionalState.
    """
    name: str
    type_id: str
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0
    happiness: float = 50.0 # Synced for backward compatibility
    stress: float = 0.0 # Synced for backward compatibility
    social: float = 50.0
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
        manual_override (bool): If True, UtilitySelector will not change the current action.
    """
    current_action: str = "Idle"
    current_target_id: int = -1
    path: list[Any] | None = None
    action_progress: float = 0.0
    state_data: Dict[str, Any] | None = None
    failed_targets: Set[int] = field(default_factory=set)
    manual_override: bool = False

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
