"""
Yukkuri Components Module.
"""
from dataclasses import dataclass, field
from typing import Set, Dict, Any, Optional, List, Deque
from collections import deque
from ..engine.ecs import Component

@dataclass
class PersonalityAxis:
    """
    The 4-Axis integer system (-100 to +100) for personality.

    Attributes:
        kindness (int): Kindness vs Selfishness.
        energy (int): Energy vs Laziness.
        bravery (int): Bravery vs Cowardice.
        greed (int): Greed vs Generosity.
    """
    kindness: int = 0
    energy: int = 0
    bravery: int = 0
    greed: int = 0

@dataclass
class EmotionalState(Component):
    """
    Component for the 2D Stress-Happiness Graph and derived emotions.

    Attributes:
        happiness (float): -100 to 100.
        stress (float): 0 to 100.
    """
    happiness: float = 0.0 # -100 to 100
    stress: float = 0.0    # 0 to 100

    def get_dominant_emotion(self, bravery: int = 0) -> str:
        """
        Derives the mood based on the 4 quadrants and Bravery.

        Args:
            bravery (int): The bravery stat of the entity.

        Returns:
            str: The name of the dominant emotion.
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

    Attributes:
        name (str): Name of the Yukkuri.
        type_id (str): Type identifier.
        health (float): Current health.
        max_health (float): Maximum health.
        hunger (float): Current hunger (0-100).
        social (float): Current social satisfaction (0-100).
        energy (float): Current energy (0-100).
        cleanliness (float): Current cleanliness (0-100).
        age (float): Current age in seconds.
        growth_stage (str): Current growth stage (e.g., "Baby", "Adult").
        badges (int): Number of badges earned.
        quality_score (float): Calculated quality score.
        discipline (float): Current discipline level (0-100).
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

    def calculate_value(self, emotional_state: Optional["EmotionalState"] = None) -> int:
        """
        Calculates the value of the Yukkuri based on stats and emotional state.

        Args:
            emotional_state (Optional[EmotionalState]): The emotional state component.

        Returns:
            int: The calculated monetary value.
        """
        score = 100.0
        if emotional_state:
            score += (emotional_state.happiness + 100)
        score += self.badges * 500
        if self.health < self.max_health:
            score -= (self.max_health - self.health) * 2
        score += int(self.age / 60) * 10
        return int(score)

@dataclass
class MemoryHeadline:
    """
    Represents a significant memory/event.

    Attributes:
        id (int): Unique ID of the memory.
        timestamp (float): Time when the event occurred.
        importance (float): Absolute magnitude of the event's impact.
        sentiment (float): Signed value (-100 to 100) representing opinion change.
        event_type (str): Type of the event.
        text (str): Description of the event.
        is_locked (bool): Whether the memory is locked (cannot be forgotten).
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

    Attributes:
        affinity (float): Affection/Liking (-100 to 100).
        trust (float): Trust level (-100 to 100).
        fear (float): Fear level (0 to 100).
        familiarity (float): How well they know each other.
        last_update (float): Timestamp of last interaction.
        base_compatibility (float): Cached base compatibility score.
        trivial_sentiment_sum (float): Sum of sentiments in trivial buffer.
        core_sentiment_sum (float): Sum of sentiments in core buffer.
        trivial_buffer (List[MemoryHeadline]): List of trivial memories.
        core_buffer (List[MemoryHeadline]): List of core memories.
        TRIVIAL_MAX_LEN (int): Max size of trivial buffer.
        CORE_MAX_LEN (int): Max size of core buffer.
    """
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    last_update: float = 0.0

    # Base compatibility (cached from last calculation to avoid recomputing every frame)
    base_compatibility: float = 0.0

    # Running sums for sentiment
    trivial_sentiment_sum: float = 0.0
    core_sentiment_sum: float = 0.0

    # Memory Buffers
    # We use lists to manually manage size and update sums
    trivial_buffer: List[MemoryHeadline] = field(default_factory=list)
    core_buffer: List[MemoryHeadline] = field(default_factory=list)

    # Constants
    TRIVIAL_MAX_LEN: int = 25
    CORE_MAX_LEN: int = 35

    def add_headline(self, headline: MemoryHeadline, threshold: float = 50.0) -> None:
        """
        Adds a headline to the appropriate buffer.

        Args:
            headline (MemoryHeadline): The memory to add.
            threshold (float): Importance threshold for core memories.
        """
        if headline.importance > threshold or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self._add_trivial_memory(headline)

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """
        Support for pickling: Ensure running sums are consistent when loading old data
        or data that wasn't saved with sums.
        """
        self.__dict__.update(state)
        # Recalculate sums on load to ensure data integrity
        self.trivial_sentiment_sum = sum(m.sentiment for m in self.trivial_buffer)
        self.core_sentiment_sum = sum(m.sentiment for m in self.core_buffer)

    def _add_trivial_memory(self, headline: MemoryHeadline) -> None:
        if len(self.trivial_buffer) >= self.TRIVIAL_MAX_LEN:
             removed = self.trivial_buffer.pop(0) # Remove oldest
             self.trivial_sentiment_sum -= removed.sentiment

        self.trivial_buffer.append(headline)
        self.trivial_sentiment_sum += headline.sentiment

    def _add_core_memory(self, headline: MemoryHeadline) -> None:
        """
        Adds to core buffer with Locking logic.
        If full, only overwrites unlocked memories or lower importance if allowed.
        """
        # If space exists
        if len(self.core_buffer) < self.CORE_MAX_LEN:
            self.core_buffer.append(headline)
            self.core_sentiment_sum += headline.sentiment
            return

        # Buffer is full

        # 1. Try to find the oldest UNLOCKED memory.
        # We iterate from oldest (index 0) to newest.
        victim_index = -1

        # We also track the lowest importance LOCKED memory in case we need it later.
        min_locked_importance = float('inf')
        min_locked_index = -1

        for i, mem in enumerate(self.core_buffer):
            if not mem.is_locked:
                victim_index = i
                break # Found the oldest unlocked, stop searching
            else:
                if mem.importance < min_locked_importance:
                    min_locked_importance = mem.importance
                    min_locked_index = i

        if victim_index != -1:
            # Replace the unlocked memory
            # Deque remove by index is O(N), but necessary here if not popping ends.
            removed = self.core_buffer[victim_index]
            self.core_sentiment_sum -= removed.sentiment
            del self.core_buffer[victim_index]

            self.core_buffer.append(headline)
            self.core_sentiment_sum += headline.sentiment
            return

        # 2. All memories are locked. Check if new memory is significantly more important.
        # "Significantly higher magnitude" -> let's say +20 difference.
        if min_locked_index != -1:
             if headline.importance > (min_locked_importance + 20.0):
                removed = self.core_buffer[min_locked_index]
                self.core_sentiment_sum -= removed.sentiment
                del self.core_buffer[min_locked_index]

                self.core_buffer.append(headline)
                self.core_sentiment_sum += headline.sentiment

@dataclass
class RelationshipRegistry:
    """
    Component tracking social relationships and family ties.

    Attributes:
        relationships (Dict[int, RelationshipData]): Map of EntityID to RelationshipData.
        biological_parents (List[int]): List of parent entity IDs.
        biological_children (List[int]): List of children entity IDs.
        family_group_id (Optional[int]): ID of the family group they belong to.
        mate_id (Optional[int]): ID of the mate entity.
    """
    relationships: Dict[int, RelationshipData] = field(default_factory=dict)
    biological_parents: List[int] = field(default_factory=list)
    biological_children: List[int] = field(default_factory=list)
    family_group_id: Optional[int] = None
    mate_id: Optional[int] = None

    # Metadata for serialization remapping
    # Fields that contain EntityIDs that need remapping
    _references: Set[str] = field(default_factory=lambda: {"relationships", "biological_parents", "biological_children", "family_group_id", "mate_id"}, repr=False, init=False)

@dataclass
class GossipPacket:
    """
    Represents a single piece of gossip or social information.
    """
    target_id: int
    event_type: str
    value: float
    timestamp: float = 0.0

    def __lt__(self, other: "GossipPacket") -> bool:
        return self.value < other.value

@dataclass
class GossipQueue(Component):
    """
    Component managing a queue of gossip packets.
    """
    priority_queue: List[GossipPacket] = field(default_factory=list)

    # Metadata for serialization remapping
    # Note: GossipPacket contains target_id, so we might need deep inspection or just clear it on load?
    # Retaining gossip across saves is complex if we have to remap inside nested objects in a list.
    # For now, we will NOT remap GossipQueue and accept that IDs might be stale (or we clear it on load).
    # Ideally, we should iterate priority_queue.
    # _references: Set[str] = field(default_factory=lambda: {"priority_queue"}, repr=False, init=False)

    def add_packet(self, packet: GossipPacket, max_length: int = 10) -> None:
        """
        Adds a packet to the queue, merging duplicates and keeping the list sorted by value (descending).

        Args:
            packet (GossipPacket): The gossip packet to add.
            max_length (int): Maximum length of the queue.
        """
        # 1. Check for duplicates
        duplicate_index = -1
        for i, existing in enumerate(self.priority_queue):
            if existing.target_id == packet.target_id and existing.event_type == packet.event_type:
                duplicate_index = i
                break

        if duplicate_index != -1:
            existing = self.priority_queue[duplicate_index]
            if packet.value > existing.value:
                # Replace
                self.priority_queue[duplicate_index] = packet
                # Re-sort to maintain order
                self.priority_queue.sort(key=lambda x: x.value, reverse=True)
            return

        # 2. Add new packet if we have space or it's better than the worst
        if len(self.priority_queue) < max_length:
            self.priority_queue.append(packet)
            self.priority_queue.sort(key=lambda x: x.value, reverse=True)
        else:
            # Check if better than the last one (lowest priority)
            if packet.value > self.priority_queue[-1].value:
                self.priority_queue[-1] = packet
                self.priority_queue.sort(key=lambda x: x.value, reverse=True)

@dataclass
class AIState:
    """
    Component maintaining the AI state of an entity.

    Attributes:
        current_action (str): The name of the current action.
        current_target_id (int): The ID of the current target entity.
        path (Optional[List[Any]]): The current navigation path.
        action_progress (float): Progress of the current action (0.0 to 1.0).
        state_data (Optional[Dict[str, Any]]): Arbitrary data for the current state.
        failed_targets (Set[int]): Set of target IDs that failed recently.
        manual_override (bool): Whether AI is overridden by manual control.
    """
    current_action: str = "Idle"
    current_target_id: int = -1
    path: Optional[List[Any]] = None
    action_progress: float = 0.0
    state_data: Optional[Dict[str, Any]] = None
    failed_targets: Set[int] = field(default_factory=set)
    manual_override: bool = False

    # Metadata for serialization remapping
    _references: Set[str] = field(default_factory=lambda: {"current_target_id", "failed_targets"}, repr=False, init=False)

@dataclass
class ItemStats:
    """
    Component containing statistics for an Item.

    Attributes:
        name (str): Name of the item.
        type_id (str): Type identifier.
        cost (int): Cost in money.
        nutrition (float): Nutrition value.
        fun (float): Fun value.
        comfort (float): Comfort value.
        is_portable (bool): Whether it can be carried.
    """
    name: str
    type_id: str
    cost: int
    nutrition: float = 0.0
    fun: float = 0.0
    comfort: float = 0.0
    is_portable: bool = False

@dataclass
class SkillState:
    """
    Tracks the state of a single skill.

    Attributes:
        level (int): Current skill level.
        current_xp (float): XP accumulated towards the next level.
        passion (float): Multiplier for XP gain.
        last_used_gametime (float): Timestamp of last skill usage.
    """
    level: int = 0
    current_xp: float = 0.0
    passion: float = 1.0
    last_used_gametime: float = 0.0

@dataclass
class Skills(Component):
    """
    Component holding all skills for an entity.

    Attributes:
        states (Dict[str, SkillState]): Map of SkillId to SkillState.
    """
    states: Dict[str, SkillState] = field(default_factory=dict)

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
