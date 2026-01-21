"""
Yukkuri Components Module.

Defines all ECS components specific to Yukkuri entities, covering stats,
personality, social relationships, AI state, and physical properties.

Key Features:
- **Flyweight Pattern**: Uses `YukkuriArchetype` to share static data.
- **Memory Optimization**: Utilizes `slots=True` for all dataclasses.
- **Headline System**: Implements memory management in `RelationshipData`.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING
from ..engine.ecs import Component
from ..engine.types import EntityID

if TYPE_CHECKING:
    from ..config import StatsSettings
    from ..engine.data_models import YukkuriType


# ==============================================================================
# FLYWEIGHT PATTERN - Shared Type Data
# ==============================================================================


@dataclass(slots=True)
class YukkuriArchetype:
    """
    Flyweight object holding static data shared by all Yukkuris of a specific type.

    Wraps the read-only TOML configuration to avoid per-entity data duplication.

    Attributes:
        type_data (Optional[YukkuriType]): The loaded configuration data.
    """

    type_data: "YukkuriType | None" = None


# Module-level Flyweight cache: type_id -> YukkuriArchetype
_ARCHETYPE_CACHE: dict[str, YukkuriArchetype] = {}


def register_archetype(type_id: str, type_data: "YukkuriType") -> None:
    """
    Registers a type configuration into the Flyweight cache.

    Args:
        type_id (str): The unique type identifier.
        type_data (YukkuriType): The configuration object to cache.
    """
    if type_id not in _ARCHETYPE_CACHE:
        _ARCHETYPE_CACHE[type_id] = YukkuriArchetype(type_data=type_data)


# ==============================================================================
# FLIGHT SYSTEM
# ==============================================================================


class FlightState(Enum):
    """
    Enumeration representing the current flight status of a Yukkuri.
    """

    GROUNDED = 0
    TAKEOFF = 1  # Ascending
    FLYING = 2
    HOVERING = 3  # Stationary (Reduced Stamina Cost)
    LANDING = 4  # Descending
    SWOOPING = 5  # Rapid attack descent
    FALLING = 6  # Out of stamina/Stunned


@dataclass(slots=True)
class PersonalityAxis:
    """
    The 4-Axis integer system (-100 to +100) defining personality traits.

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
    Component tracking emotional wellbeing via a 2D Stress-Happiness graph.

    Attributes:
        happiness (float): Range -100 to 100.
        stress (float): Range 0 to 100.
    """

    happiness: float = 0.0
    stress: float = 0.0

    def get_dominant_emotion(self, bravery: int = 0) -> str:
        """
        Determines the current dominant emotion based on stress/happiness quadrants.

        Args:
            bravery (int): The entity's bravery stat, influencing stress response.

        Returns:
            str: The name of the dominant emotion (e.g., "Excited", "Rage").
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
                return "Rage" if bravery > 0 else "Terror"
            else:
                return "Depressed/Sulking"


@dataclass(slots=True)
class Needs(Component):
    """
    Component managing physiological needs.

    Attributes:
        health (float): Current health points.
        max_health (float): Maximum health capacity.
        hunger (float): Hunger level (0-100). Higher is hungrier.
        social (float): Social satisfaction (0-100).
        energy (float): Energy level (0-100).
        cleanliness (float): Hygiene level (0-100).
        bladder (float): Bladder fullness (0-100).
        easiness (float): Overall happiness metric (0-100).
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
    Component containing general statistics and progression data.

    Attributes:
        name (str): Entity name.
        type_id (str): Type identifier key.
        age (float): Age in game seconds.
        growth_stage (str): Lifecycle stage (e.g., "Baby", "Adult").
        badges (int): Number of achievements/badges earned.
        quality_score (float): Calculated value/quality metric.
        discipline (float): Training level (0-100).
        intelligence (float): Intelligence multiplier.
    """

    name: str
    type_id: str
    age: float = 0.0
    growth_stage: str = "Baby"
    badges: int = 0
    quality_score: float = 0.0
    discipline: float = 0.0
    intelligence: float = 1.0
    agility: float = 1.0

    @property
    def archetype(self) -> "YukkuriArchetype | None":
        """
        Retrieves the shared archetype data from the global cache.

        Returns:
            Optional[YukkuriArchetype]: The cached archetype, or None if not registered.
        """
        return _ARCHETYPE_CACHE.get(self.type_id)

    def get_intelligence(self) -> float:
        """
        Retrieves the intelligence stat.

        Returns:
            float: The intelligence value.
        """
        return self.intelligence

    def calculate_value(
        self,
        needs: "Needs | None" = None,
        emotional_state: "EmotionalState | None" = None,
        stats_config: "StatsSettings | None" = None,
    ) -> int:
        """
        Calculates the monetary value of the Yukkuri.

        Value is derived from badges, emotional state, health, and age.

        Args:
            needs: Optional Needs component to factor in health penalty.
            emotional_state: Optional EmotionalState to factor in happiness.
            stats_config: Optional configuration settings for value weights.

        Returns:
            int: The calculated value.
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
    Represents a significant memory or event in an entity's history.

    Attributes:
        id (int): Unique memory identifier.
        timestamp (float): Game time when the event occurred.
        importance (float): Absolute magnitude of impact (0-100+).
        sentiment (float): Signed opinion change (-100 to 100).
        event_type (str): Category of the event.
        text (str): Readable description.
        is_locked (bool): If True, prevents this memory from being forgotten.
    """

    id: int
    timestamp: float
    importance: float
    sentiment: float
    event_type: str
    text: str = ""
    is_locked: bool = False


@dataclass(slots=True)
class Personality:
    """
    Component defining the personality profile.

    Attributes:
        traits (Set[str]): Set of active trait IDs.
        axis (PersonalityAxis): Current personality values.
        base_axis (PersonalityAxis): Genetic/Innate personality baseline.
        cached_overrides (Optional[Dict[str, Any]]): Cached AI behavior overrides.
    """

    traits: set[str] = field(default_factory=set)
    axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    base_axis: PersonalityAxis = field(default_factory=PersonalityAxis)
    cached_overrides: dict[str, Any] | None = None


@dataclass(slots=True)
class RelationshipData:
    """
    Data structure managing the relationship with a specific entity.
    Implements the "Headline System" for memory retention and sentiment calculation.

    Attributes:
        affinity (float): Net affection/liking (-100 to 100).
        trust (float): Reliability perception (-100 to 100).
        fear (float): Thread perception (0 to 100).
        familiarity (float): Knowledge level (0 to 100).
        last_update (float): Timestamp of last interaction.
        base_compatibility (float): Cached personality compatibility score.
        trivial_sentiment_sum (float): Cached sum of trivial memory sentiments.
        core_sentiment_sum (float): Cached sum of core memory sentiments.
        trivial_buffer (List[MemoryHeadline]): FIFO buffer for minor events.
        core_buffer (List[MemoryHeadline]): Priority buffer for major events.
        TRIVIAL_MAX_LEN (int): Capacity of trivial buffer.
        CORE_MAX_LEN (int): Capacity of core buffer.
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
    trivial_buffer: list[MemoryHeadline] = field(default_factory=list)
    core_buffer: list[MemoryHeadline] = field(default_factory=list)

    # Constants
    TRIVIAL_MAX_LEN: int = 25
    CORE_MAX_LEN: int = 35

    def add_headline(self, headline: MemoryHeadline, threshold: float = 50.0) -> None:
        """
        Adds a memory to the appropriate buffer based on importance.

        Args:
            headline (MemoryHeadline): The new memory.
            threshold (float): Importance threshold for Core vs Trivial.
        """
        if headline.importance > threshold or headline.is_locked:
            self._add_core_memory(headline)
        else:
            self._add_trivial_memory(headline)

    def __setstate__(self, state: dict[str, Any]) -> None:
        """
        Restores state from pickle, recalculating sentiment sums to ensure consistency.
        """
        for k, v in state.items():
            setattr(self, k, v)
        # Recalculate sums to ensure data integrity.
        self.trivial_sentiment_sum = sum(m.sentiment for m in self.trivial_buffer)
        self.core_sentiment_sum = sum(m.sentiment for m in self.core_buffer)

    def _add_trivial_memory(self, headline: MemoryHeadline) -> None:
        """Adds to trivial buffer (FIFO)."""
        if len(self.trivial_buffer) >= self.TRIVIAL_MAX_LEN:
            removed = self.trivial_buffer.pop(0)  # Remove oldest
            self.trivial_sentiment_sum -= removed.sentiment

        self.trivial_buffer.append(headline)
        self.trivial_sentiment_sum += headline.sentiment

    def _add_core_memory(self, headline: MemoryHeadline) -> None:
        """
        Adds to core buffer with priority logic.
        Evicts the least valuable memory if full (Oldest Unlocked > Lowest Importance Locked).
        """
        if len(self.core_buffer) < self.CORE_MAX_LEN:
            self.core_buffer.append(headline)
            self.core_sentiment_sum += headline.sentiment
            return

        # Buffer is full - Find victim
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

        # All items are locked: replace lowest importance only if significantly better
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

    Attributes:
        relationships (Dict[EntityID, RelationshipData]): Map of target entity IDs to relationship data.
        biological_parents (List[EntityID]): IDs of biological parents.
        biological_children (List[EntityID]): IDs of biological children.
        family_group_id (Optional[EntityID]): Shared family group identifier.
        mate_id (Optional[EntityID]): ID of current mate.
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

    Attributes:
        target_id (EntityID): The subject of the gossip.
        event_type (str): The nature of the event (e.g., "Attack").
        value (float): Informational value/priority.
        timestamp (float): Time of the event.
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
    Component managing a priority queue of outgoing gossip.

    Attributes:
        priority_queue (List[GossipPacket]): Sorted list of gossip packets.
    """

    priority_queue: list[GossipPacket] = field(default_factory=list)

    def add_packet(self, packet: GossipPacket, max_length: int = 10) -> None:
        """
        Adds a packet to the queue, maintaining sort order and handling duplicates.

        Args:
            packet (GossipPacket): The packet to add.
            max_length (int): Max queue size.
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

        # 2. Handle duplicate: update if new packet has higher value
        if duplicate_index != -1:
            if packet.value > self.priority_queue[duplicate_index].value:
                self.priority_queue[duplicate_index] = packet
                self.priority_queue.sort(key=lambda x: x.value, reverse=True)
            return

        # 3. Add or replace lowest
        if len(self.priority_queue) < max_length:
            self.priority_queue.append(packet)
            self.priority_queue.sort(key=lambda x: x.value, reverse=True)
        else:
            if packet.value > self.priority_queue[-1].value:
                self.priority_queue[-1] = packet
                self.priority_queue.sort(key=lambda x: x.value, reverse=True)


@dataclass(slots=True)
class AIState:
    """
    Component maintaining execution state for the AI system.

    Attributes:
        current_action (str): Debug name of current activity.
        current_target_id (EntityID): Entity being targeted.
        path (Optional[List[Any]]): Navigation path cache.
        action_progress (float): Completion percentage (0.0-1.0).
        state_data (Optional[Dict]): Scratchpad for action-specific data.
        failed_targets (Set[EntityID]): Blacklist of recently failed targets.
        manual_override (bool): If True, AI logic is suspended.
    """

    current_action: str = "Idle"
    current_target_id: EntityID = EntityID(-1)
    path: list[Any] | None = None
    action_progress: float = 0.0
    state_data: dict[str, Any] | None = None
    failed_targets: set[EntityID] = field(default_factory=set)
    visible_entities: set[EntityID] = field(default_factory=set)
    manual_override: bool = False


@dataclass(slots=True)
class ItemStats:
    """
    Component defining the properties of an Item entity.

    Attributes:
        name (str): Display name.
        type_id (str): Type key.
        cost (int): Monetary value.
        nutrition (float): Hunger reduction value.
        fun (float): Entertainment value.
        comfort (float): Stress reduction value.
        is_portable (bool): Can be picked up.
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
    Data container for a single skill instance.

    Attributes:
        level (int): Proficiency tier.
        current_xp (float): Progress to next level.
        passion (float): XP gain multiplier (Talent).
        last_used_gametime (float): Timestamp of last activation.
    """

    level: int = 0
    current_xp: float = 0.0
    passion: float = 1.0
    last_used_gametime: float = 0.0


@dataclass(slots=True)
class Skills(Component):
    """
    Component holding the collection of skills for an entity.

    Attributes:
        states (Dict[str, SkillState]): Map of Skill ID to SkillState.
    """

    states: dict[str, SkillState] = field(default_factory=dict)


@dataclass(slots=True)
class Poop:
    """Tag component identifying identifying the entity as excrement."""

    pass


@dataclass(slots=True)
class Dead:
    """Tag component identifying that the entity is deceased."""

    pass


@dataclass(slots=True)
class Flight(Component):
    """
    Component handling flight mechanics and stamina.

    Attributes:
        altitude (float): Current height above ground.
        max_altitude (float): Ceiling height.
        vertical_speed (float): Ascent/Descent rate.
        stamina (float): Current flight energy.
        max_stamina (float): Max flight energy.
        fly_cost (float): Stamina drain per second when moving.
        hover_cost (float): Stamina drain per second when static.
        recovery_rate (float): Stamina regen per second when grounded.
        state (FlightState): Current flight mode.
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
    Component for predator behavior logic.

    Attributes:
        prey_tags (Set[str]): Tags defining valid food sources.
        prey_sense_radius (float): Detection range for prey.
        hunger_threshold (float): Hunger level triggering hunt mode.
        aggression (float): Aggression multiplier.
        dps (float): Damage per second during feeding.
    """

    prey_tags: set[str] = field(default_factory=set)
    prey_sense_radius: float = 300.0
    hunger_threshold: float = 60.0
    aggression: float = 1.0
    dps: float = 20.0


# --- Unified AI Architecture Components ---


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
class GoalComponent(Component):
    """
    Component representing the current strategic goal selected by Utility AI.

    Attributes:
        goal_type (GoalType): The active goal category.
        priority (float): Utility score (importance).
        target_id (Optional[EntityID]): Specific target associated with goal.
        stickiness (float): Score bonus to maintain current goal (hysteresis).
        timestamp (float): Time when the goal was adopted.
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

    Attributes:
        entity_id (EntityID): The observed entity.
        position (Tuple[float, float]): Last observed location.
        distance (float): Distance from observer.
        relation (str): Semantic relationship ("Friend", "Enemy", etc.).
        timestamp (float): Time of observation.
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

    Attributes:
        position (Tuple[float, float]): Last valid position.
        timestamp (float): Time when contact was lost.
    """

    position: tuple[float, float]
    timestamp: float = 0.0


@dataclass(slots=True)
class Blackboard(Component):
    """
    Shared knowledge state for AI decision making.
    Populated by PerceptionSystem, consumed by UtilitySystem.

    Attributes:
        visible_targets (Dict[EntityID, TargetInfo]): Currently seen entities.
        short_term_memory (Dict[EntityID, LastKnownPosition]): Recently lost entities.
        nearby_friends (int): Count of allies nearby.
        nearby_enemies (int): Count of threats nearby.
        nearby_prey (int): Count of prey nearby.
        closest_threat_id (Optional[EntityID]): ID of critical threat.
        closest_food_id (Optional[EntityID]): ID of optimal food source.
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

    Attributes:
        archetype_id (str): Behavior profile name (e.g. "predator", "coward").
        priorities (List[GoalType]): Ordered preference list for goals.
        prey_tags (Set[str]): Tags treated as prey.
        predator_tags (Set[str]): Tags treated as predators.
        stamina_regen (float): Stamina recovery rate.
        personality_bias (Dict[str, float]): Base modifier for personality axes.
    """

    archetype_id: str = "default"
    priorities: list[GoalType] = field(default_factory=lambda: [GoalType.IDLE])
    prey_tags: set[str] = field(default_factory=set)
    predator_tags: set[str] = field(default_factory=set)
    stamina_regen: float = 10.0
    personality_bias: dict[str, float] = field(default_factory=dict)
