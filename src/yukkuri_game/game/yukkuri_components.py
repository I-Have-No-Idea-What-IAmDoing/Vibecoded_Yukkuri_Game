"""
Module defining the Yukkuri-specific components for the game.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Set, List, Optional
from collections import deque
from enum import Enum
from ..engine.ecs import Component

# Yukkuri Specific Components

@dataclass
class PersonalityAxis:
    """
    The 4-Axis integer system (-100 to +100) for personality.
    """
    kindness: int = 0
    energy: int = 0
    bravery: int = 0
    greed: int = 0

@dataclass
class Personality:
    """
    Component defining the personality of a Yukkuri.

    Attributes:
        traits (Set[str]): A set of trait IDs referencing TOML data.
        axis (PersonalityAxis): The 4-Axis personality values.
    """
    traits: Set[str] = field(default_factory=set)
    axis: PersonalityAxis = field(default_factory=PersonalityAxis)

@dataclass
class Headline:
    """
    Represents a significant memory/event (The 'Headline' System).
    """
    id: int
    timestamp: float
    importance: float
    is_locked: bool
    text: str
    event_type: str = "GENERIC"

@dataclass
class MemoryBuffer:
    maxlen: int
    items: List['Headline'] = field(default_factory=list)

    def add(self, item: 'Headline'):
        self.items.append(item)
        if len(self.items) > self.maxlen:
            # 1. Try to remove oldest non-locked
            # We iterate to find the first (oldest) non-locked item
            # self.items[-1] is the new item, don't remove it yet
            for i in range(len(self.items) - 1):
                if not self.items[i].is_locked:
                    self.items.pop(i)
                    return

            # 2. If all locked, check importance
            # Find lowest importance among existing items (excluding new one)
            lowest_idx = -1
            lowest_val = float('inf')
            for i in range(len(self.items) - 1):
                if self.items[i].importance < lowest_val:
                    lowest_val = self.items[i].importance
                    lowest_idx = i

            # If new item is significantly more important (e.g. 2x)
            if lowest_idx != -1 and item.importance > lowest_val * 2.0:
                self.items.pop(lowest_idx)
            else:
                # Drop the new item
                self.items.pop()

@dataclass
class RelationshipData:
    """
    Stores data about a relationship with another entity.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0

    trivial_buffer: MemoryBuffer = field(default_factory=lambda: MemoryBuffer(maxlen=25))
    core_buffer: MemoryBuffer = field(default_factory=lambda: MemoryBuffer(maxlen=35))

    last_update: float = 0.0

@dataclass
class RelationshipRegistry:
    """
    Component tracking social relationships and family ties.
    """
    relationships: Dict[int, RelationshipData] = field(default_factory=dict)
    biological_parents: List[int] = field(default_factory=list)
    biological_children: List[int] = field(default_factory=list)
    family_group_id: Optional[int] = None
    mate_id: Optional[int] = None

@dataclass
class EmotionalState:
    """
    Component for the 2D Stress-Happiness Graph and derived emotions.
    """
    happiness: float = 0.0 # -100 to 100
    stress: float = 0.0    # 0 to 100
    anger: float = 0.0     # -100 to 100
    fear: float = 0.0      # -100 to 100

    def get_dominant_emotion(self) -> str:
        if self.happiness > 0:
            if self.stress > 50:
                return "EXCITED"
            else:
                return "HAPPY"
        else:
            if self.stress > 50:
                return "STRESSED"
            else:
                return "SAD"

@dataclass
class YukkuriStats:
    """
    Component containing the statistics and state of a Yukkuri.
    """
    name: str
    type_id: str
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0
    social: float = 50.0
    energy: float = 100.0
    cleanliness: float = 100.0
    age: float = 0.0
    growth_stage: str = "Baby"
    badges: int = 0
    quality_score: float = 0.0
    discipline: float = 0.0

@dataclass
class GossipPacket:
    target_id: int
    event_type: str
    value: float
    timestamp: float = 0.0

@dataclass
class GossipQueue:
    priority_queue: List[GossipPacket] = field(default_factory=list)

@dataclass
class AIState:
    """
    Component maintaining the AI state of an entity.
    """
    current_action: str = "Idle"
    current_target_id: int = -1
    path: Optional[List[Any]] = None
    action_progress: float = 0.0
    state_data: Optional[Dict[str, Any]] = None
    failed_targets: Set[int] = field(default_factory=set)
    manual_override: bool = False

@dataclass
class ItemStats:
    """
    Component containing statistics for an Item.
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

@dataclass
class Dead:
    """
    Tag component for dead entities.
    """
    pass
