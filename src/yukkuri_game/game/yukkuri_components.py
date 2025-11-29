from dataclasses import dataclass, field
from typing import Set, Dict, Any, Optional, List, Deque
from collections import deque
from ..engine.ecs import Component

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
class EmotionalState(Component):
    """
    Component for the 2D Stress-Happiness Graph and derived emotions.
    """
    happiness: float = 0.0 # -100 to 100
    stress: float = 0.0    # 0 to 100
    anger: float = 0.0
    fear: float = 0.0

    def get_dominant_emotion(self, bravery: int = 0) -> str:
        """
        Derives the mood based on the 4 quadrants and Bravery.
        """
        is_happy = self.happiness >= 0
        is_stressed = self.stress >= 50

        if is_happy:
            if is_stressed:
                return "Excited/Manic"
            else:
                return "Content/Relaxed"
        else:
            if is_stressed:
                if bravery > 0:
                    return "Rage"
                else:
                    return "Terror"
            else:
                return "Depressed/Sulking"

@dataclass
class YukkuriStats(Component):
    """
    Component containing the statistics and state of a Yukkuri.
    Removed happiness/stress in favor of EmotionalState.
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
class Headline:
    """
    Represents a significant memory/event.
    """
    id: int
    timestamp: float
    importance: float
    event_type: str
    text: str = ""
    is_locked: bool = False

@dataclass
class MemoryBuffer:
    """
    Wrapper for Deque to handle custom add logic if needed.
    Kept for backward compatibility if logic was here, but actually logic is moved to RelationshipData.
    We can just use Deque directly or keep this class.
    Review suggested RelationshipData logic.
    """
    maxlen: int
    items: List['Headline'] = field(default_factory=list) # Using List but behaving like Deque or just use Deque

@dataclass
class Personality:
    """
    Component defining the personality of a Yukkuri.

    Attributes:
        traits (Set[str]): A set of trait IDs referencing TOML data.
        axis (PersonalityAxis): The current 4-Axis personality values.
        base_axis (PersonalityAxis): The natural resting point of the personality (Genetic + Traits).
        cached_overrides (Optional[Dict]): Cached AI overrides from traits.
    """
    traits: Set[str] = field(default_factory=set)
    axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    base_axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    cached_overrides: Optional[Dict[str, Any]] = None

@dataclass
class RelationshipData:
    """
    Stores data about a relationship with another entity.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    last_update: float = 0.0

    # Memory Buffers
    trivial_buffer: Deque[Headline] = field(default_factory=lambda: deque(maxlen=25))
    core_buffer: Deque[Headline] = field(default_factory=lambda: deque(maxlen=35))

    def add_headline(self, headline: Headline):
        """Adds a headline to the appropriate buffer."""
        if headline.importance > 50.0 or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self.trivial_buffer.append(headline)

    def _add_core_memory(self, headline: Headline):
        """
        Adds to core buffer with Locking logic.
        If full, only overwrites unlocked memories or lower importance if allowed.
        """
        if len(self.core_buffer) < self.core_buffer.maxlen:
            self.core_buffer.append(headline)
            return

        # Buffer is full, check for unlocked victim
        # Strategy: Remove oldest unlocked memory
        removed = False
        # Iterate to find first unlocked (oldest)
        for i, mem in enumerate(self.core_buffer):
            if not mem.is_locked:
                del self.core_buffer[i]
                self.core_buffer.append(headline)
                removed = True
                break

        if not removed:
            # All memories are locked.
            pass

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
class GossipPacket:
    target_id: int
    event_type: str
    value: float
    timestamp: float = 0.0

    def __lt__(self, other):
        return self.value < other.value

@dataclass
class GossipQueue(Component):
    priority_queue: List[GossipPacket] = field(default_factory=list)

    def add_packet(self, packet: GossipPacket):
        self.priority_queue.append(packet)
        self.priority_queue.sort(key=lambda x: x.value, reverse=True)
        if len(self.priority_queue) > 10: # Keep top 10
            self.priority_queue = self.priority_queue[:10]

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
