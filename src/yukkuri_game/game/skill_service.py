"""
Service for managing Skill mechanics: XP gain, Leveling, and Decay.
"""

from collections.abc import MutableMapping
from typing import Any

from loguru import logger

from ..config import SkillsSettings
from ..engine.ecs import World
from ..engine.event_bus import EventBus
from ..engine.resource_manager import ResourceManager
from .events import LevelUpEvent
from .services import TimeService
from .skill_constants import PassionLevel
from .trait_service import TraitService
from .components import (
    EmotionalState,
    Personality,
    Skills,
    SkillState,
    YukkuriStats,
)


class SkillService:
    """
    Manages skills for entities.

    Attributes:
        world (World): The ECS world instance.
        settings (SkillsSettings): Configuration settings.
        skill_definitions (MutableMapping[str, Any]): Loaded skill definitions.
    """

    def __init__(self, world: World, settings: SkillsSettings | None = None):
        """
        Initializes the SkillService.

        Args:
            world (World): The ECS world instance.
            settings (SkillsSettings | None): Configuration settings.
        """
        self.world = world
        self.settings = settings if settings else SkillsSettings()
        self.skill_definitions: MutableMapping[str, Any] = {}
        self.load_skill_definitions()

    def load_skill_definitions(self) -> None:
        """Loads skill definitions from ResourceManager."""
        rm = self.world.services.try_get(ResourceManager)
        if rm:
            # We use the raw dictionary/struct from ResourceManager
            # rm.skills is Dict[str, SkillDefinition]
            self.skill_definitions = rm.skills
        else:
            logger.warning("ResourceManager not found in World.")

    def initialize_skills(self, entity_id: int) -> None:
        """
        Initializes the Skills component for an entity if it doesn't exist,
        and ensures all defined skills are present.

        Args:
            entity_id (int): The entity ID.
        """
        if not self.world.entity_exists(entity_id):
            return

        skills = self.world.try_get_component(entity_id, Skills)
        if not skills:
            skills = Skills()
            self.world.add_component(entity_id, skills)

        # Determine current time for initialization to avoid instant decay
        current_time = 0.0
        time_service = self.world.services.try_get(TimeService)
        if time_service:
            current_time = time_service.time_elapsed

        # Initialize missing skills
        for skill_id in self.skill_definitions.keys():
            if skill_id not in skills.states:
                skills.states[skill_id] = SkillState(last_used_gametime=current_time)

        # Apply passion from traits
        self.recalculate_passions(entity_id)

    def recalculate_passions(self, entity_id: int) -> None:
        """
        Recalculates passion levels for all skills based on traits.

        Args:
            entity_id (int): The entity ID.
        """
        skills = self.world.try_get_component(entity_id, Skills)
        personality = self.world.try_get_component(entity_id, Personality)
        trait_service = self.world.services.try_get(TraitService)

        if not skills or not trait_service:
            return

        # Reset to default passion (Normal)
        for state in skills.states.values():
            state.passion = PassionLevel.NORMAL.value

        if not personality:
            return

        # Apply trait modifiers
        for trait_id in personality.traits:
            trait_data = trait_service.get_trait(trait_id)
            if not trait_data:
                continue

            # TraitDefinition is a msgspec.Struct.
            skill_modifiers = trait_data.skill_modifiers

            for skill_id_str, mods in skill_modifiers.items():
                if skill_id_str in skills.states:
                    passion_mult = mods.get("passion_multiplier", 1.0)
                    skills.states[skill_id_str].passion *= passion_mult

    def add_xp(self, entity_id: int, skill_id: str, amount: float) -> None:
        """
        Adds XP to a skill.

        Formula: XP_gain = Base * Passion * IntelligenceFactor * SoftCapMultiplier
        Intelligence is roughly derived from Discipline or Learning stat if available.

        Args:
            entity_id (int): The entity ID.
            skill_id (str): The skill identifier.
            amount (float): The amount of XP to add.
        """
        skills = self.world.try_get_component(entity_id, Skills)
        if not skills or skill_id not in skills.states:
            return

        state = skills.states[skill_id]
        definition = self.skill_definitions.get(skill_id)
        if not definition:
            return

        # definition is msgspec Struct
        max_level = definition.max_level

        if state.level >= max_level:
            return

        # Logic for Soft Cap
        soft_cap_base = definition.soft_cap_base_level
        # Passion affects soft cap: Cap = BaseCap + (Passion * 2)
        # Passion is float (0.5 to 2.5), so e.g. 1.0 -> +2 levels. 2.5 -> +5 levels.
        soft_cap_level = soft_cap_base + (state.passion * 2)

        gain_multiplier = 1.0
        if state.level >= soft_cap_level:
            gain_multiplier = 0.1

        # Intelligence factor.
        stats = self.world.try_get_component(entity_id, YukkuriStats)
        int_factor = 1.0
        if stats:
            int_factor = stats.intelligence

        final_xp = amount * state.passion * int_factor * gain_multiplier

        state.current_xp += final_xp

        # Burning Passion Effect: Gain happiness
        if state.passion >= PassionLevel.BURNING.value:
            emotional_state = self.world.try_get_component(entity_id, EmotionalState)
            if emotional_state:
                # Small happiness boost.
                # Capping it to avoid overflow is handled by logic elsewhere presumably,
                # but let's be safe or just add it. EmotionalState has limits -100 to 100?
                # The component definition says -100 to 100 but doesn't enforce it in the data class.
                # Usually systems enforce limits. We will just add a small amount.
                emotional_state.happiness = min(100.0, emotional_state.happiness + 1.0)

        # Update usage time
        time_service = self.world.services.try_get(TimeService)
        if time_service:
            state.last_used_gametime = time_service.time_elapsed

        self._check_level_up(entity_id, skill_id, state)

    def _check_level_up(self, entity_id: int, skill_id: str, state: SkillState) -> None:
        """
        Checks if the skill should level up.

        Args:
            entity_id (int): The entity ID.
            skill_id (str): The skill identifier.
            state (SkillState): The current skill state.
        """
        required = self.get_required_xp(state.level)
        while state.current_xp >= required:
            state.current_xp -= required
            state.level += 1
            logger.info(f"Entity {entity_id} leveled up {skill_id} to {state.level}!")

            # Publish event
            event_bus = self.world.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(LevelUpEvent(entity_id, skill_id, state.level))

            required = self.get_required_xp(state.level)

    def get_required_xp(self, level: int) -> float:
        """
        Calculates required XP for a level.

        Formula: Base * (Exponent)^L

        Args:
            level (int): The level.

        Returns:
            float: Required XP.
        """
        return self.settings.xp_base * (self.settings.xp_exponent**level)

    def apply_decay(self, entity_id: int) -> None:
        """
        Applies decay to all skills for an entity based on time since last use.

        This calculates accumulated decay since last use.
        Formula: Loss = DecayRate * (DaysSinceLastUse - GracePeriod)

        Args:
            entity_id (int): The entity ID.
        """
        skills = self.world.try_get_component(entity_id, Skills)
        if not skills:
            return

        time_service = self.world.services.try_get(TimeService)
        if not time_service:
            return

        current_time = time_service.time_elapsed
        SECONDS_PER_DAY = TimeService.GAME_DAY_LENGTH

        for skill_id, state in skills.states.items():
            definition = self.skill_definitions.get(skill_id)
            if not definition:
                continue

            decay_rate = definition.decay_rate
            if decay_rate <= 0:
                continue

            days_since_use = (current_time - state.last_used_gametime) / SECONDS_PER_DAY

            if days_since_use > 1.0:
                # Accumulate decay for the days past grace period
                # If days_since_use is 2.5, and grace is 1.0, we decay for 1.5 days worth
                excess_days = days_since_use - 1.0
                loss = decay_rate * excess_days

                state.current_xp = max(0.0, state.current_xp - loss)
