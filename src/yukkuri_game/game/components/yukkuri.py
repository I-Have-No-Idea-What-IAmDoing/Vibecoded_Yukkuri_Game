"""
Yukkuri-specific components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...engine.data_models import YukkuriType
    from ...config import StatsSettings
    from .social import Needs, EmotionalState

@dataclass(slots=True)
class YukkuriArchetype:
    """
    Flyweight object holding static data shared by all Yukkuris of a specific type.
    """
    from ...engine.data_models import YukkuriType
    type_data: "YukkuriType | None" = None


class FlightState(Enum):
    """
    Enumeration representing the current flight status of a Yukkuri.
    """
    GROUNDED = 0
    TAKEOFF = 1
    FLYING = 2
    HOVERING = 3
    LANDING = 4
    SWOOPING = 5
    FALLING = 6


@dataclass(slots=True)
class YukkuriStats:
    """
    Component containing general statistics and progression data.
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

    def calculate_value(
        self,
        needs: "Needs | None" = None,
        emotional_state: "EmotionalState | None" = None,
        stats_config: "StatsSettings | None" = None,
    ) -> int:
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
class SkillState:
    """
    Data container for a single skill instance.
    """
    level: int = 0
    current_xp: float = 0.0
    passion: float = 1.0
    last_used_gametime: float = 0.0


@dataclass(slots=True)
class Skills:
    """
    Component holding the collection of skills for an entity.
    """
    states: dict[str, SkillState] = field(default_factory=dict)


@dataclass(slots=True)
class Flight:
    """
    Component handling flight mechanics and stamina.
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
class Predator:
    """
    Component for predator behavior logic.
    """
    prey_tags: set[str] = field(default_factory=set)
    prey_sense_radius: float = 300.0
    hunger_threshold: float = 60.0
    aggression: float = 1.0
    dps: float = 20.0


@dataclass(slots=True)
class ItemStats:
    """
    Component defining the properties of an Item entity.
    """
    name: str
    type_id: str
    cost: int
    nutrition: float = 0.0
    fun: float = 0.0
    comfort: float = 0.0
    is_portable: bool = False
