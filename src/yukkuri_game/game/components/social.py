"""
Social and AI components.
"""

import bisect
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
from typing import TYPE_CHECKING, Any
from ...engine.types import EntityID

if TYPE_CHECKING:
    pass

class GoalType(Enum):
    """
    High-level goal categories for Utility AI selection.
    """
    IDLE = 0
    WANDER = 1
    FORAGE = 2
    EAT = 3
    FLEE = 4
    HUNT = 5
    SOCIALIZE = 6
    SLEEP = 7
    PATROL = 8


@dataclass(slots=True)
class GoalComponent:
    """
    Component representing the current strategic goal selected by Utility AI.
    """
    goal_type: GoalType = GoalType.IDLE
    priority: float = 0.0
    target_id: EntityID | None = None
    stickiness: float = 10.0
    timestamp: float = 0.0


@dataclass(slots=True)
class TargetInfo:
    """
    Snapshot of a perceived entity in the Blackboard.
    """
    entity_id: EntityID
    position: tuple[float, float]
    distance: float
    relation: str = "Neutral"
    timestamp: float = 0.0
    detected_at: float = 0.0


@dataclass(slots=True)
class LastKnownPosition:
    """
    Memory record for an entity that has moved out of view.
    """
    position: tuple[float, float]
    timestamp: float = 0.0


@dataclass(slots=True)
class Blackboard:
    """
    Shared knowledge state for AI decision making.
    """
    visible_targets: dict[EntityID, TargetInfo] = field(default_factory=dict)
    short_term_memory: dict[EntityID, LastKnownPosition] = field(default_factory=dict)
    nearby_friends: int = 0
    nearby_enemies: int = 0
    nearby_prey: int = 0
    closest_threat_id: EntityID | None = None
    closest_food_id: EntityID | None = None


@dataclass(slots=True)
class ArchetypeConfig:
    """
    Configuration attached to entities to define specific AI behavior profiles.
    """
    archetype_id: str = "default"
    priorities: list[GoalType] = field(default_factory=lambda: [GoalType.IDLE])
    prey_tags: set[str] = field(default_factory=set)
    predator_tags: set[str] = field(default_factory=set)
    stamina_regen: float = 10.0
    personality_bias: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryHeadline:
    """
    Represents a significant memory or event in an entity's history.
    """
    id: int
    timestamp: float
    importance: float
    sentiment: float
    event_type: str
    text: str = ""
    is_locked: bool = False


@dataclass(slots=True)
class PersonalityAxis:
    """
    The 4-Axis integer system (-100 to +100) defining personality traits.
    """
    kindness: int = 0
    energy: int = 0
    bravery: int = 0
    greed: int = 0


@dataclass(slots=True)
class EmotionalState:
    """
    Component tracking emotional wellbeing.
    """
    happiness: float = 0.0
    stress: float = 0.0

    def get_dominant_emotion(self, bravery: int = 0) -> str:
        is_happy = self.happiness >= 0
        is_stressed = self.stress >= 50

        if is_happy:
            if is_stressed:
                return "Excited/Manic"
            else:
                return "Content/Relaxed"
        else:
            if is_stressed:
                return "Rage" if bravery > 0 else "Terror"
            else:
                return "Depressed/Sulking"


@dataclass(slots=True)
class Needs:
    """
    Component managing physiological needs.
    """
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0
    social: float = 50.0
    energy: float = 100.0
    cleanliness: float = 100.0
    bladder: float = 0.0
    easiness: float = 50.0


@dataclass(slots=True)
class Personality:
    """
    Component defining the personality profile.
    """
    traits: set[str] = field(default_factory=set)
    axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    base_axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    cached_overrides: dict[str, Any] | None = None


@dataclass(slots=True)
class RelationshipData:
    """
    Data structure managing the relationship with a specific entity.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    last_update: float = 0.0
    base_compatibility: float = 0.0
    trivial_sentiment_sum: float = 0.0
    core_sentiment_sum: float = 0.0
    trivial_buffer: deque[MemoryHeadline] = field(default_factory=deque)
    core_buffer: list[MemoryHeadline] = field(default_factory=list)
    TRIVIAL_MAX_LEN: int = 25
    CORE_MAX_LEN: int = 35

    def add_headline(self, headline: MemoryHeadline, threshold: float = 50.0) -> None:
        if headline.importance > threshold or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self._add_trivial_memory(headline)

    def __setstate__(self, state: dict[str, Any]) -> None:
        for k, v in state.items():
            setattr(self, k, v)
        self.trivial_sentiment_sum = sum(m.sentiment for m in self.trivial_buffer)
        self.core_sentiment_sum = sum(m.sentiment for m in self.core_buffer)

    def _add_trivial_memory(self, headline: MemoryHeadline) -> None:
        if len(self.trivial_buffer) >= self.TRIVIAL_MAX_LEN:
            removed = self.trivial_buffer.popleft()
            self.trivial_sentiment_sum -= removed.sentiment
        self.trivial_buffer.append(headline)
        self.trivial_sentiment_sum += headline.sentiment

    def _add_core_memory(self, headline: MemoryHeadline) -> None:
        if len(self.core_buffer) < self.CORE_MAX_LEN:
            self.core_buffer.append(headline)
            self.core_sentiment_sum += headline.sentiment
            return
        victim_index = -1
        min_locked_importance = float("inf")
        min_locked_index = -1
        for i, mem in enumerate(self.core_buffer):
            if not mem.is_locked:
                victim_index = i
                break
            else:
                if mem.importance < min_locked_importance:
                    min_locked_importance = mem.importance
                    min_locked_index = i
        if victim_index != -1:
            removed = self.core_buffer[victim_index]
            self.core_sentiment_sum -= removed.sentiment
            del self.core_buffer[victim_index]
            self.core_buffer.append(headline)
            self.core_sentiment_sum += headline.sentiment
            return
        if min_locked_index != -1:
            if headline.importance > (min_locked_importance + 20.0):
                removed = self.core_buffer[min_locked_index]
                self.core_sentiment_sum -= removed.sentiment
                del self.core_buffer[min_locked_index]
                self.core_buffer.append(headline)
                self.core_sentiment_sum += headline.sentiment


@dataclass(slots=True)
class RelationshipRegistry:
    """
    Component storing all social relationships for an entity.
    """
    relationships: dict[EntityID, RelationshipData] = field(default_factory=dict)
    biological_parents: list[EntityID] = field(default_factory=list)
    biological_children: list[EntityID] = field(default_factory=list)
    family_group_id: EntityID | None = None
    mate_id: EntityID | None = None


@dataclass(slots=True)
class GossipPacket:
    """
    Represents a unit of social information transmission.
    """
    target_id: EntityID
    event_type: str
    value: float
    timestamp: float = 0.0

    def __lt__(self, other: "GossipPacket") -> bool:
        return self.value < other.value


@dataclass(slots=True)
class GossipQueue:
    """
    Component managing a priority queue of outgoing gossip.
    """
    priority_queue: list[GossipPacket] = field(default_factory=list)

    def add_packet(self, packet: GossipPacket, max_length: int = 10) -> None:
        duplicate_index = -1
        for i, existing in enumerate(self.priority_queue):
            if (
                existing.target_id == packet.target_id
                and existing.event_type == packet.event_type
            ):
                duplicate_index = i
                break
        if duplicate_index != -1:
            if packet.value > self.priority_queue[duplicate_index].value:
                del self.priority_queue[duplicate_index]
                bisect.insort(self.priority_queue, packet, key=lambda x: -x.value)
            return
        if len(self.priority_queue) < max_length:
            bisect.insort(self.priority_queue, packet, key=lambda x: -x.value)
        else:
            if packet.value > self.priority_queue[-1].value:
                self.priority_queue.pop()
                bisect.insort(self.priority_queue, packet, key=lambda x: -x.value)


@dataclass(slots=True)
class AIState:
    """
    Component maintaining execution state for the AI system.
    """
    current_action: str = "Idle"
    current_target_id: EntityID = EntityID(-1)
    path: list[Any] | None = None
    action_progress: float = 0.0
    state_data: dict[str, Any] | None = None
    failed_targets: set[EntityID] = field(default_factory=set)
    visible_entities: set[EntityID] = field(default_factory=set)
    manual_override: bool = False
