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
class MemoryHeadline:
    """
    Represents a significant memory/event.
    """
    id: int
    timestamp: float
    importance: float # Absolute magnitude of the event
    sentiment: float  # Signed value (-100 to 100) representing opinion change
    event_type: str
    text: str = ""
    is_locked: bool = False

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

    # Base compatibility (cached from last calculation to avoid recomputing every frame)
    base_compatibility: float = 0.0

    # Memory Sums (Cached for O(1) Opinion Calculation)
    sum_core_sentiment: float = 0.0
    sum_trivial_sentiment: float = 0.0

    # Memory Buffers
    # We use lists to manually manage size and update sums
    trivial_buffer: List[MemoryHeadline] = field(default_factory=list)
    core_buffer: List[MemoryHeadline] = field(default_factory=list)

    # Constants
    TRIVIAL_MAX_LEN: int = 25
    CORE_MAX_LEN: int = 35

    def add_headline(self, headline: MemoryHeadline, threshold: float = 50.0):
        """Adds a headline to the appropriate buffer."""
        if headline.importance > threshold or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self._add_trivial_memory(headline)

    def _add_trivial_memory(self, headline: MemoryHeadline):
        """Adds a trivial memory, managing the buffer size and sum."""
        self.trivial_buffer.append(headline)
        self.sum_trivial_sentiment += headline.sentiment

        while len(self.trivial_buffer) > self.TRIVIAL_MAX_LEN:
            removed = self.trivial_buffer.pop(0)
            self.sum_trivial_sentiment -= removed.sentiment

    def _add_core_memory(self, headline: MemoryHeadline):
        """
        Adds to core buffer with Locking logic.
        If full, only overwrites unlocked memories or lower importance if allowed.
        """
        # Try to append if space available
        if len(self.core_buffer) < self.CORE_MAX_LEN:
            self.core_buffer.append(headline)
            self.sum_core_sentiment += headline.sentiment
            return

        # Buffer is full, try to find an unlocked victim (oldest)
        for i, mem in enumerate(self.core_buffer):
            if not mem.is_locked:
                removed = self.core_buffer.pop(i)
                self.sum_core_sentiment -= removed.sentiment

                self.core_buffer.append(headline)
                self.sum_core_sentiment += headline.sentiment
                return

        # If we are here, all memories are locked.
        # Check if the new memory is significantly more important than the *least important* locked memory.

        # Find the locked memory with the lowest importance
        victim_index = -1
        min_importance = float('inf')

        for i, mem in enumerate(self.core_buffer):
            if mem.importance < min_importance:
                min_importance = mem.importance
                victim_index = i

        # Check threshold
        if victim_index != -1:
            if headline.importance > (min_importance + 20.0):
                removed = self.core_buffer.pop(victim_index)
                self.sum_core_sentiment -= removed.sentiment

                self.core_buffer.append(headline)
                self.sum_core_sentiment += headline.sentiment

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

    def add_packet(self, packet: GossipPacket, max_length: int = 10):
        # Merge Duplicates: Check if we already have a packet for this target and event
        for i, existing in enumerate(self.priority_queue):
            if existing.target_id == packet.target_id and existing.event_type == packet.event_type:
                # Keep the one with higher value (importance)
                if packet.value > existing.value:
                    self.priority_queue[i] = packet
                # Sort again after modification
                self.priority_queue.sort(key=lambda x: x.value, reverse=True)
                return

        # If not found, add new
        self.priority_queue.append(packet)
        self.priority_queue.sort(key=lambda x: x.value, reverse=True)
        if len(self.priority_queue) > max_length:
            self.priority_queue = self.priority_queue[:max_length]

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
