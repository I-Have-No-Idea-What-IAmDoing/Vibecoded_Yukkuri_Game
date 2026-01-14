"""
Yukkuri Components Module.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING
from ..engine.ecs import Component
from ..engine.types import EntityID

if TYPE_CHECKING:
    from ..config import StatsSettings


class FlightState(Enum):
    """
    Enum representing the flight state of a flying Yukkuri.
    """

    GROUNDED = 0  # Walking/Idle on ground
    TAKEOFF = 1  # Ascending (Altitude < Max)
    FLYING = 2  # Cruising (Altitude ~= Max)
    HOVERING = 3  # Stationary in air (Reduced Stamina Cost)
    LANDING = 4  # Descending (Altitude > 0)
    SWOOPING = 5  # Rapid attack descent (Altitude -> 0 temporarily)
    FALLING = 6  # Out of stamina/Stunned. Gravity applies full force.


@dataclass(slots=True)
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


@dataclass(slots=True)
class EmotionalState(Component):
    """
    Component for the 2D Stress-Happiness Graph and derived emotions.

    Attributes:
        happiness (float): -100 to 100.
        stress (float): 0 to 100.
    """

    happiness: float = 0.0  # -100 to 100
    stress: float = 0.0  # 0 to 100

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


@dataclass(slots=True)
class Needs(Component):
    """
    Component containing the physiological needs of a Yukkuri.

    Attributes:
        health (float): Current health.
        max_health (float): Maximum health.
        hunger (float): Current hunger (0-100).
        social (float): Current social satisfaction (0-100).
        energy (float): Current energy (0-100).
        cleanliness (float): Current cleanliness (0-100).
        bladder (float): Current bladder fullness (0-100).
        easiness (float): Overall happiness stat (0-100).
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
class YukkuriStats(Component):
    """
    Component containing the statistics of a Yukkuri.

    Attributes:
        name (str): Name of the Yukkuri.
        type_id (str): Type identifier.
        age (float): Current age in seconds.
        growth_stage (str): Current growth stage (e.g., "Baby", "Adult").
        badges (int): Number of badges earned.
        quality_score (float): Calculated quality score.
        discipline (float): Current discipline level (0-100).
        intelligence (float): Intelligence stat.
    """

    name: str
    type_id: str
    age: float = 0.0
    growth_stage: str = "Baby"
    badges: int = 0
    quality_score: float = 0.0
    discipline: float = 0.0
    intelligence: float = 1.0

    def get_intelligence(self, stats_config: "StatsSettings | None" = None) -> float:
        """
        Returns the intelligence stat.

        Args:
            stats_config (StatsSettings | None): Config for stats (unused now, kept for compatibility).
        """
        return self.intelligence

    def calculate_value(
        self,
        needs: "Needs | None" = None,
        emotional_state: "EmotionalState | None" = None,
        stats_config: "StatsSettings | None" = None,
    ) -> int:
        """
        Calculates the value of the Yukkuri based on stats and emotional state.

        Args:
            needs (Needs | None): The needs component.
            emotional_state (EmotionalState | None): The emotional state component.
            stats_config (StatsSettings | None): Config for stats value calculation.

        Returns:
            int: The calculated monetary value.
        """
        badge_val = 500
        health_penalty = 2.0
        age_bonus = 10.0

        if stats_config:
            badge_val = stats_config.badge_value
            health_penalty = stats_config.health_deficit_penalty
            age_bonus = stats_config.age_value_bonus

        score = 100.0
        if emotional_state:
            score += emotional_state.happiness + 100
        score += self.badges * badge_val

        if needs and needs.health < needs.max_health:
            score -= (needs.max_health - needs.health) * health_penalty

        score += int(self.age / 60) * age_bonus
        return int(score)


@dataclass(slots=True)
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
    importance: float  # Absolute magnitude of the event
    sentiment: float  # Signed value (-100 to 100) representing opinion change
    event_type: str
    text: str = ""
    is_locked: bool = False


@dataclass(slots=True)
class Personality:
    """
    Component defining the personality of a Yukkuri.

    Attributes:
        traits (Set[str]): A set of trait IDs referencing TOML data.
        axis (PersonalityAxis): The current 4-Axis personality values.
        base_axis (PersonalityAxis): The natural resting point of the personality (Genetic + Traits).
        cached_overrides (dict[str, Any] | None): Cached AI overrides from traits.
    """

    traits: set[str] = field(default_factory=set)
    axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    base_axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    cached_overrides: dict[str, Any] | None = None


@dataclass(slots=True)
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
    trivial_buffer: list[MemoryHeadline] = field(default_factory=list)
    core_buffer: list[MemoryHeadline] = field(default_factory=list)

    # Constants
    TRIVIAL_MAX_LEN: int = 25
    CORE_MAX_LEN: int = 35

    def add_headline(self, headline: MemoryHeadline, threshold: float = 50.0) -> None:
        """
        Adds a headline to the appropriate buffer based on its importance.

        Args:
            headline (MemoryHeadline): The memory event to add.
            threshold (float): Importance threshold for determining if a memory is 'core'.
                               Defaults to 50.0.
        """
        if headline.importance > threshold or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self._add_trivial_memory(headline)

    def __setstate__(self, state: dict[str, Any]) -> None:
        """
        Support for pickling: Ensure running sums are consistent when loading old data
        or data that wasn't saved with sums.

        Args:
            state (Dict[str, Any]): The pickled state dictionary.
        """
        for k, v in state.items():
            setattr(self, k, v)
        # Recalculate sums on load to ensure data integrity
        self.trivial_sentiment_sum = sum(m.sentiment for m in self.trivial_buffer)
        self.core_sentiment_sum = sum(m.sentiment for m in self.core_buffer)

    def _add_trivial_memory(self, headline: MemoryHeadline) -> None:
        """
        Adds a memory to the trivial buffer. Manages buffer size FIFO.

        Args:
            headline (MemoryHeadline): The memory to add.
        """
        if len(self.trivial_buffer) >= self.TRIVIAL_MAX_LEN:
            removed = self.trivial_buffer.pop(0)  # Remove oldest
            self.trivial_sentiment_sum -= removed.sentiment

        self.trivial_buffer.append(headline)
        self.trivial_sentiment_sum += headline.sentiment

    def _add_core_memory(self, headline: MemoryHeadline) -> None:
        """
        Adds to core buffer with locking and priority logic.
        If full, only overwrites unlocked memories or lower importance locked memories if significantly better.

        Args:
            headline (MemoryHeadline): The memory to add.
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
        min_locked_importance = float("inf")
        min_locked_index = -1

        for i, mem in enumerate(self.core_buffer):
            if not mem.is_locked:
                victim_index = i
                break  # Found the oldest unlocked, stop searching
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


@dataclass(slots=True)
class RelationshipRegistry:
    """
    Component tracking social relationships and family ties.

    Attributes:
        relationships (Dict[EntityID, RelationshipData]): Map of EntityID to RelationshipData.
        biological_parents (List[EntityID]): List of parent entity IDs.
        biological_children (List[EntityID]): List of children entity IDs.
        family_group_id (EntityID | None): ID of the family group they belong to.
        mate_id (EntityID | None): ID of the mate entity.
    """

    relationships: dict[EntityID, RelationshipData] = field(default_factory=dict)
    biological_parents: list[EntityID] = field(default_factory=list)
    biological_children: list[EntityID] = field(default_factory=list)
    family_group_id: EntityID | None = None
    mate_id: EntityID | None = None

    # Metadata for serialization remapping
    # Fields that contain EntityIDs that need remapping
    # _references: Set[str] = field(default_factory=lambda: {"relationships", "biological_parents", "biological_children", "family_group_id", "mate_id"}, repr=False, init=False)


@dataclass(slots=True)
class GossipPacket:
    """
    Represents a single piece of gossip or social information.
    """

    target_id: EntityID
    event_type: str
    value: float
    timestamp: float = 0.0

    def __lt__(self, other: "GossipPacket") -> bool:
        return self.value < other.value


@dataclass(slots=True)
class GossipQueue(Component):
    """
    Component managing a queue of gossip packets.
    """

    priority_queue: list[GossipPacket] = field(default_factory=list)

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
            if (
                existing.target_id == packet.target_id
                and existing.event_type == packet.event_type
            ):
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


@dataclass(slots=True)
class AIState:
    """
    Component maintaining the AI state of an entity.

    Attributes:
        current_action (str): The name of the current action.
        current_target_id (EntityID): The ID of the current target entity.
        path (list[Any] | None): The current navigation path.
        action_progress (float): Progress of the current action (0.0 to 1.0).
        state_data (dict[str, Any] | None): Arbitrary data for the current state.
        failed_targets (Set[EntityID]): Set of target IDs that failed recently.
        manual_override (bool): Whether AI is overridden by manual control.
    """

    current_action: str = "Idle"
    current_target_id: EntityID = EntityID(-1)
    path: list[Any] | None = None
    action_progress: float = 0.0
    state_data: dict[str, Any] | None = None
    failed_targets: set[EntityID] = field(default_factory=set)
    visible_entities: set[EntityID] = field(default_factory=set)
    manual_override: bool = False

    # Metadata for serialization remapping
    # _references: Set[str] = field(default_factory=lambda: {"current_target_id", "failed_targets"}, repr=False, init=False)


@dataclass(slots=True)
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


@dataclass(slots=True)
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


@dataclass(slots=True)
class Skills(Component):
    """
    Component holding all skills for an entity.

    Attributes:
        states (Dict[str, SkillState]): Map of SkillId to SkillState.
    """

    states: dict[str, SkillState] = field(default_factory=dict)


@dataclass(slots=True)
class Poop:
    """
    Tag component identifying an entity as Poop.
    """

    pass


@dataclass(slots=True)
class Dead:
    """
    Tag component for dead entities.
    """

    pass


@dataclass(slots=True)
class Flight(Component):
    """
    Component for flying Yukkuris.

    Attributes:
        altitude (float): Current visual height (0.0 to max_altitude).
        max_altitude (float): Target height for cruising.
        vertical_speed (float): Units per second for ascent/descent.
        stamina (float): Current flight stamina.
        max_stamina (float): Maximum flight stamina.
        fly_cost (float): Stamina drain/sec while moving in air.
        hover_cost (float): Stamina drain/sec while stationary.
        recovery_rate (float): Stamina gain/sec while GROUNDED.
        state (FlightState): Current flight state.
    """

    altitude: float = 0.0
    max_altitude: float = 60.0
    vertical_speed: float = 20.0

    stamina: float = 100.0
    max_stamina: float = 100.0

    fly_cost: float = 5.0
    hover_cost: float = 1.0
    recovery_rate: float = 10.0

    state: FlightState = FlightState.GROUNDED


@dataclass(slots=True)
class Predator(Component):
    """
    Component for predator Yukkuris that hunt other entities.

    Attributes:
        prey_tags (set[str]): Tags that identify valid prey (e.g., {"Prey", "Weak"}).
        prey_sense_radius (float): Detection range for prey.
        hunger_threshold (float): Hunger level at which hunting starts.
        aggression (float): Multiplier for attack decisions.
        dps (float): Damage per second when eating prey.
    """

    prey_tags: set[str] = field(default_factory=set)
    prey_sense_radius: float = 300.0
    hunger_threshold: float = 60.0
    aggression: float = 1.0
    dps: float = 20.0
